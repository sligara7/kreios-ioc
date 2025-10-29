#!/usr/bin/env python3
"""
Export a reflow system to a separate GitHub repository.

This tool creates a clean export of a system (architecture only or with implementation)
to its own GitHub repository, keeping it separate from reflow tooling.

Usage:
    # Interactive mode
    python3 export_system_to_github.py systems/my_system --interactive

    # Direct mode
    python3 export_system_to_github.py systems/my_system \
        --type architecture_only \
        --repo https://github.com/org/my-system \
        --branch main
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import validate_system_root, PathSecurityError


class SystemExporter:
    """Export reflow systems to GitHub repositories"""

    def __init__(self, system_path: Path, reflow_root: Path):
        """
        Initialize system exporter with validated paths.

        Args:
            system_path: Pre-validated Path object to system directory
            reflow_root: Pre-validated Path object to reflow root directory
        """
        self.system_path = system_path
        self.system_name = system_path.name
        self.reflow_root = reflow_root

        if not self.system_path.exists():
            raise ValueError(f"System not found: {system_path}")

        print(f"System: {self.system_name}")
        print(f"Path: {self.system_path}")
    
    def get_export_type_interactive(self) -> str:
        """Prompt user for export type"""
        print("\n" + "=" * 80)
        print("EXPORT TYPE")
        print("=" * 80)
        print("1. architecture_only       - Architecture specs and docs only (no code)")
        print("2. architecture_and_implementation - Complete system with implementation")
        print("3. selective_services      - Choose specific services to export")
        
        while True:
            choice = input("\nSelect export type (1-3): ").strip()
            if choice == "1":
                return "architecture_only"
            elif choice == "2":
                return "architecture_and_implementation"
            elif choice == "3":
                return "selective_services"
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    
    def get_selected_services(self) -> List[str]:
        """Prompt user for service selection"""
        services_dir = self.system_path / "services"
        
        if not services_dir.exists():
            print("No services directory found")
            return []
        
        available_services = [
            d.name for d in services_dir.iterdir() 
            if d.is_dir() and not d.name.startswith('.')
        ]
        
        if not available_services:
            print("No services found in services/ directory")
            return []
        
        print("\nAvailable services:")
        for i, service in enumerate(available_services, 1):
            print(f"  {i}. {service}")
        
        print("\nEnter service numbers separated by commas (e.g., 1,3,4)")
        print("Or enter 'all' for all services")
        
        selection = input("Selection: ").strip()
        
        if selection.lower() == "all":
            return available_services
        
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(",")]
            return [available_services[i] for i in indices if 0 <= i < len(available_services)]
        except (ValueError, IndexError):
            print("Invalid selection, including all services")
            return available_services
    
    def prepare_export_directory(
        self, 
        export_type: str, 
        selected_services: Optional[List[str]] = None
    ) -> Path:
        """Create export directory with selected artifacts"""
        
        # Create temporary export directory
        export_dir = Path(tempfile.mkdtemp(prefix=f"reflow_export_{self.system_name}_"))
        
        print(f"\nPreparing export in: {export_dir}")
        
        # Always include specs and docs
        if (self.system_path / "specs").exists():
            print("  Copying specs/")
            shutil.copytree(
                self.system_path / "specs",
                export_dir / "specs"
            )
        
        if (self.system_path / "docs").exists():
            print("  Copying docs/")
            shutil.copytree(
                self.system_path / "docs",
                export_dir / "docs"
            )
        
        # Include services based on export type
        if export_type in ["architecture_and_implementation", "selective_services"]:
            services_dir = self.system_path / "services"
            if services_dir.exists():
                export_services_dir = export_dir / "services"
                export_services_dir.mkdir()
                
                if export_type == "selective_services" and selected_services:
                    for service in selected_services:
                        service_path = services_dir / service
                        if service_path.exists():
                            print(f"  Copying services/{service}/")
                            shutil.copytree(
                                service_path,
                                export_services_dir / service
                            )
                else:
                    print("  Copying services/")
                    for item in services_dir.iterdir():
                        if item.is_dir() and not item.name.startswith('.'):
                            shutil.copytree(item, export_services_dir / item.name)
        
        # Generate README
        self.generate_readme(export_dir, export_type)
        
        # Generate .gitignore
        self.generate_gitignore(export_dir, export_type)
        
        # Explicitly exclude context/ directory
        print("  Excluding context/ (reflow internal files)")
        
        return export_dir
    
    def generate_readme(self, export_dir: Path, export_type: str):
        """Generate README for exported system"""
        
        readme_content = f"""# {self.system_name}

**System Architecture and Implementation**

