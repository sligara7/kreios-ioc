#!/usr/bin/env python3
"""
Framework Migration Tool - Migrate architecture files between frameworks

LESSON-08: Framework Switching Capability

Problem: If wrong framework chosen, must manually re-do all architecture files.
Solution: Automate framework migration with field mapping and manual review flagging.

Usage:
    python3 migrate_framework.py --from uaf --to decision_flow --system-root /path/to/system
    python3 migrate_framework.py --from decision_flow --to uaf --system-root /path/to/system
    python3 migrate_framework.py --analyze-only --system-root /path/to/system

Features:
    - Read existing architecture files (old framework)
    - Map fields: old framework → new framework
    - Generate architecture files in new framework
    - Update working_memory.json
    - Preserve data where possible, flag manual review needed

Limitations:
    - Cannot auto-generate edge weights (requires domain knowledge)
    - Cannot determine node types (decision_node vs process_step)
    - User must review and refine migrated files

Author: Claude (Anthropic)
Version: 1.0.0
Date: 2025-10-26
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# ANSI color codes for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class FrameworkMigrator:
    """Migrates architecture files between frameworks"""

    # Framework field mappings
    FIELD_MAPPINGS = {
        "uaf_to_decision_flow": {
            "service_id": "step_id",
            "service_name": "step_name",
            "service_description": "step_description",
            "interfaces": "transitions",
            "dependencies": "prerequisites",
            "capabilities": "activities",
            "deployment": "execution_environment",
        },
        "decision_flow_to_uaf": {
            "step_id": "service_id",
            "step_name": "service_name",
            "step_description": "service_description",
            "transitions": "interfaces",
            "prerequisites": "dependencies",
            "activities": "capabilities",
            "execution_environment": "deployment",
        },
        # Add more mappings as needed
    }

    # Default values for new fields that don't exist in source framework
    DEFAULT_VALUES = {
        "decision_flow": {
            "node_type": "process_step",  # Manual review needed
            "transitions": {
                "probability": 0.5,  # Manual review needed
                "weight": 5,  # Manual review needed
                "condition": "always",  # Manual review needed
                "transition_type": "sequential"
            }
        },
        "uaf": {
            "service_type": "application",
            "protocol": "HTTP",
            "authentication": "required"
        }
    }

    def __init__(self, system_root: str, from_framework: str, to_framework: str):
        self.system_root = Path(system_root)
        self.from_framework = from_framework
        self.to_framework = to_framework
        self.migration_report = {
            "migrated_files": 0,
            "auto_mapped_fields": 0,
            "manual_review_needed": [],
            "warnings": [],
            "errors": []
        }

    def analyze_current_framework(self) -> Dict[str, Any]:
        """Analyze current framework from working_memory.json"""
        working_memory_path = self.system_root / "context" / "working_memory.json"

        if not working_memory_path.exists():
            return {
                "current_framework": "unknown",
                "architecture_files": [],
                "error": f"working_memory.json not found at {working_memory_path}"
            }

        with open(working_memory_path, 'r') as f:
            working_memory = json.load(f)

        current_framework = working_memory.get("framework_configuration", {}).get("framework_id", "unknown")

        # Find architecture files
        specs_machine = self.system_root / "specs" / "machine"
        arch_files = []

        if specs_machine.exists():
            # Look for service_arch, component_arch, workflow_arch, etc.
            for arch_dir in specs_machine.iterdir():
                if arch_dir.is_dir() and "arch" in arch_dir.name:
                    for arch_file in arch_dir.rglob("*.json"):
                        if "architecture" in arch_file.name and not arch_file.is_symlink():
                            arch_files.append(str(arch_file.relative_to(self.system_root)))

        return {
            "current_framework": current_framework,
            "architecture_files": arch_files,
            "working_memory_path": str(working_memory_path.relative_to(self.system_root))
        }

    def map_field(self, field_name: str, field_value: Any, mapping_key: str) -> Tuple[str, Any, bool]:
        """
        Map a field from one framework to another.

        Returns:
            Tuple of (new_field_name, new_field_value, needs_manual_review)
        """
        field_mappings = self.FIELD_MAPPINGS.get(mapping_key, {})

        # Direct field mapping
        if field_name in field_mappings:
            new_field_name = field_mappings[field_name]
            return (new_field_name, field_value, False)

        # Field doesn't have direct mapping - preserve as-is but flag for review
        return (field_name, field_value, True)

    def migrate_architecture_file(self, arch_file_path: Path, mapping_key: str) -> Dict[str, Any]:
        """Migrate a single architecture file"""

        with open(arch_file_path, 'r') as f:
            old_arch = json.load(f)

        new_arch = {}
        manual_review_items = []

        # Migrate each field
        for field_name, field_value in old_arch.items():
            new_field_name, new_field_value, needs_review = self.map_field(
                field_name, field_value, mapping_key
            )

            new_arch[new_field_name] = new_field_value
            self.migration_report["auto_mapped_fields"] += 1

            if needs_review:
                manual_review_items.append({
                    "field": field_name,
                    "reason": "No direct mapping found",
                    "preserved_as": new_field_name,
                    "value": str(field_value)[:100]  # Truncate long values
                })

        # Add new framework-specific fields with defaults
        if self.to_framework in self.DEFAULT_VALUES:
            defaults = self.DEFAULT_VALUES[self.to_framework]
            for default_field, default_value in defaults.items():
                if default_field not in new_arch:
                    new_arch[default_field] = default_value
                    manual_review_items.append({
                        "field": default_field,
                        "reason": f"New field for {self.to_framework} framework - default value added",
                        "default_value": default_value,
                        "action": "Review and update with correct value"
                    })

        # Special handling for framework-specific transformations
        if mapping_key == "uaf_to_decision_flow":
            new_arch = self._transform_uaf_to_decision_flow(new_arch, manual_review_items)
        elif mapping_key == "decision_flow_to_uaf":
            new_arch = self._transform_decision_flow_to_uaf(new_arch, manual_review_items)

        return {
            "new_architecture": new_arch,
            "manual_review_items": manual_review_items
        }

    def _transform_uaf_to_decision_flow(self, arch: Dict, review_items: List) -> Dict:
        """Transform UAF-specific structures to Decision Flow"""

        # Transform interfaces → transitions
        if "transitions" in arch and isinstance(arch["transitions"], list):
            for i, transition in enumerate(arch["transitions"]):
                # Add Decision Flow specific fields
                if "probability" not in transition:
                    transition["probability"] = 0.5  # Default - needs review
                    review_items.append({
                        "field": f"transitions[{i}].probability",
                        "reason": "Transition probability not specified in UAF - default 0.5 added",
                        "action": "Estimate actual probability based on usage patterns"
                    })

                if "weight" not in transition:
                    transition["weight"] = 5  # Default - needs review
                    review_items.append({
                        "field": f"transitions[{i}].weight",
                        "reason": "Transition weight not specified in UAF - default 5 added",
                        "action": "Estimate execution count or frequency"
                    })

                if "condition" not in transition:
                    transition["condition"] = "always"
                    review_items.append({
                        "field": f"transitions[{i}].condition",
                        "reason": "Transition condition not specified - 'always' added",
                        "action": "Add actual condition if transition is conditional"
                    })

                if "transition_type" not in transition:
                    transition["transition_type"] = "sequential"
                    review_items.append({
                        "field": f"transitions[{i}].transition_type",
                        "reason": "Transition type not specified - 'sequential' assumed",
                        "action": "Change to 'conditional', 'rework', 'skip', or 'parallel' if appropriate"
                    })

        # Add node_type field
        if "node_type" not in arch:
            arch["node_type"] = "process_step"
            review_items.append({
                "field": "node_type",
                "reason": "Node type not in UAF - 'process_step' assumed",
                "action": "Change to 'decision_node', 'start_state', or 'end_state' if appropriate"
            })

        return arch

    def _transform_decision_flow_to_uaf(self, arch: Dict, review_items: List) -> Dict:
        """Transform Decision Flow-specific structures to UAF"""

        # Transform transitions → interfaces
        if "interfaces" in arch and isinstance(arch["interfaces"], list):
            for i, interface in enumerate(arch["interfaces"]):
                # Remove Decision Flow specific fields that don't apply to UAF
                flow_specific_fields = ["probability", "weight", "condition", "transition_type"]
                for field in flow_specific_fields:
                    if field in interface:
                        del interface[field]
                        review_items.append({
                            "field": f"interfaces[{i}].{field}",
                            "reason": f"Decision Flow field '{field}' removed (not applicable to UAF)",
                            "action": "No action needed - this is expected"
                        })

        # Remove node_type field
        if "node_type" in arch:
            del arch["node_type"]
            review_items.append({
                "field": "node_type",
                "reason": "Decision Flow node_type removed (not applicable to UAF)",
                "action": "No action needed - UAF uses service_type instead"
            })

        return arch

    def migrate(self, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """Execute framework migration"""

        print(f"{Colors.HEADER}═══════════════════════════════════════════════════════════{Colors.ENDC}")
        print(f"{Colors.BOLD}Framework Migration Tool{Colors.ENDC}")
        print(f"{Colors.HEADER}═══════════════════════════════════════════════════════════{Colors.ENDC}\n")

        print(f"System Root: {self.system_root}")
        print(f"From Framework: {Colors.FAIL}{self.from_framework}{Colors.ENDC}")
        print(f"To Framework: {Colors.OKGREEN}{self.to_framework}{Colors.ENDC}\n")

        # Analyze current state
        analysis = self.analyze_current_framework()

        if "error" in analysis:
            print(f"{Colors.FAIL}✗ Error:{Colors.ENDC} {analysis['error']}")
            return {"success": False, "error": analysis['error']}

        print(f"Current Framework: {analysis['current_framework']}")
        print(f"Architecture Files Found: {len(analysis['architecture_files'])}\n")

        if analysis['current_framework'] != self.from_framework:
            warning = f"WARNING: Current framework ({analysis['current_framework']}) doesn't match --from ({self.from_framework})"
            print(f"{Colors.WARNING}{warning}{Colors.ENDC}\n")
            self.migration_report["warnings"].append(warning)

        # Determine mapping key
        mapping_key = f"{self.from_framework}_to_{self.to_framework}"
        if mapping_key not in self.FIELD_MAPPINGS:
            error = f"No field mapping defined for {mapping_key}"
            print(f"{Colors.FAIL}✗ Error:{Colors.ENDC} {error}")
            print(f"\nAvailable mappings: {', '.join(self.FIELD_MAPPINGS.keys())}")
            return {"success": False, "error": error}

        # Create output directory
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = self.system_root / "specs" / "machine" / "migrated" / f"{self.to_framework}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        output_path.mkdir(parents=True, exist_ok=True)
        print(f"Output Directory: {output_path}\n")

        # Migrate each architecture file
        print(f"{Colors.OKBLUE}Migrating architecture files...{Colors.ENDC}\n")

        migrated_files = []
        for arch_file_rel in analysis['architecture_files']:
            arch_file = self.system_root / arch_file_rel
            print(f"  Processing: {arch_file.name}")

            result = self.migrate_architecture_file(arch_file, mapping_key)

            # Save migrated file
            output_file = output_path / arch_file.name
            with open(output_file, 'w') as f:
                json.dump(result["new_architecture"], f, indent=2)

            migrated_files.append({
                "original_file": str(arch_file_rel),
                "migrated_file": str(output_file.relative_to(self.system_root)),
                "manual_review_items": result["manual_review_items"]
            })

            self.migration_report["migrated_files"] += 1

            if result["manual_review_items"]:
                self.migration_report["manual_review_needed"].extend([
                    f"{arch_file.name}: {item['field']} - {item['reason']}"
                    for item in result["manual_review_items"]
                ])

        # Generate migration report
        report_path = output_path / "migration_report.json"
        full_report = {
            "migration_metadata": {
                "timestamp": datetime.now().isoformat(),
                "from_framework": self.from_framework,
                "to_framework": self.to_framework,
                "system_root": str(self.system_root),
                "output_directory": str(output_path)
            },
            "summary": self.migration_report,
            "migrated_files": migrated_files
        }

        with open(report_path, 'w') as f:
            json.dump(full_report, f, indent=2)

        # Print summary
        print(f"\n{Colors.OKGREEN}═══════════════════════════════════════════════════════════{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Migration Complete!{Colors.ENDC}")
        print(f"{Colors.OKGREEN}═══════════════════════════════════════════════════════════{Colors.ENDC}\n")

        print(f"Migrated Files: {Colors.BOLD}{self.migration_report['migrated_files']}{Colors.ENDC}")
        print(f"Auto-mapped Fields: {Colors.BOLD}{self.migration_report['auto_mapped_fields']}{Colors.ENDC}")
        print(f"Manual Review Items: {Colors.WARNING}{len(self.migration_report['manual_review_needed'])}{Colors.ENDC}\n")

        if self.migration_report['manual_review_needed']:
            print(f"{Colors.WARNING}⚠ Manual Review Needed:{Colors.ENDC}\n")
            for item in self.migration_report['manual_review_needed'][:10]:  # Show first 10
                print(f"  • {item}")
            if len(self.migration_report['manual_review_needed']) > 10:
                print(f"  ... and {len(self.migration_report['manual_review_needed']) - 10} more items")
            print()

        print(f"Next Steps:")
        print(f"  1. Review migrated files in: {output_path}")
        print(f"  2. Update edge probabilities/weights where needed (Decision Flow)")
        print(f"  3. Set correct node types (decision_node vs process_step)")
        print(f"  4. Run: python3 tools/validate_architecture.py {output_path}")
        print(f"  5. If validation passes, update working_memory.json framework_configuration")
        print(f"\nMigration report saved to: {report_path}\n")

        return {
            "success": True,
            "report": full_report,
            "output_directory": str(output_path)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Migrate architecture files between frameworks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate from UAF to Decision Flow
  python3 migrate_framework.py --from uaf --to decision_flow --system-root /path/to/system

  # Migrate from Decision Flow to UAF
  python3 migrate_framework.py --from decision_flow --to uaf --system-root /path/to/system

  # Analyze current framework only (no migration)
  python3 migrate_framework.py --analyze-only --system-root /path/to/system

  # Specify custom output directory
  python3 migrate_framework.py --from uaf --to decision_flow --system-root /path/to/system --output /custom/path

Supported Framework Migrations:
  • uaf → decision_flow (Services to Workflow States)
  • decision_flow → uaf (Workflow States to Services)

Limitations:
  - Cannot auto-generate edge weights (probability, weight) - requires domain knowledge
  - Cannot determine node types (decision_node vs process_step) - manual review required
  - User must review and refine migrated files before use
        """
    )

    parser.add_argument(
        '--from',
        dest='from_framework',
        type=str,
        help='Source framework ID (e.g., uaf, decision_flow)'
    )

    parser.add_argument(
        '--to',
        dest='to_framework',
        type=str,
        help='Target framework ID (e.g., decision_flow, uaf)'
    )

    parser.add_argument(
        '--system-root',
        type=str,
        required=True,
        help='Path to system root directory'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='Custom output directory for migrated files (default: specs/machine/migrated/)'
    )

    parser.add_argument(
        '--analyze-only',
        action='store_true',
        help='Only analyze current framework, do not migrate'
    )

    args = parser.parse_args()

    # Validate system root
    system_root = Path(args.system_root)
    if not system_root.exists():
        print(f"{Colors.FAIL}Error:{Colors.ENDC} System root does not exist: {system_root}")
        sys.exit(1)

    # Analyze-only mode
    if args.analyze_only:
        print(f"{Colors.HEADER}Framework Analysis{Colors.ENDC}\n")
        migrator = FrameworkMigrator(str(system_root), "unknown", "unknown")
        analysis = migrator.analyze_current_framework()

        if "error" in analysis:
            print(f"{Colors.FAIL}Error:{Colors.ENDC} {analysis['error']}")
            sys.exit(1)

        print(f"Current Framework: {Colors.OKGREEN}{analysis['current_framework']}{Colors.ENDC}")
        print(f"Architecture Files: {len(analysis['architecture_files'])}")

        if analysis['architecture_files']:
            print("\nArchitecture Files Found:")
            for arch_file in analysis['architecture_files']:
                print(f"  • {arch_file}")
        else:
            print(f"\n{Colors.WARNING}No architecture files found{Colors.ENDC}")

        sys.exit(0)

    # Migration mode - validate arguments
    if not args.from_framework or not args.to_framework:
        print(f"{Colors.FAIL}Error:{Colors.ENDC} --from and --to are required for migration")
        print("Use --analyze-only to see current framework without migrating")
        sys.exit(1)

    # Execute migration
    migrator = FrameworkMigrator(str(system_root), args.from_framework, args.to_framework)
    result = migrator.migrate(args.output)

    if not result["success"]:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
