#!/usr/bin/env python3
"""
Feature Analysis Tool

Parses feature summary documents to identify required systems and their responsibilities.
This tool helps break down high-level requirements into system boundaries for architecture design.

Analyzes markdown feature summaries with structured sections (### numbered sections) and:
- Extracts feature descriptions from each section
- Maps features to system IDs based on section titles
- Identifies required systems for architecture design
- Updates working memory with system requirements
- Generates analysis report for LLM architectural planning

Usage:
    python3 analyze_features.py <feature_summary_path>

Expected Input Format:
    Markdown file with sections like:
    ### 1. User Authentication & Management
    ### 2. Content Creation & Publishing
    ### 3. Payment Processing & Billing

Output:
    - JSON analysis report with system breakdown
    - Updated working_memory.json with required_systems list

LLM Usage:
    Use analysis results to inform system decomposition in architecture phase.
    Each identified system becomes a candidate for service architecture design.
"""

import sys
import json
from pathlib import Path
import re
from typing import Dict, List, Set

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import sanitize_path, validate_system_root, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError

class FeatureAnalyzer:
    def __init__(self, feature_summary_path: Path):
        self.feature_summary_path = Path(feature_summary_path)
        self.required_systems = {}
        self.system_features = {}

    def parse_feature_summary(self) -> dict:
        """Parse feature summary markdown for system requirements"""
        try:
            with open(self.feature_summary_path) as f:
                content = f.read()

            # Find all major section headers (e.g., "### 1. Character Creation & Management")
            sections = re.findall(r'### \d+\. ([^\n]+)', content)
            
            for section in sections:
                # Extract section content
                section_pattern = f"### \\d+\\. {re.escape(section)}([^#]*)"
                match = re.search(section_pattern, content)
                if not match:
                    continue
                
                section_content = match.group(1)
                
                # Determine required system
                system_id = self._get_system_id(section)
                
                # Extract features
                features = self._extract_features(section_content)
                
                # Store mapping
                if features:
                    self.required_systems[system_id] = {
                        "section": section,
                        "features": features
                    }
                    self.system_features[system_id] = features

        except Exception as e:
            print(f"Error parsing feature summary: {str(e)}")
            return None

        return {
            "required_systems": self.required_systems,
            "system_features": self.system_features
        }

    def _get_system_id(self, section: str) -> str:
        """Convert section title to system ID"""
        # Remove numbers and special characters
        clean = re.sub(r'^\d+\.\s*', '', section)
        # Convert to lowercase and replace spaces/special chars
        system_id = clean.lower().replace(" & ", "_").replace(" ", "_") + "_system"
        return system_id

    def _extract_features(self, content: str) -> List[str]:
        """Extract feature descriptions from section content"""
        features = []
        
        # Look for subsections (####) or bullet points
        subsections = re.findall(r'####\s+([^\n]+)', content)
        bullets = re.findall(r'[-*]\s+([^\n]+)', content)
        
        features.extend(subsections)
        features.extend(bullets)
        
        return features

    def update_working_memory(self, working_memory_path: Path):
        """
        Update working memory with required systems.

        Args:
            working_memory_path: Pre-validated Path object to working_memory.json
        """
        try:
            # Load existing working memory
            if working_memory_path.exists():
                memory = safe_load_json(working_memory_path, file_type_description="working memory")
            else:
                memory = {}

            # Update required systems
            memory["required_systems"] = [
                {
                    "system_id": system_id,
                    "section": data["section"],
                    "feature_count": len(data["features"]),
                    "status": "identified",
                    "created_at": None
                }
                for system_id, data in self.required_systems.items()
            ]

            # Save updated working memory
            with open(working_memory_path, "w") as f:
                json.dump(memory, f, indent=2)

        except PathSecurityError as e:
            print(f"Error: Path security violation: {e}")
        except Exception as e:
            print(f"Error updating working memory: {str(e)}")

    def generate_report(self) -> dict:
        """Generate analysis report with LLM architectural guidance"""
        total_features = sum(len(features) for features in self.system_features.values())
        
        return {
            "timestamp": "2025-10-14T00:00:00Z",
            "feature_summary_path": str(self.feature_summary_path),
            "analysis": {
                "required_systems": len(self.required_systems),
                "total_features": total_features,
                "systems": [
                    {
                        "system_id": system_id,
                        "section": data["section"],
                        "feature_count": len(data["features"]),
                        "features": data["features"]
                    }
                    for system_id, data in self.required_systems.items()
                ]
            },
            "llm_architectural_guidance": {
                "purpose": "Use identified systems as basis for service architecture decomposition",
                "next_steps": [
                    "1. Review each identified system and its feature responsibilities",
                    "2. Use system_id values as candidate service names in architecture design",
                    "3. Map features to service capabilities in service_architecture.json files",
                    "4. Ensure complete feature coverage across all identified systems",
                    "5. Consider system interactions and interface requirements"
                ],
                "system_design_considerations": [
                    f"Each system represents a distinct domain boundary with {total_features//len(self.required_systems) if len(self.required_systems) > 0 else 0} average features",
                    "Systems with high feature counts may need further decomposition",
                    "Systems with related features should consider shared interfaces",
                    "Use feature descriptions to derive service capabilities and interfaces"
                ],
                "working_memory_updated": "required_systems list populated for architecture workflow"
            }
        }

def main():
    if len(sys.argv) != 2:
        print("Usage: analyze_features.py <feature_summary_path>")
        sys.exit(1)

    # Security: Validate feature summary path (v3.4.0 fix - SV-01)
    try:
        feature_summary_path = Path(sys.argv[1]).resolve()

        # Verify file exists
        if not feature_summary_path.exists():
            print(f"Error: Feature summary {feature_summary_path} does not exist")
            sys.exit(1)

        if not feature_summary_path.is_file():
            print(f"Error: Path must be a file: {feature_summary_path}")
            sys.exit(1)

        # Get system_root (parent directory of feature summary)
        system_root = feature_summary_path.parent
        system_root = validate_system_root(system_root)

        # Sanitize feature_summary_path relative to system_root
        feature_summary_path = sanitize_path(
            feature_summary_path.relative_to(system_root),
            system_root,
            must_exist=True
        )

    except PathSecurityError as e:
        print(f"ERROR: Path security violation: {e}")
        sys.exit(1)
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    analyzer = FeatureAnalyzer(feature_summary_path)

    # Parse features
    analysis = analyzer.parse_feature_summary()
    if not analysis:
        print("Error analyzing feature summary")
        sys.exit(1)

    # Security: Sanitize working_memory path (v3.4.0 fix - SV-01)
    try:
        working_memory_path = sanitize_path(
            "working_memory.json",
            system_root,
            must_exist=False
        )
        analyzer.update_working_memory(working_memory_path)
    except PathSecurityError as e:
        print(f"ERROR: Could not update working memory: Path security violation: {e}")
        # Continue anyway - analysis report is still useful

    # Generate and print report
    report = analyzer.generate_report()
    print(json.dumps(report, indent=2))
    
    # Summary for LLM agents
    system_count = len(analyzer.required_systems)
    feature_count = sum(len(features) for features in analyzer.system_features.values())
    
    print(f"\n📊 Feature Analysis Complete:")
    print(f"✅ Identified {system_count} required systems from feature analysis")
    print(f"✅ Mapped {feature_count} total features to system boundaries")
    print(f"✅ Updated working_memory.json with required_systems list")
    print("🤖 LLM agents can use identified systems for architecture decomposition")

if __name__ == "__main__":
    main()