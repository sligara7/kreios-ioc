#!/usr/bin/env python3
"""
Module Structure Validation Tool (D-07-A02)
Part of v3.6.0 Early Testing Integration - Pre-Deployment Validation

Validates that:
1. All packages have __init__.py files (Python)
2. No circular imports exist
3. Module naming conventions are followed
4. No name shadowing of standard library modules

Usage:
    python3 validate_module_structure.py <system_root>

Example:
    python3 validate_module_structure.py /home/user/my_system

Outputs:
    - validation_results.json with findings
    - Exit code 0 if all pass, 1 if critical issues, 2 if warnings only
"""

import sys
import json
import ast
from pathlib import Path
from typing import Set, Dict, List, Tuple
from collections import defaultdict
import re

def find_python_packages(system_root: Path) -> List[Path]:
    """
    Find all Python packages (directories with .py files).

    Returns:
        List of directory paths that contain Python files
    """
    packages = set()

    for py_file in system_root.rglob('*.py'):
        # Skip hidden directories, venv, __pycache__
        if any(part.startswith('.') for part in py_file.parts):
            continue
        if 'venv' in py_file.parts or '__pycache__' in py_file.parts:
            continue

        # Add parent directory as a package
        packages.add(py_file.parent)

    return sorted(packages)


def check_init_files(packages: List[Path], system_root: Path) -> Dict:
    """
    Check that all Python packages have __init__.py files.

    Returns:
        Dict with validation results
    """
    results = {
        "critical_issues": [],
        "warnings": [],
        "info": []
    }

    missing_init = []

    for pkg_dir in packages:
        init_file = pkg_dir / '__init__.py'

        # Skip if this is the root directory or a non-package directory
        if pkg_dir == system_root:
            continue

        # Check if directory has subdirectories with .py files (it's a package)
        has_submodules = any(
            f.suffix == '.py' and f.name != '__init__.py'
            for f in pkg_dir.iterdir()
            if f.is_file()
        )

        if has_submodules and not init_file.exists():
            missing_init.append(str(pkg_dir.relative_to(system_root)))

    if missing_init:
        results["critical_issues"].append({
            "issue": "missing_init_files",
            "description": f"{len(missing_init)} packages missing __init__.py",
            "packages": sorted(missing_init),
            "impact": "CRITICAL - Python may not recognize these as packages, imports will fail"
        })
    else:
        results["info"].append("All packages have __init__.py files")

    return results


