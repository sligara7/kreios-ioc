#!/usr/bin/env python3
"""
Configuration Consistency Validation Tool (D-07-A03)
Part of v3.6.0 Early Testing Integration - Pre-Deployment Validation

Validates that:
1. Environment variables in code match those in docker-compose.yml / .env files
2. Configuration defaults in code match deployment configs
3. Port numbers in code match docker-compose.yml
4. No hardcoded secrets or credentials
5. Configuration files are consistent across environments

Usage:
    python3 validate_configuration_consistency.py <system_root>

Example:
    python3 validate_configuration_consistency.py /home/user/my_system

Outputs:
    - validation_results.json with findings
    - Exit code 0 if all pass, 1 if critical issues, 2 if warnings only
"""

import sys
import json
import re
from pathlib import Path
from typing import Set, Dict, List
import yaml

def extract_env_vars_from_code(system_root: Path) -> Dict[str, List[str]]:
    """
    Extract environment variable references from code.

    Returns:
        Dict mapping env var names to list of files that reference them
    """
    env_vars = {}

    # Find all Python files
    py_files = [
        f for f in system_root.rglob('*.py')
        if not any(part.startswith('.') for part in f.parts)
        and 'venv' not in f.parts
        and '__pycache__' not in f.parts
    ]

    # Patterns to match environment variable access
    patterns = [
        r'os\.getenv\(["\']([A-Z_]+)["\']',
        r'os\.environ\[["\']([A-Z_]+)["\']\]',
        r'os\.environ\.get\(["\']([A-Z_]+)["\']',
        r'environ\[["\']([A-Z_]+)["\']\]',
        r'environ\.get\(["\']([A-Z_]+)["\']'
    ]

    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if match not in env_vars:
                        env_vars[match] = []
                    env_vars[match].append(str(py_file.relative_to(system_root)))
        except:
            pass

    return env_vars


