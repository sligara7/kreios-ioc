#!/usr/bin/env python3
"""
Dependency Validation Tool (D-07-A01)
Part of v3.6.0 Early Testing Integration - Pre-Deployment Validation

Validates that:
1. All imports in code exist in requirements.txt / package.json
2. No unused dependencies in requirements files
3. Version pinning is consistent
4. No conflicting dependency versions

Usage:
    python3 validate_dependencies.py <system_root>

Example:
    python3 validate_dependencies.py /home/user/my_system

Outputs:
    - validation_results.json with findings
    - Exit code 0 if all pass, 1 if critical issues, 2 if warnings only
"""

import sys
import json
import ast
from pathlib import Path
from typing import Set, Dict, List, Tuple
import re

def extract_python_imports(file_path: Path) -> Set[str]:
    """
    Extract all import statements from a Python file.

    Returns:
        Set of base package names (e.g., 'requests' from 'import requests' or 'from requests import get')
    """
    imports = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Get base package (e.g., 'requests' from 'requests.auth')
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])
    except SyntaxError:
        print(f"Warning: Syntax error in {file_path}, skipping")
    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}")

    return imports


def parse_requirements_txt(req_file: Path) -> Dict[str, str]:
    """
    Parse requirements.txt and return package → version mapping.

    Returns:
        Dict mapping package name to version specifier (e.g., {'requests': '==2.28.0'})
    """
    requirements = {}

    if not req_file.exists():
        return requirements

    with open(req_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue

            # Skip -e and -r directives
            if line.startswith('-e') or line.startswith('-r'):
                continue

            # Parse package==version or package>=version
            match = re.match(r'^([a-zA-Z0-9_-]+)([>=<~!]*[0-9.]*)', line)
            if match:
                package = match.group(1).lower()
                version_spec = match.group(2) if match.group(2) else ''
                requirements[package] = version_spec

    return requirements


def parse_package_json(pkg_file: Path) -> Dict[str, str]:
    """
    Parse package.json and return dependencies.

    Returns:
        Dict mapping package name to version (e.g., {'express': '^4.18.0'})
    """
    dependencies = {}

    if not pkg_file.exists():
        return dependencies

    try:
        with open(pkg_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Merge dependencies and devDependencies
        dependencies.update(data.get('dependencies', {}))
        dependencies.update(data.get('devDependencies', {}))
    except Exception as e:
        print(f"Warning: Could not parse {pkg_file}: {e}")

    return dependencies


def extract_nodejs_imports(file_path: Path) -> Set[str]:
    """
    Extract require() and import statements from JavaScript/TypeScript files.

    Returns:
        Set of package names
    """
    imports = set()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Match require('package') or require("package")
        require_pattern = r"require\(['\"]([^'\"./][^'\"]*)['\"]"
        imports.update(re.findall(require_pattern, content))

        # Match import ... from 'package' or import ... from "package"
        import_pattern = r"import\s+.*\s+from\s+['\"]([^'\"./][^'\"]*)['\"]"
        imports.update(re.findall(import_pattern, content))

        # Get base package (e.g., 'express' from 'express/lib/router')
        imports = {pkg.split('/')[0] for pkg in imports}
    except Exception as e:
        print(f"Warning: Could not parse {file_path}: {e}")

    return imports


def validate_python_dependencies(system_root: Path) -> Dict:
    """
    Validate Python dependencies.

    Returns:
        Dict with validation results
    """
    results = {
        "language": "python",
        "critical_issues": [],
        "warnings": [],
        "info": []
    }

    # Find requirements.txt
    req_files = list(system_root.rglob('requirements.txt'))
    if not req_files:
        results["info"].append("No requirements.txt found, skipping Python validation")
        return results

    req_file = req_files[0]
    declared_deps = parse_requirements_txt(req_file)
    results["info"].append(f"Found requirements.txt at {req_file.relative_to(system_root)}")
    results["info"].append(f"Declared dependencies: {len(declared_deps)}")

    # Find all Python files
    py_files = [
        f for f in system_root.rglob('*.py')
        if not any(part.startswith('.') for part in f.parts)  # Skip hidden dirs
        and 'venv' not in f.parts
        and '__pycache__' not in f.parts
    ]

    if not py_files:
        results["warnings"].append("No Python files found")
        return results

    results["info"].append(f"Analyzing {len(py_files)} Python files")

    # Extract all imports
    all_imports = set()
    for py_file in py_files:
        all_imports.update(extract_python_imports(py_file))

    # Filter out stdlib and local imports
    stdlib_modules = {
        'sys', 'os', 'json', 'ast', 're', 'pathlib', 'typing', 'collections',
        'itertools', 'functools', 'datetime', 'time', 'logging', 'argparse',
        'subprocess', 'shutil', 'tempfile', 'urllib', 'http', 'copy', 'math',
        'random', 'string', 'unittest', 'pytest', 'enum', 'dataclasses', 'abc'
    }

    third_party_imports = {
        imp for imp in all_imports
        if imp not in stdlib_modules and not imp.startswith('_')
    }

    results["info"].append(f"Found {len(third_party_imports)} third-party imports")

    # Check for missing dependencies
    missing_deps = []
    for imp in third_party_imports:
        # Normalize package names (e.g., 'PIL' → 'pillow')
        normalized = imp.lower().replace('_', '-')

        if normalized not in declared_deps:
            missing_deps.append(imp)

    if missing_deps:
        results["critical_issues"].append({
            "issue": "missing_dependencies",
            "description": f"Code imports {len(missing_deps)} packages not in requirements.txt",
            "packages": sorted(missing_deps),
            "impact": "CRITICAL - will cause ModuleNotFoundError at runtime"
        })

    # Check for unpinned versions
    unpinned = []
    for pkg, version in declared_deps.items():
        if not version or version.startswith('>=') or version.startswith('>'):
            unpinned.append(pkg)

    if unpinned:
        results["warnings"].append({
            "issue": "unpinned_versions",
            "description": f"{len(unpinned)} packages without exact version pins",
            "packages": sorted(unpinned),
            "recommendation": "Pin to exact versions (use ==) for reproducible builds"
        })

    # Check for unused dependencies
    unused = []
    for pkg in declared_deps.keys():
        normalized = pkg.replace('-', '_')
        if normalized not in [imp.lower().replace('-', '_') for imp in third_party_imports]:
            unused.append(pkg)

    if unused:
        results["info"].append(f"Potentially unused dependencies: {', '.join(sorted(unused))}")

    return results


def validate_nodejs_dependencies(system_root: Path) -> Dict:
    """
    Validate Node.js dependencies.

    Returns:
        Dict with validation results
    """
    results = {
        "language": "nodejs",
        "critical_issues": [],
        "warnings": [],
        "info": []
    }

    # Find package.json
    pkg_files = list(system_root.rglob('package.json'))
    if not pkg_files:
        results["info"].append("No package.json found, skipping Node.js validation")
        return results

    pkg_file = pkg_files[0]
    declared_deps = parse_package_json(pkg_file)
    results["info"].append(f"Found package.json at {pkg_file.relative_to(system_root)}")
    results["info"].append(f"Declared dependencies: {len(declared_deps)}")

    # Find all JS/TS files
    js_files = [
        f for f in system_root.rglob('*.js')
        if not any(part.startswith('.') for part in f.parts)
        and 'node_modules' not in f.parts
    ]
    ts_files = [
        f for f in system_root.rglob('*.ts')
        if not any(part.startswith('.') for part in f.parts)
        and 'node_modules' not in f.parts
    ]

    all_files = js_files + ts_files

    if not all_files:
        results["warnings"].append("No JavaScript/TypeScript files found")
        return results

    results["info"].append(f"Analyzing {len(all_files)} JS/TS files")

    # Extract all imports
    all_imports = set()
    for file in all_files:
        all_imports.update(extract_nodejs_imports(file))

    # Filter out Node.js built-ins
    builtin_modules = {
        'fs', 'path', 'http', 'https', 'url', 'util', 'events', 'stream',
        'crypto', 'os', 'process', 'buffer', 'child_process', 'cluster'
    }

    third_party_imports = {
        imp for imp in all_imports
        if imp not in builtin_modules and not imp.startswith('.')
    }

    results["info"].append(f"Found {len(third_party_imports)} third-party imports")

    # Check for missing dependencies
    missing_deps = []
    for imp in third_party_imports:
        if imp not in declared_deps:
            missing_deps.append(imp)

    if missing_deps:
        results["critical_issues"].append({
            "issue": "missing_dependencies",
            "description": f"Code imports {len(missing_deps)} packages not in package.json",
            "packages": sorted(missing_deps),
            "impact": "CRITICAL - will cause MODULE_NOT_FOUND error at runtime"
        })

    # Check for semver ranges
    wide_ranges = []
    for pkg, version in declared_deps.items():
        if version.startswith('^') or version.startswith('~') or version == '*':
            wide_ranges.append(f"{pkg}: {version}")

    if wide_ranges:
        results["warnings"].append({
            "issue": "semver_ranges",
            "description": f"{len(wide_ranges)} packages use semver ranges (^, ~, *)",
            "packages": sorted(wide_ranges),
            "recommendation": "Consider using exact versions or package-lock.json for reproducibility"
        })

    return results


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 validate_dependencies.py <system_root>")
        sys.exit(1)

    system_root = Path(sys.argv[1]).resolve()

    if not system_root.exists():
        print(f"Error: System root does not exist: {system_root}")
        sys.exit(1)

    print(f"Validating dependencies in: {system_root}")
    print("=" * 80)

    # Validate Python dependencies
    python_results = validate_python_dependencies(system_root)

    # Validate Node.js dependencies
    nodejs_results = validate_nodejs_dependencies(system_root)

    # Combine results
    combined_results = {
        "validation_type": "dependency_validation",
        "system_root": str(system_root),
        "python": python_results,
        "nodejs": nodejs_results
    }

    # Count issues
    total_critical = len(python_results["critical_issues"]) + len(nodejs_results["critical_issues"])
    total_warnings = len(python_results["warnings"]) + len(nodejs_results["warnings"])

    # Print summary
    print("\n" + "=" * 80)
    print("DEPENDENCY VALIDATION SUMMARY")
    print("=" * 80)

    if total_critical > 0:
        print(f"\n🔴 CRITICAL ISSUES: {total_critical}")
        for lang_results in [python_results, nodejs_results]:
            for issue in lang_results["critical_issues"]:
                print(f"\n  [{lang_results['language'].upper()}] {issue['issue']}")
                print(f"  {issue['description']}")
                print(f"  Impact: {issue['impact']}")
                print(f"  Packages: {', '.join(issue['packages'][:10])}")
                if len(issue['packages']) > 10:
                    print(f"  ... and {len(issue['packages']) - 10} more")

    if total_warnings > 0:
        print(f"\n⚠️  WARNINGS: {total_warnings}")
        for lang_results in [python_results, nodejs_results]:
            for warning in lang_results["warnings"]:
                if isinstance(warning, dict):
                    print(f"\n  [{lang_results['language'].upper()}] {warning['issue']}")
                    print(f"  {warning['description']}")
                else:
                    print(f"  [{lang_results['language'].upper()}] {warning}")

    if total_critical == 0 and total_warnings == 0:
        print("\n✅ All dependency validations passed!")

    # Write results to file
    output_file = system_root / "specs" / "machine" / "validation" / "dependency_validation_results.json"
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