This system was designed using the [reflow](https://github.com/your-org/reflow) architecture workflow.

## Overview

"""
        
        # Include mission statement if available
        mission_file = self.system_path / "docs" / "SYSTEM_MISSION_STATEMENT.md"
        if mission_file.exists():
            with open(mission_file, 'r') as f:
                mission = f.read()
            readme_content += f"{mission}\n\n"
        
        # Architecture section
        readme_content += """## Architecture

System architecture specifications are located in the `specs/` directory:

- `specs/machine/` - Machine-readable specifications (JSON)
  - `index.json` - System component index
  - `service_arch/` - Service architecture definitions
  - `interface_registry.json` - Interface definitions
  - `interfaces/` - Interface Contract Documents (ICDs)
- `specs/human/` - Human-readable documentation
  - `visualizations/` - Architecture diagrams
  - `reports/` - Analysis reports

## Documentation

Foundational documentation is in the `docs/` directory:

- `SYSTEM_MISSION_STATEMENT.md` - System purpose and goals
- `USER_SCENARIOS.md` - User interaction scenarios
- `SUCCESS_CRITERIA.md` - System success metrics
- `ARCHITECTURE_CONTEXT_SUMMARY.md` - Architecture overview

"""
        
        # Implementation section (if applicable)
        if export_type != "architecture_only":
            readme_content += """## Implementation

Service implementations are in the `services/` directory:

```
services/
├── service_name_1/
│   ├── src/
│   ├── tests/
│   └── README.md
├── service_name_2/
│   ├── src/
│   ├── tests/
│   └── README.md
...
```

### Setup

(Add setup instructions here based on your implementation)

### Running Services

(Add service startup instructions here)

### Testing

(Add testing instructions here)

"""
        
        # Footer
        readme_content += f"""## Export Information

- **Export Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Export Type:** {export_type}
- **Source System:** {self.system_name}

## Contributing

(Add contribution guidelines here)

## License

(Add license information here)
"""
        
        with open(export_dir / "README.md", 'w') as f:
            f.write(readme_content)
        
        print("  Generated README.md")
    
    def generate_gitignore(self, export_dir: Path, export_type: str):
        """Generate .gitignore for exported system"""
        
        gitignore_content = """# Reflow internal files (DO NOT COMMIT)
context/
*.backup

# Editor files
.vscode/
.idea/
*.swp
*.swo

# OS files
.DS_Store
Thumbs.db
"""
        
        # Add language-specific ignores
        services_dir = export_dir / "services"
        if services_dir.exists():
            # Detect Python
            if any(services_dir.rglob("*.py")):
                gitignore_content += """
# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
.env
*.egg-info/
dist/
build/
"""
            
            # Detect Node.js
            if any(services_dir.rglob("package.json")):
                gitignore_content += """
# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.env
dist/
"""
            
            # Detect Go
            if any(services_dir.rglob("go.mod")):
                gitignore_content += """
# Go
*.exe
*.exe~
*.dll
*.so
*.dylib
bin/
vendor/
"""
        
        with open(export_dir / ".gitignore", 'w') as f:
            f.write(gitignore_content)
        
        print("  Generated .gitignore")
    
    def initialize_git_repo(self, export_dir: Path, commit_message: str) -> str:
        """Initialize git repository and create initial commit"""
        
        os.chdir(export_dir)
        
        # Initialize repo
        subprocess.run(["git", "init"], check=True, capture_output=True)
        print("  Initialized git repository")
        
        # Add all files
        subprocess.run(["git", "add", "."], check=True, capture_output=True)
        
        # Create initial commit
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            check=True,
            capture_output=True
        )
        
        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True
        )
        commit_hash = result.stdout.strip()
        
        print(f"  Created commit: {commit_hash[:8]}")
        
        return commit_hash
    
    def push_to_github(self, export_dir: Path, repo_url: str, branch: str = "main"):
        """Push to GitHub repository"""
        
        os.chdir(export_dir)
        
        print(f"\nPushing to {repo_url} ({branch})...")
        
        # Add remote
        subprocess.run(
            ["git", "remote", "add", "origin", repo_url],
            check=True,
            capture_output=True
        )
        
        # Rename branch if needed
        subprocess.run(
            ["git", "branch", "-M", branch],
            check=True,
            capture_output=True
        )
        
        # Push
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", branch],
                check=True,
                text=True
            )
            print(f"✓ Successfully pushed to {repo_url}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Push failed: {e}")
            print("  You may need to:")
            print("    1. Create the repository on GitHub first")
            print("    2. Ensure you have push access")
            print("    3. Set up authentication (SSH keys or token)")
            return False
    
    def document_export(
        self, 
        export_type: str, 
        repo_url: str, 
        branch: str, 
        commit_hash: str
    ):
        """Document export in system's process log"""
        
        process_log = self.system_path / "context" / "process_log.md"
        
        if not process_log.exists():
            process_log.parent.mkdir(parents=True, exist_ok=True)
            process_log.touch()
        
        log_entry = f"""
## GitHub Export - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

- **Export Type:** {export_type}
- **Repository:** {repo_url}
- **Branch:** {branch}
- **Commit Hash:** {commit_hash}
- **Status:** Completed

"""
        
        with open(process_log, 'a') as f:
            f.write(log_entry)
        
        print(f"\n✓ Export documented in {process_log}")
    
    def cleanup_export_directory(self, export_dir: Path):
        """Remove temporary export directory"""
        try:
            shutil.rmtree(export_dir)
            print(f"\n✓ Cleaned up temporary export directory")
        except Exception as e:
            print(f"\n⚠ Could not clean up {export_dir}: {e}")
            print("  You may need to remove it manually")
    
    def export(
        self,
        export_type: str,
        repo_url: str,
        branch: str = "main",
        commit_message: str = "Initial system export from reflow",
        selected_services: Optional[List[str]] = None,
        cleanup: bool = True
    ):
        """Main export process"""
        
        print("\n" + "=" * 80)
        print(f"EXPORTING SYSTEM: {self.system_name}")
        print("=" * 80)
        
        # Prepare export directory
        export_dir = self.prepare_export_directory(export_type, selected_services)
        
        # Initialize git and commit
        commit_hash = self.initialize_git_repo(export_dir, commit_message)
        
        # Push to GitHub
        push_success = self.push_to_github(export_dir, repo_url, branch)
        
        if push_success:
            # Document export
            self.document_export(export_type, repo_url, branch, commit_hash)
            
            print("\n" + "=" * 80)
            print("EXPORT COMPLETE")
            print("=" * 80)
            print(f"Repository: {repo_url}")
            print(f"Branch: {branch}")
            print(f"Commit: {commit_hash}")
        else:
            print("\n" + "=" * 80)
            print("EXPORT INCOMPLETE")
            print("=" * 80)
            print(f"Export prepared in: {export_dir}")
            print("You can manually push from this directory")
            cleanup = False  # Don't cleanup if push failed
        
        # Cleanup
        if cleanup:
            self.cleanup_export_directory(export_dir)
        
        return push_success


def main():
    parser = argparse.ArgumentParser(
        description="Export reflow system to GitHub repository"
    )
    parser.add_argument(
        "system_path",
        help="Path to system directory (e.g., systems/my_system)"
    )
    parser.add_argument(
        "--type",
        choices=["architecture_only", "architecture_and_implementation", "selective_services"],
        help="Type of export"
    )
    parser.add_argument(
        "--repo",
        help="GitHub repository URL (e.g., https://github.com/org/my-system)"
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch to push to (default: main)"
    )
    parser.add_argument(
        "--message",
        default="Initial system export from reflow",
        help="Commit message"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode (prompts for all options)"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Keep temporary export directory after push"
    )
    
    args = parser.parse_args()

    # Security: Validate system path and reflow root (v3.4.0 fix - SV-01)
    try:
        system_path = validate_system_root(args.system_path)
    except PathSecurityError as e:
        print(f"ERROR: Path security violation for system path: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"ERROR: System path does not exist: {args.system_path}")
        sys.exit(1)

    # Find reflow root
    if "systems" in system_path.parts:
        reflow_root = system_path.parent.parent
    else:
        reflow_root = Path.cwd()

    # Security: Validate reflow root (v3.4.0 fix - SV-01)
    try:
        reflow_root = validate_system_root(reflow_root)
    except (PathSecurityError, FileNotFoundError) as e:
        print(f"ERROR: Invalid reflow root: {e}")
        sys.exit(1)

    try:
        exporter = SystemExporter(system_path, reflow_root)
        
        # Interactive mode
        if args.interactive:
            export_type = exporter.get_export_type_interactive()
            
            selected_services = None
            if export_type == "selective_services":
                selected_services = exporter.get_selected_services()
            
            repo_url = input("\nGitHub repository URL: ").strip()
            branch = input(f"Branch (default: main): ").strip() or "main"
            commit_message = input(f"Commit message (default: Initial system export from reflow): ").strip()
            commit_message = commit_message or "Initial system export from reflow"
        else:
            # Direct mode
            if not args.type or not args.repo:
                print("ERROR: --type and --repo required in non-interactive mode")
                print("Use --interactive for guided export")
                sys.exit(1)
            
            export_type = args.type
            repo_url = args.repo
            branch = args.branch
            commit_message = args.message
            selected_services = None
        
        # Execute export
        success = exporter.export(
            export_type=export_type,
            repo_url=repo_url,
            branch=branch,
            commit_message=commit_message,
            selected_services=selected_services,
            cleanup=not args.no_cleanup
        )
        
        sys.exit(0 if success else 1)
    
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