def extract_imports_with_location(file_path: Path) -> List[Tuple[str, int]]:
    """
    Extract imports with line numbers.

    Returns:
        List of (module_name, line_number) tuples
    """
    imports = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append((alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append((node.module, node.lineno))
    except:
        pass

    return imports


def build_import_graph(system_root: Path) -> Dict[Path, Set[Path]]:
    """
    Build a graph of module imports.

    Returns:
        Dict mapping file paths to set of imported file paths
    """
    graph = defaultdict(set)

    # Find all Python files
    py_files = [
        f for f in system_root.rglob('*.py')
        if not any(part.startswith('.') for part in f.parts)
        and 'venv' not in f.parts
        and '__pycache__' not in f.parts
    ]

    # Build mapping of module names to file paths
    module_to_file = {}
    for py_file in py_files:
        rel_path = py_file.relative_to(system_root)
        # Convert file path to module name (e.g., services/auth/handler.py → services.auth.handler)
        module_name = '.'.join(rel_path.with_suffix('').parts)
        module_to_file[module_name] = py_file

    # Build import graph
    for py_file in py_files:
        imports = extract_imports_with_location(py_file)

        for imp_module, _ in imports:
            # Try to match import to a file in the system
            if imp_module in module_to_file:
                graph[py_file].add(module_to_file[imp_module])

            # Try partial matches (e.g., 'services.auth' might import 'services.auth.handler')
            for mod_name, mod_file in module_to_file.items():
                if mod_name.startswith(imp_module + '.'):
                    graph[py_file].add(mod_file)

    return graph


def detect_circular_imports(import_graph: Dict[Path, Set[Path]], system_root: Path) -> List[List[Path]]:
    """
    Detect circular imports using DFS.

    Returns:
        List of cycles, where each cycle is a list of file paths
    """
    cycles = []
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node: Path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in import_graph.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found a cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)

        path.pop()
        rec_stack.remove(node)
        return False

    for node in import_graph:
        if node not in visited:
            dfs(node)

    return cycles


def check_circular_imports(system_root: Path) -> Dict:
    """
    Check for circular imports.

    Returns:
        Dict with validation results
    """
    results = {
        "critical_issues": [],
        "warnings": [],
        "info": []
    }

    import_graph = build_import_graph(system_root)
    results["info"].append(f"Analyzed {len(import_graph)} Python modules")

    cycles = detect_circular_imports(import_graph, system_root)

    if cycles:
        cycle_strs = []
        for cycle in cycles[:5]:  # Limit to first 5 cycles
            cycle_str = ' → '.join([str(f.relative_to(system_root)) for f in cycle])
            cycle_strs.append(cycle_str)

        results["critical_issues"].append({
            "issue": "circular_imports",
            "description": f"Detected {len(cycles)} circular import(s)",
            "cycles": cycle_strs,
            "impact": "CRITICAL - May cause ImportError or AttributeError at runtime"
        })
    else:
        results["info"].append("No circular imports detected")

    return results


def check_naming_conventions(system_root: Path) -> Dict:
    """
    Check module naming conventions.

    Returns:
        Dict with validation results
    """
    results = {
        "critical_issues": [],
        "warnings": [],
        "info": []
    }

    # Find all Python files
    py_files = [
        f for f in system_root.rglob('*.py')
        if not any(part.startswith('.') for part in f.parts)
        and 'venv' not in f.parts
        and '__pycache__' not in f.parts
    ]

    # Check naming conventions
    invalid_names = []
    for py_file in py_files:
        module_name = py_file.stem

        # Skip __init__ and special files
        if module_name.startswith('__') and module_name.endswith('__'):
            continue

        # Check for valid Python identifier
        if not re.match(r'^[a-z_][a-z0-9_]*$', module_name):
            invalid_names.append({
                "file": str(py_file.relative_to(system_root)),
                "issue": "Module name should be lowercase with underscores (snake_case)"
            })

    if invalid_names:
        results["warnings"].append({
            "issue": "naming_conventions",
            "description": f"{len(invalid_names)} files violate Python naming conventions",
            "files": invalid_names,
            "recommendation": "Use lowercase_with_underscores for module names"
        })
    else:
        results["info"].append("All module names follow conventions")

    return results


def check_stdlib_shadowing(system_root: Path) -> Dict:
    """
    Check for modules that shadow standard library names.

    Returns:
        Dict with validation results
    """
    results = {
        "critical_issues": [],
        "warnings": [],
        "info": []
    }

    # Common stdlib modules that shouldn't be shadowed
    stdlib_modules = {
        'sys', 'os', 'json', 'ast', 're', 'pathlib', 'typing', 'collections',
        'itertools', 'functools', 'datetime', 'time', 'logging', 'argparse',
        'subprocess', 'shutil', 'tempfile', 'urllib', 'http', 'copy', 'math',
        'random', 'string', 'unittest', 'pytest', 'enum', 'dataclasses', 'abc',
        'asyncio', 'socket', 'threading', 'multiprocessing', 'queue', 'csv',
        'email', 'html', 'xml', 'sqlite3', 'pickle', 'struct', 'io', 'gc'
    }

    # Find all Python files
    py_files = [
        f for f in system_root.rglob('*.py')
        if not any(part.startswith('.') for part in f.parts)
        and 'venv' not in f.parts
        and '__pycache__' not in f.parts
    ]

    shadowing = []
    for py_file in py_files:
        module_name = py_file.stem

        if module_name in stdlib_modules:
            shadowing.append({
                "file": str(py_file.relative_to(system_root)),
                "shadows": module_name
            })

    if shadowing:
        results["critical_issues"].append({
            "issue": "stdlib_shadowing",
            "description": f"{len(shadowing)} modules shadow standard library names",
            "files": shadowing,
            "impact": "CRITICAL - Will prevent importing standard library modules, causing runtime errors"
        })
    else:
        results["info"].append("No standard library shadowing detected")

    return results


def check_package_structure(system_root: Path) -> Dict:
    """
    Check overall package structure health.

    Returns:
        Dict with validation results
    """
    results = {
        "critical_issues": [],
        "warnings": [],
        "info": []
    }

    # Find common package directories
    common_dirs = ['src', 'services', 'lib', 'app', 'tests']
    found_dirs = [d for d in common_dirs if (system_root / d).exists()]

    if found_dirs:
        results["info"].append(f"Found standard package directories: {', '.join(found_dirs)}")

    # Check for tests directory
    test_dirs = list(system_root.rglob('test*'))
    if not test_dirs:
        results["warnings"].append({
            "issue": "no_tests_directory",
            "description": "No tests directory found",
            "recommendation": "Create a 'tests' directory for unit/integration tests"
        })

    return results


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 validate_module_structure.py <system_root>")
        sys.exit(1)

    system_root = Path(sys.argv[1]).resolve()

    if not system_root.exists():
        print(f"Error: System root does not exist: {system_root}")
        sys.exit(1)

    print(f"Validating module structure in: {system_root}")
    print("=" * 80)

    # Find packages
    packages = find_python_packages(system_root)
    print(f"Found {len(packages)} Python package directories")

    # Run all checks
    init_results = check_init_files(packages, system_root)
    circular_results = check_circular_imports(system_root)
    naming_results = check_naming_conventions(system_root)
    shadowing_results = check_stdlib_shadowing(system_root)
    structure_results = check_package_structure(system_root)

    # Combine results
    combined_results = {
        "validation_type": "module_structure_validation",
        "system_root": str(system_root),
        "init_files": init_results,
        "circular_imports": circular_results,
        "naming_conventions": naming_results,
        "stdlib_shadowing": shadowing_results,
        "package_structure": structure_results
    }

    # Count issues
    all_results = [init_results, circular_results, naming_results, shadowing_results, structure_results]
    total_critical = sum(len(r["critical_issues"]) for r in all_results)
    total_warnings = sum(len(r["warnings"]) for r in all_results)

    # Print summary
    print("\n" + "=" * 80)
    print("MODULE STRUCTURE VALIDATION SUMMARY")
    print("=" * 80)

    if total_critical > 0:
        print(f"\n🔴 CRITICAL ISSUES: {total_critical}")
        for check_results in all_results:
            for issue in check_results["critical_issues"]:
                print(f"\n  {issue['issue']}")
                print(f"  {issue['description']}")
                print(f"  Impact: {issue['impact']}")

                if 'packages' in issue:
                    print(f"  Packages: {', '.join(issue['packages'][:5])}")
                    if len(issue['packages']) > 5:
                        print(f"  ... and {len(issue['packages']) - 5} more")

                if 'cycles' in issue:
                    for cycle in issue['cycles']:
                        print(f"  Cycle: {cycle}")

                if 'files' in issue:
                    for file_info in issue['files'][:5]:
                        if isinstance(file_info, dict):
                            print(f"  File: {file_info.get('file', file_info)}")
                        else:
                            print(f"  File: {file_info}")
                    if len(issue['files']) > 5:
                        print(f"  ... and {len(issue['files']) - 5} more")

    if total_warnings > 0:
        print(f"\n⚠️  WARNINGS: {total_warnings}")
        for check_results in all_results:
            for warning in check_results["warnings"]:
                if isinstance(warning, dict):
                    print(f"\n  {warning['issue']}")
                    print(f"  {warning['description']}")
                    if 'recommendation' in warning:
                        print(f"  Recommendation: {warning['recommendation']}")
                else:
                    print(f"  {warning}")

    if total_critical == 0 and total_warnings == 0:
        print("\n✅ All module structure validations passed!")

    # Write results to file
    output_file = system_root / "specs" / "machine" / "validation" / "module_structure_validation_results.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(combined_results, f, indent=2)

    print(f"\nDetailed results written to: {output_file}")

    # Exit with appropriate code
    if total_critical > 0:
        print("\n❌ VALIDATION FAILED - Critical issues detected")
        sys.exit(1)
    elif total_warnings > 0:
        print("\n⚠️  VALIDATION PASSED WITH WARNINGS")
        sys.exit(2)
    else:
        print("\n✅ VALIDATION PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