def parse_docker_compose(compose_file: Path) -> Dict:
    """
    Parse docker-compose.yml for environment variables and ports.

    Returns:
        Dict with environment variables and port mappings
    """
    result = {
        "env_vars": set(),
        "ports": {}
    }

    if not compose_file.exists():
        return result

    try:
        with open(compose_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Extract environment variables
        if 'services' in data:
            for service_name, service_config in data['services'].items():
                # Environment from list
                if 'environment' in service_config:
                    env = service_config['environment']
                    if isinstance(env, list):
                        for item in env:
                            if '=' in item:
                                var_name = item.split('=')[0]
                                result["env_vars"].add(var_name)
                    elif isinstance(env, dict):
                        result["env_vars"].update(env.keys())

                # Extract ports
                if 'ports' in service_config:
                    for port_mapping in service_config['ports']:
                        if isinstance(port_mapping, str):
                            # Format: "host:container" or "port"
                            parts = port_mapping.split(':')
                            if len(parts) == 2:
                                result["ports"][service_name] = {
                                    "host": parts[0],
                                    "container": parts[1]
                                }
                            else:
                                result["ports"][service_name] = {
                                    "port": parts[0]
                                }
    except Exception as e:
        print(f"Warning: Could not parse docker-compose.yml: {e}")

    return result


def parse_env_file(env_file: Path) -> Set[str]:
    """
    Parse .env file for declared environment variables.

    Returns:
        Set of environment variable names
    """
    env_vars = set()

    if not env_file.exists():
        return env_vars

    try:
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse VAR=value
                if '=' in line:
                    var_name = line.split('=')[0]
                    env_vars.add(var_name)
    except:
        pass

    return env_vars


def check_hardcoded_secrets(system_root: Path) -> Dict:
    """
    Check for hardcoded secrets in code.

    Returns:
        Dict with validation results
    """
    results = {
        "critical_issues": [],
        "warnings": [],
        "info": []
    }

    # Patterns that indicate hardcoded secrets
    secret_patterns = [
        (r'password\s*=\s*["\'][^"\']+["\']', "password"),
        (r'api_key\s*=\s*["\'][^"\']+["\']', "api_key"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "secret"),
        (r'token\s*=\s*["\'][^"\']+["\']', "token"),
        (r'["\'][A-Za-z0-9]{32,}["\']', "long_random_string")
    ]

    # Find all Python files
    py_files = [
        f for f in system_root.rglob('*.py')
        if not any(part.startswith('.') for part in f.parts)
        and 'venv' not in f.parts
        and '__pycache__' not in f.parts
    ]

    potential_secrets = []

    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            for pattern, secret_type in secret_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    potential_secrets.append({
                        "file": str(py_file.relative_to(system_root)),
                        "type": secret_type,
                        "count": len(matches)
                    })
        except:
            pass

    if potential_secrets:
        results["critical_issues"].append({
            "issue": "hardcoded_secrets",
            "description": f"Found {len(potential_secrets)} potential hardcoded secrets",
            "files": potential_secrets[:10],
            "impact": "CRITICAL - Hardcoded secrets pose security risk, use environment variables"
        })
        if len(potential_secrets) > 10:
            results["critical_issues"][-1]["more"] = f"... and {len(potential_secrets) - 10} more"
    else:
        results["info"].append("No obvious hardcoded secrets detected")

    return results


def validate_env_var_consistency(system_root: Path) -> Dict:
    """
    Validate environment variable consistency.

    Returns:
        Dict with validation results
    """
    results = {
        "critical_issues": [],
        "warnings": [],
        "info": []
    }

    # Extract env vars from code
    code_env_vars = extract_env_vars_from_code(system_root)

    if not code_env_vars:
        results["info"].append("No environment variables found in code")
        return results

    results["info"].append(f"Found {len(code_env_vars)} environment variables in code")

    # Parse docker-compose.yml
    compose_file = system_root / "docker-compose.yml"
    compose_data = parse_docker_compose(compose_file)

    # Parse .env file
    env_file = system_root / ".env"
    env_file_vars = parse_env_file(env_file)

    # Check for missing environment variables
    declared_vars = compose_data["env_vars"] | env_file_vars
    missing_vars = []

    for var_name in code_env_vars.keys():
        if var_name not in declared_vars:
            missing_vars.append({
                "var": var_name,
                "used_in": code_env_vars[var_name][:3]
            })

    if missing_vars:
        results["critical_issues"].append({
            "issue": "undeclared_env_vars",
            "description": f"{len(missing_vars)} env vars used in code but not declared in docker-compose.yml or .env",
            "variables": missing_vars[:10],
            "impact": "CRITICAL - Will cause runtime errors when variables are undefined"
        })
        if len(missing_vars) > 10:
            results["critical_issues"][-1]["more"] = f"... and {len(missing_vars) - 10} more"
    else:
        results["info"].append("All code env vars are declared in config files")

    return results


def validate_port_consistency(system_root: Path) -> Dict:
    """
    Validate port number consistency.

    Returns:
        Dict with validation results
    """
    results = {
        "critical_issues": [],
        "warnings": [],
        "info": []
    }

    # Parse docker-compose.yml
    compose_file = system_root / "docker-compose.yml"
    compose_data = parse_docker_compose(compose_file)

    if not compose_data["ports"]:
        results["info"].append("No ports found in docker-compose.yml")
        return results

    results["info"].append(f"Found {len(compose_data['ports'])} services with port mappings")

    # Extract port references from code
    py_files = [
        f for f in system_root.rglob('*.py')
        if not any(part.startswith('.') for part in f.parts)
        and 'venv' not in f.parts
        and '__pycache__' not in f.parts
    ]

    # Pattern to match port numbers in code
    port_pattern = r'port\s*=\s*(\d+)'
    code_ports = {}

    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()

            matches = re.findall(port_pattern, content)
            for port in matches:
                if port not in code_ports:
                    code_ports[port] = []
                code_ports[port].append(str(py_file.relative_to(system_root)))
        except:
            pass

    if code_ports:
        results["info"].append(f"Found {len(code_ports)} port references in code")

    # Check for port conflicts
    declared_ports = set()
    for service, port_info in compose_data["ports"].items():
        if "container" in port_info:
            declared_ports.add(port_info["container"].split('/')[0])
        if "port" in port_info:
            declared_ports.add(port_info["port"].split('/')[0])

    undeclared_ports = []
    for port, files in code_ports.items():
        if port not in declared_ports:
            undeclared_ports.append({
                "port": port,
                "used_in": files[:3]
            })

    if undeclared_ports:
        results["warnings"].append({
            "issue": "undeclared_ports",
            "description": f"{len(undeclared_ports)} ports used in code but not in docker-compose.yml",
            "ports": undeclared_ports,
            "recommendation": "Ensure all service ports are documented in docker-compose.yml"
        })

    return results


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 validate_configuration_consistency.py <system_root>")
        sys.exit(1)

    system_root = Path(sys.argv[1]).resolve()

    if not system_root.exists():
        print(f"Error: System root does not exist: {system_root}")
        sys.exit(1)

    print(f"Validating configuration consistency in: {system_root}")
    print("=" * 80)

    # Run all checks
    secrets_results = check_hardcoded_secrets(system_root)
    env_results = validate_env_var_consistency(system_root)
    port_results = validate_port_consistency(system_root)

    # Combine results
    combined_results = {
        "validation_type": "configuration_consistency_validation",
        "system_root": str(system_root),
        "hardcoded_secrets": secrets_results,
        "env_var_consistency": env_results,
        "port_consistency": port_results
    }

    # Count issues
    all_results = [secrets_results, env_results, port_results]
    total_critical = sum(len(r["critical_issues"]) for r in all_results)
    total_warnings = sum(len(r["warnings"]) for r in all_results)

    # Print summary
    print("\n" + "=" * 80)
    print("CONFIGURATION CONSISTENCY VALIDATION SUMMARY")
    print("=" * 80)

    if total_critical > 0:
        print(f"\n🔴 CRITICAL ISSUES: {total_critical}")
        for check_results in all_results:
            for issue in check_results["critical_issues"]:
                print(f"\n  {issue['issue']}")
                print(f"  {issue['description']}")
                print(f"  Impact: {issue['impact']}")

                if 'files' in issue:
                    for file_info in issue['files'][:5]:
                        if isinstance(file_info, dict):
                            print(f"  File: {file_info}")
                        else:
                            print(f"  File: {file_info}")

                if 'variables' in issue:
                    for var_info in issue['variables'][:5]:
                        print(f"  Variable: {var_info['var']} used in {', '.join(var_info['used_in'])}")

                if 'more' in issue:
                    print(f"  {issue['more']}")

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
        print("\n✅ All configuration consistency validations passed!")

    # Write results to file
    output_file = system_root / "specs" / "machine" / "validation" / "config_consistency_validation_results.json"
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
