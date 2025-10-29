#!/usr/bin/env python3
"""
Validate Component Deltas Tool - PRODUCTION VERSION
Validates that proposed component deltas are feasible and don't conflict with existing code

Validation checks:
1. File existence - Do files exist where changes are proposed?
2. Function/class existence - Can we modify what we claim exists?
3. Dependency compatibility - Are new dependencies compatible?
4. Breaking change detection - Are breaking changes correctly flagged?
5. Feasibility assessment - Can proposed changes be implemented?

Usage:
    # Validate single delta:
    python3 validate_component_deltas.py \\
        --component-delta <path_to_component_delta.json> \\
        --component-source <path_to_component_source_dir> \\
        --check-feasibility

    # Validate all deltas:
    python3 validate_component_deltas.py \\
        --all-deltas <path_to_component_deltas_dir> \\
        --inventory <path_to_component_inventory.json>
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
import re
from datetime import datetime

VERSION = "2.0.0"

def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def check_file_exists(source_dir: Path, file_path: str) -> bool:
    """Check if file exists in source directory"""
    # Remove src/ prefix if present
    file_path = file_path.replace('src/', '')

    # Try different possible paths
    possible_paths = [
        source_dir / file_path,
        source_dir / 'src' / file_path,
        source_dir / file_path.split('/')[-1]  # Just filename
    ]

    for path in possible_paths:
        if path.exists():
            return True
    return False

def check_function_exists(source_dir: Path, location: str) -> Tuple[bool, Path | None]:
    """
    Check if function already exists (to detect conflicts)

    Returns: (exists, file_path)
    """
    # Parse location (e.g., "src/component/api.py::function_name()")
    parts = location.split('::')
    file_path = parts[0]
    function_name = parts[1].split('(')[0] if len(parts) > 1 else None

    if not function_name:
        return False, None

    # Check if file exists
    file_path_clean = file_path.replace('src/', '')
    possible_paths = [
        source_dir / file_path_clean,
        source_dir / 'src' / file_path_clean
    ]

    for path in possible_paths:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    content = f.read()
                    # Look for function definition
                    patterns = [
                        f"def {function_name}\\(",
                        f"async def {function_name}\\("
                    ]
                    for pattern in patterns:
                        if re.search(pattern, content):
                            return True, path
            except:
                pass

    return False, None

def check_class_exists(source_dir: Path, location: str, class_name: str) -> Tuple[bool, Path | None]:
    """
    Check if class already exists

    Returns: (exists, file_path)
    """
    file_path = location.replace('src/', '')
    possible_paths = [
        source_dir / file_path,
        source_dir / 'src' / file_path
    ]

    for path in possible_paths:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    content = f.read()
                    if re.search(f"class {class_name}\\(", content) or re.search(f"class {class_name}:", content):
                        return True, path
            except:
                pass

    return False, None

def validate_dependency_compatibility(dependencies: List[str]) -> List[Dict[str, str]]:
    """
    Validate that dependencies are compatible

    Returns list of issues found
    """
    issues = []

    # Check for version conflicts within added dependencies
    dep_versions = {}
    for dep in dependencies:
        # Parse package name and version (e.g., "requests>=2.31.0")
        match = re.match(r'([a-zA-Z0-9_-]+)(.*)', dep)
        if match:
            pkg_name = match.group(1)
            version_spec = match.group(2)

            if pkg_name in dep_versions:
                issues.append({
                    "issue": f"Duplicate dependency: {pkg_name}",
                    "severity": "medium",
                    "details": f"Package {pkg_name} specified multiple times: {dep_versions[pkg_name]}, {version_spec}"
                })
            else:
                dep_versions[pkg_name] = version_spec

    return issues

def validate_single_delta(delta: Dict, source_dir: Path, check_source: bool = True) -> Dict[str, Any]:
    """
    Validate a single component delta

    Args:
        delta: Component delta JSON
        source_dir: Path to component source directory
        check_source: Whether to check actual source code (False if source unavailable)

    Returns:
        Validation results dict
    """

    component_id = delta['delta_metadata']['component_id']

    print(f"\nValidating delta for component: {component_id}")

    validation_results = {
        "component_id": component_id,
        "validation_passed": True,
        "issues": [],
        "warnings": [],
        "info": [],
        "checks_performed": {
            "structure_validation": True,
            "source_code_validation": check_source,
            "dependency_validation": True,
            "breaking_change_analysis": True
        }
    }

    # Check 1: Validate delta structure
    required_fields = ['delta_metadata', 'component_context', 'required_changes', 'summary']
    for field in required_fields:
        if field not in delta:
            validation_results['issues'].append({
                "check": "structure_validation",
                "issue": f"Missing required field: {field}",
                "severity": "critical"
            })
            validation_results['validation_passed'] = False

    # Check 2: Validate each required change
    for change in delta.get('required_changes', []):
        change_id = change.get('change_id', 'UNKNOWN')
        change_type = change.get('change_type')
        location = change.get('location', '')

        print(f"  Validating {change_id} ({change_type})...")

        # Check 2a: New functions shouldn't already exist
        if change_type == 'new_function' and check_source:
            if '::' in location:
                exists, file_path = check_function_exists(source_dir, location)
                if exists:
                    func_name = location.split('::')[1].split('(')[0]
                    validation_results['issues'].append({
                        "change_id": change_id,
                        "check": "function_existence",
                        "issue": f"Function {func_name} already exists in {file_path}",
                        "severity": "high",
                        "recommendation": "Use modify_function instead of new_function OR rename the new function"
                    })
                    validation_results['validation_passed'] = False
            else:
                # Check if file exists for new function
                file_path = location.split('::')[0]
                if check_source and not check_file_exists(source_dir, file_path):
                    validation_results['warnings'].append({
                        "change_id": change_id,
                        "check": "file_existence",
                        "warning": f"File {file_path} does not exist - will be created",
                        "severity": "info"
                    })

        # Check 2b: Modified functions should exist
        elif change_type == 'modify_function' and check_source:
            if '::' in location:
                exists, file_path = check_function_exists(source_dir, location)
                if not exists:
                    func_name = location.split('::')[1].replace('()', '')
                    validation_results['issues'].append({
                        "change_id": change_id,
                        "check": "function_existence",
                        "issue": f"Function {func_name} does not exist in {location.split('::')[0]} - cannot modify",
                        "severity": "critical",
                        "recommendation": "Use new_function instead OR verify function name is correct"
                    })
                    validation_results['validation_passed'] = False

        # Check 2c: New classes shouldn't already exist
        elif change_type == 'new_class' and check_source:
            impl = change.get('new_implementation', {})
            classes = impl.get('classes', [])
            for cls in classes:
                class_name = cls.get('class_name')
                if class_name:
                    exists, file_path = check_class_exists(source_dir, location, class_name)
                    if exists:
                        validation_results['issues'].append({
                            "change_id": change_id,
                            "check": "class_existence",
                            "issue": f"Class {class_name} already exists in {file_path}",
                            "severity": "high",
                            "recommendation": "Use modify_class instead OR rename the new class"
                        })
                        validation_results['validation_passed'] = False

        # Check 2d: New modules shouldn't already exist
        elif change_type == 'new_module' and check_source:
            if check_file_exists(source_dir, location):
                validation_results['warnings'].append({
                    "change_id": change_id,
                    "check": "module_existence",
                    "warning": f"Module {location} already exists - will overwrite",
                    "severity": "medium",
                    "recommendation": "Review existing module before overwriting"
                })

        # Check 2e: Validate breaking changes are correctly flagged
        breaking_change = change.get('breaking_change', False)
        backward_compatible = change.get('backward_compatible', True)

        if change_type == 'modify_function':
            current_sig = change.get('current_state', {}).get('current_code', '')
            new_impl = change.get('new_implementation', {})

            # Heuristic: If function signature changes, it's likely breaking
            if current_sig and 'def ' in current_sig:
                # Extract current signature
                current_func = re.search(r'def\s+(\w+)\([^)]*\)', current_sig)
                new_sig = new_impl.get('function_signature', '')

                if current_func and new_sig and 'def ' in new_sig:
                    new_func = re.search(r'def\s+(\w+)\([^)]*\)', new_sig)
                    if current_func.group(0) != new_func.group(0):
                        # Signature changed
                        if not breaking_change:
                            validation_results['warnings'].append({
                                "change_id": change_id,
                                "check": "breaking_change_detection",
                                "warning": "Function signature changed but not flagged as breaking",
                                "severity": "high",
                                "recommendation": "Verify if this is a breaking change"
                            })

        # Check 2f: Validate estimated effort is reasonable
        effort = change.get('estimated_effort', '')
        if not effort or effort == 'TBD':
            validation_results['warnings'].append({
                "change_id": change_id,
                "check": "effort_estimation",
                "warning": "No effort estimate provided",
                "severity": "low"
            })

    # Check 3: Validate dependencies
    dep_changes = delta.get('dependency_changes', {})
    added_deps = dep_changes.get('added', [])

    if added_deps:
        dep_issues = validate_dependency_compatibility(added_deps)
        for issue in dep_issues:
            validation_results['warnings'].append({
                "check": "dependency_validation",
                "warning": issue['issue'],
                "severity": issue['severity'],
                "details": issue.get('details', '')
            })

    # Check 4: Validate summary is accurate
    summary = delta.get('summary', {})
    actual_change_count = len(delta.get('required_changes', []))
    reported_change_count = summary.get('total_changes', 0)

    if actual_change_count != reported_change_count:
        validation_results['issues'].append({
            "check": "summary_validation",
            "issue": f"Summary reports {reported_change_count} changes but {actual_change_count} changes found",
            "severity": "medium"
        })

    # Check 5: Validate breaking changes count
    actual_breaking = len([c for c in delta.get('required_changes', []) if c.get('breaking_change')])
    reported_breaking = summary.get('breaking_changes', 0)

    if actual_breaking != reported_breaking:
        validation_results['issues'].append({
            "check": "breaking_change_count",
            "issue": f"Summary reports {reported_breaking} breaking changes but {actual_breaking} found",
            "severity": "high"
        })

    # Check 6: Validate version increment logic
    current_version = delta.get('delta_metadata', {}).get('current_version', '1.0.0')
    target_version = delta.get('delta_metadata', {}).get('target_version', '1.0.0')
    has_breaking = summary.get('breaking_changes', 0) > 0

    # Parse versions
    try:
        current_parts = [int(x) for x in current_version.split('+')[0].split('.')]
        target_parts = [int(x) for x in target_version.split('+')[0].split('.')]

        if has_breaking:
            # Should increment major version
            if target_parts[0] <= current_parts[0]:
                validation_results['issues'].append({
                    "check": "version_increment",
                    "issue": f"Breaking changes present but major version not incremented: {current_version} → {target_version}",
                    "severity": "high",
                    "recommendation": "Increment major version for breaking changes"
                })
        else:
            # Should increment minor version
            if target_parts[0] != current_parts[0]:
                validation_results['warnings'].append({
                    "check": "version_increment",
                    "warning": f"Major version incremented ({current_version} → {target_version}) but no breaking changes flagged",
                    "severity": "medium"
                })
    except:
        validation_results['warnings'].append({
            "check": "version_format",
            "warning": f"Could not parse version format: {current_version} → {target_version}",
            "severity": "low"
        })

    # Info messages
    if not check_source:
        validation_results['info'].append({
            "info": "Source code validation skipped (source directory not available)"
        })

    validation_results['info'].append({
        "info": f"Validated {actual_change_count} changes"
    })

    return validation_results

def validate_all_deltas(deltas_dir: Path, inventory_path: Path):
    """Validate all component deltas in directory"""

    print(f"=== Component Delta Validation v{VERSION} ===\n")
    print(f"Loading inventory from {inventory_path}")
    inventory = load_json(inventory_path)

    delta_files = list(deltas_dir.glob("*_delta.json"))
    print(f"Found {len(delta_files)} delta files to validate\n")

    all_results = []

    for delta_file in delta_files:
        component_id = delta_file.stem.replace('_delta', '')

        print(f"{'='*60}")
        print(f"Validating: {delta_file.name}")
        print(f"{'='*60}")

        # Find component source location in inventory
        component = None
        for comp in inventory.get('components', []):
            if comp['component_id'] == component_id:
                component = comp
                break

        if not component:
            print(f"⚠️  WARNING: Component {component_id} not found in inventory")
            result = {
                "component_id": component_id,
                "validation_passed": False,
                "issues": [{
                    "issue": "Component not found in inventory",
                    "severity": "critical"
                }]
            }
            all_results.append(result)
            continue

        # Get source location
        source_location = component.get('source_location', {}).get('url', '')
        check_source = False

        if source_location and Path(source_location).exists():
            source_dir = Path(source_location)
            check_source = True
            print(f"Source location: {source_dir}")
        else:
            source_dir = Path('.')  # Dummy
            print(f"⚠️  Source location not available - skipping source code checks")

        # Load and validate delta
        delta = load_json(delta_file)
        result = validate_single_delta(delta, source_dir, check_source)
        all_results.append(result)

    # Print summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")

    total_passed = sum(1 for r in all_results if r['validation_passed'])
    total_failed = len(all_results) - total_passed
    total_issues = sum(len(r.get('issues', [])) for r in all_results)
    total_warnings = sum(len(r.get('warnings', [])) for r in all_results)

    print(f"Total deltas validated: {len(all_results)}")
    print(f"✓ Passed: {total_passed}")
    print(f"✗ Failed: {total_failed}")
    print(f"  Total issues: {total_issues}")
    print(f"  Total warnings: {total_warnings}")

    # Detail failures
    for result in all_results:
        if not result['validation_passed']:
            print(f"\n✗ FAILED: {result['component_id']}")
            for issue in result['issues']:
                severity = issue.get('severity', 'unknown')
                print(f"  [{severity.upper()}] {issue.get('issue')}")
                if 'recommendation' in issue:
                    print(f"    → {issue['recommendation']}")

    # Detail warnings
    if total_warnings > 0:
        print(f"\n{'='*60}")
        print("WARNINGS")
        print(f"{'='*60}")
        for result in all_results:
            if result.get('warnings'):
                print(f"\n⚠️  {result['component_id']} ({len(result['warnings'])} warnings):")
                for warning in result['warnings']:
                    print(f"  - {warning.get('warning')}")

    return all_results

def main():
    parser = argparse.ArgumentParser(description="Validate component deltas for feasibility and correctness")
    parser.add_argument('--component-delta', help="Path to single component delta JSON")
    parser.add_argument('--component-source', help="Path to component source directory")
    parser.add_argument('--all-deltas', help="Path to directory containing all delta JSON files")
    parser.add_argument('--inventory', help="Path to component_inventory.json (required with --all-deltas)")
    parser.add_argument('--check-feasibility', action='store_true', help="Check feasibility against source code")

    args = parser.parse_args()

    if args.all_deltas:
        # Validate all deltas
        if not args.inventory:
            print("ERROR: --inventory required when using --all-deltas")
            return 1

        deltas_dir = Path(args.all_deltas)
        inventory_path = Path(args.inventory)

        if not deltas_dir.exists():
            print(f"ERROR: Deltas directory not found: {deltas_dir}")
            return 1

        if not inventory_path.exists():
            print(f"ERROR: Inventory file not found: {inventory_path}")
            return 1

        results = validate_all_deltas(deltas_dir, inventory_path)

        # Return non-zero if any failed
        if any(not r['validation_passed'] for r in results):
            return 1
        return 0

    elif args.component_delta:
        # Validate single delta
        delta_path = Path(args.component_delta)

        if not delta_path.exists():
            print(f"ERROR: Delta file not found: {delta_path}")
            return 1

        print(f"=== Component Delta Validation v{VERSION} ===\n")
        print(f"Loading delta from {delta_path}")
        delta = load_json(delta_path)

        # Determine source directory
        check_source = False
        source_dir = Path('.')

        if args.component_source:
            source_dir = Path(args.component_source)
            if not source_dir.exists():
                print(f"⚠️  WARNING: Source directory not found: {source_dir}")
                print("Proceeding with structure-only validation\n")
            else:
                check_source = True
                print(f"Source directory: {source_dir}\n")
        elif args.check_feasibility:
            print("⚠️  WARNING: --check-feasibility specified but no --component-source provided")
            print("Proceeding with structure-only validation\n")

        # Validate
        result = validate_single_delta(delta, source_dir, check_source)

        # Print results
        print(f"\n{'='*60}")
        if result['validation_passed']:
            print("✓ VALIDATION PASSED")
        else:
            print("✗ VALIDATION FAILED")
        print(f"{'='*60}")

        if result['issues']:
            print(f"\nIssues found: {len(result['issues'])}")
            for issue in result['issues']:
                severity = issue.get('severity', 'unknown')
                print(f"  [{severity.upper()}] {issue.get('issue')}")
                if 'recommendation' in issue:
                    print(f"    → {issue['recommendation']}")

        if result['warnings']:
            print(f"\nWarnings: {len(result['warnings'])}")
            for warning in result['warnings']:
                print(f"  - {warning.get('warning')}")

        if result['info']:
            print(f"\nInfo:")
            for info in result['info']:
                print(f"  ℹ️  {info.get('info')}")

        return 0 if result['validation_passed'] else 1

    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    exit(main())
