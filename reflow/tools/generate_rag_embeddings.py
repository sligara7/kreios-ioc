#!/usr/bin/env python3
"""
Generate RAG embeddings for reflow workflow context management.

This tool chunks and embeds decision_flow.json, workflow files, and system context
into vector representations for semantic retrieval.

Usage:
    python3 generate_rag_embeddings.py <system_path> [--config <config_path>] [--force-rebuild]
"""

import json
import os
import sys
import pickle
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import argparse

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import validate_system_root, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
except ImportError as e:
    print(f"ERROR: Required dependencies not installed: {e}")
    print("Install with: pip install sentence-transformers faiss-cpu numpy")
    sys.exit(1)


class RAGEmbeddingGenerator:
    """Generate and manage embeddings for RAG-enhanced context management."""

    def __init__(self, system_path: Path, config_path: Path = None):
        """
        Initialize RAG embedding generator with validated paths.

        Args:
            system_path: Pre-validated Path object to system directory
            config_path: Optional pre-validated Path object to config file
        """
        self.system_path = system_path
        self.reflow_root = self._find_reflow_root()

        # Load RAG configuration
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = self.system_path / "context" / "rag_context_config.json"
        
        if not self.config_path.exists():
            print(f"ERROR: RAG config not found at {self.config_path}")
            print("Create from template: cp templates/rag_context_config_template.json systems/<system>/context/rag_context_config.json")
            sys.exit(1)
        
        config_data = safe_load_json(self.config_path, file_type_description="RAG context configuration")
            self.config = config_data.get('rag_context_configuration', config_data)
        
        # Initialize embedding model
        model_name = self.config['embedding_configuration']['model']
        print(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.config['embedding_configuration']['dimension']
        
        # Setup storage paths
        self.embeddings_dir = self.system_path / self.config['embedding_configuration']['storage_path']
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_dir = self.embeddings_dir / "cache"
        self.cache_dir.mkdir(exist_ok=True)
    
    def _find_reflow_root(self) -> Path:
        """Find the reflow root directory."""
        current = self.system_path
        while current != current.parent:
            if (current / "tools").exists() and (current / "templates").exists():
                return current
            current = current.parent
        raise RuntimeError("Could not find reflow root (no tools/ or templates/ directories)")
    
    def _resolve_path(self, path_str: str) -> Path:
        """Resolve relative paths from system directory or reflow root."""
        path = Path(path_str)
        if path.is_absolute():
            return path
        
        # Try relative to system directory
        system_relative = self.system_path / path
        if system_relative.exists():
            return system_relative
        
        # Try relative to reflow root
        reflow_relative = self.reflow_root / path
        if reflow_relative.exists():
            return reflow_relative
        
        raise FileNotFoundError(f"Could not resolve path: {path_str}")
    
    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file for change detection."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _chunk_json_by_sections(self, data: Dict, sections: List[str], prefix: str = "") -> List[Dict[str, Any]]:
        """Chunk JSON data by specified sections."""
        chunks = []
        
        for section in sections:
            section_path = section.split('.')
            current = data
            
            try:
                for key in section_path:
                    if isinstance(current, dict):
                        current = current[key]
                    else:
                        break
                
                chunk_id = f"{prefix}.{section}" if prefix else section
                chunk_text = json.dumps(current, indent=2) if isinstance(current, (dict, list)) else str(current)
                
                chunks.append({
                    'id': chunk_id,
                    'section': section,
                    'text': chunk_text,
                    'type': 'json_section',
                    'metadata': {
                        'section_path': section,
                        'prefix': prefix
                    }
                })
            except (KeyError, TypeError) as e:
                print(f"Warning: Could not extract section '{section}': {e}")
        
        return chunks
    
    def _chunk_workflow_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Chunk workflow JSON file by steps and substeps."""
        data = safe_load_json(file_path, file_type_description="workflow file")
        
        chunks = []
        workflow_name = file_path.stem
        
        # Chunk by steps
        if 'steps' in data:
            for step in data['steps']:
                step_id = step.get('id', step.get('step_id', 'unknown'))
                chunk_id = f"{workflow_name}.{step_id}"
                
                chunks.append({
                    'id': chunk_id,
                    'section': step_id,
                    'text': json.dumps(step, indent=2),
                    'type': 'workflow_step',
                    'metadata': {
                        'workflow': workflow_name,
                        'step_id': step_id,
                        'file': str(file_path)
                    }
                })
                
                # Chunk substeps if present
                if 'substeps' in step:
                    for substep in step['substeps']:
                        substep_id = substep.get('id', substep.get('substep_id', 'unknown'))
                        substep_chunk_id = f"{workflow_name}.{step_id}.{substep_id}"
                        
                        chunks.append({
                            'id': substep_chunk_id,
                            'section': f"{step_id}.{substep_id}",
                            'text': json.dumps(substep, indent=2),
                            'type': 'workflow_substep',
                            'metadata': {
                                'workflow': workflow_name,
                                'step_id': step_id,
                                'substep_id': substep_id,
                                'file': str(file_path)
                            }
                        })
        
        return chunks
    
    def _embed_chunks(self, chunks: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[Dict]]:
        """Generate embeddings for text chunks."""
        texts = [chunk['text'] for chunk in chunks]
        print(f"  Embedding {len(texts)} chunks...")
        
        embeddings = self.model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        return embeddings, chunks
    
    def process_knowledge_base(self, kb_config: Dict, force_rebuild: bool = False) -> Dict[str, Any]:
        """Process a single knowledge base and generate embeddings."""
        kb_name = kb_config['name']
        print(f"\nProcessing knowledge base: {kb_name}")
        
        embeddings_file = self.embeddings_dir / kb_config['embeddings_file']
        metadata_file = self.embeddings_dir / kb_config['metadata_file']
        
        # Check if rebuild needed
        if not force_rebuild and embeddings_file.exists() and metadata_file.exists():
            metadata = safe_load_json(metadata_file, file_type_description="embedding metadata")
            
            # Check if source files changed
            source_changed = False
            if 'source_file' in kb_config:
                source_path = self._resolve_path(kb_config['source_file'])
                current_hash = self._compute_file_hash(source_path)
                if metadata.get('source_hash') != current_hash:
                    source_changed = True
            
            if not source_changed:
                print(f"  Embeddings up-to-date, skipping")
                return metadata
        
        # Process based on knowledge base type
        chunks = []
        source_hashes = {}
        
        if 'source_file' in kb_config:
            source_path = self._resolve_path(kb_config['source_file'])
            print(f"  Loading: {source_path}")
            
            data = safe_load_json(source_path, file_type_description=f"knowledge base source '{kb_config.get('name', 'file')}'")
            
            source_hashes[str(source_path)] = self._compute_file_hash(source_path)
            
            if 'chunk_sections' in kb_config:
                chunks = self._chunk_json_by_sections(
                    data, 
                    kb_config['chunk_sections'],
                    prefix=kb_name
                )
            else:
                # Default: whole file as single chunk
                chunks = [{
                    'id': kb_name,
                    'section': 'full',
                    'text': json.dumps(data, indent=2),
                    'type': 'full_document',
                    'metadata': {'file': str(source_path)}
                }]
        
        elif 'source_files' in kb_config:
            # Handle multiple source files or glob patterns
            source_patterns = kb_config['source_files']
            for pattern in source_patterns:
                resolved_pattern = self._resolve_path(pattern.replace('*.json', ''))
                
                if '*' in pattern:
                    # Glob pattern
                    parent_dir = resolved_pattern
                    pattern_suffix = pattern.split('/')[-1]
                    
                    for file_path in parent_dir.glob(pattern_suffix):
                        if file_path.suffix == '.json':
                            print(f"  Loading: {file_path}")
                            source_hashes[str(file_path)] = self._compute_file_hash(file_path)
                            
                            if 'workflow' in kb_config.get('content_type', ''):
                                chunks.extend(self._chunk_workflow_file(file_path))
                            else:
                                data = safe_load_json(file_path, file_type_description="JSON document")
                                chunks.append({
                                    'id': file_path.stem,
                                    'section': 'full',
                                    'text': json.dumps(data, indent=2),
                                    'type': 'full_document',
                                    'metadata': {'file': str(file_path)}
                                })
                else:
                    # Single file
                    file_path = self._resolve_path(pattern)
                    if file_path.exists():
                        print(f"  Loading: {file_path}")
                        source_hashes[str(file_path)] = self._compute_file_hash(file_path)
                        
                        if file_path.suffix == '.json':
                            data = safe_load_json(file_path, file_type_description="JSON document")
                            text = json.dumps(data, indent=2)
                        else:
                            with open(file_path, 'r') as f:
                                text = f.read()
                        
                        chunks.append({
                            'id': file_path.stem,
                            'section': 'full',
                            'text': text,
                            'type': 'full_document',
                            'metadata': {'file': str(file_path)}
                        })
        
        if not chunks:
            print(f"  WARNING: No chunks generated for {kb_name}")
            return {}
        
        # Generate embeddings
        embeddings, chunks = self._embed_chunks(chunks)
        
        # Create FAISS index
        index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
        index.add(embeddings)
        
        # Save embeddings and index
        with open(embeddings_file, 'wb') as f:
            pickle.dump({
                'index': index,
                'embeddings': embeddings,
                'chunks': chunks
            }, f)
        
        # Save metadata
        metadata = {
            'kb_name': kb_name,
            'content_type': kb_config.get('content_type'),
            'priority': kb_config.get('priority'),
            'num_chunks': len(chunks),
            'embedding_dim': self.embedding_dim,
            'generated_at': datetime.now().isoformat(),
            'source_hashes': source_hashes,
            'chunk_ids': [c['id'] for c in chunks]
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"  Generated {len(chunks)} embeddings, saved to {embeddings_file}")
        
        return metadata
    
    def generate_all_embeddings(self, force_rebuild: bool = False):
        """Generate embeddings for all configured knowledge bases."""
        print(f"RAG Embedding Generation")
        print(f"System: {self.system_path.name}")
        print(f"Reflow Root: {self.reflow_root}")
        print(f"Embeddings Directory: {self.embeddings_dir}")
        
        results = []
        
        for kb_config in self.config['knowledge_bases']:
            try:
                metadata = self.process_knowledge_base(kb_config, force_rebuild)
                if metadata:
                    results.append(metadata)
            except Exception as e:
                print(f"ERROR processing {kb_config['name']}: {e}")
                import traceback
                traceback.print_exc()
        
        # Save generation summary
        summary = {
            'generated_at': datetime.now().isoformat(),
            'system_name': self.config.get('system_name'),
            'total_knowledge_bases': len(results),
            'embedding_model': self.config['embedding_configuration']['model'],
            'embedding_dimension': self.embedding_dim,
            'knowledge_bases': results
        }
        
        summary_file = self.embeddings_dir / "generation_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n✓ Generation complete. Summary saved to {summary_file}")
        print(f"  Total knowledge bases: {len(results)}")
        print(f"  Total chunks embedded: {sum(kb['num_chunks'] for kb in results)}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate RAG embeddings for reflow workflow context"
    )
    parser.add_argument(
        'system_path',
        help="Path to system directory (e.g., systems/my_system)"
    )
    parser.add_argument(
        '--config',
        help="Path to RAG config file (default: <system>/context/rag_context_config.json)"
    )
    parser.add_argument(
        '--force-rebuild',
        action='store_true',
        help="Force rebuild all embeddings even if up-to-date"
    )
    
    args = parser.parse_args()

    # Security: Validate system path (v3.4.0 fix - SV-01)
    try:
        system_path = validate_system_root(args.system_path)
    except PathSecurityError as e:
        print(f"ERROR: Path security violation: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"ERROR: System path does not exist: {args.system_path}")
        sys.exit(1)

    # Security: Validate config path if provided (v3.4.0 fix - SV-01)
    config_path = None
    if args.config:
        try:
            config_path = Path(args.config).resolve()
            if not config_path.exists():
                print(f"ERROR: Config file does not exist: {args.config}")
                sys.exit(1)
        except Exception as e:
            print(f"ERROR: Invalid config path: {e}")
            sys.exit(1)

    generator = RAGEmbeddingGenerator(system_path, config_path)
    generator.generate_all_embeddings(force_rebuild=args.force_rebuild)


if __name__ == '__main__':
    main()
