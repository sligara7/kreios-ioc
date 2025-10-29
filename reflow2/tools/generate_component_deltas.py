#!/usr/bin/env python3
"""
Generate Component Deltas Tool - PRODUCTION VERSION
Generates EXACT component-level changes (function/class/module level) required for integration

This is THE CRITICAL TOOL for bottom-up integration - generates exact code changes needed.

Usage:
    python3 generate_component_deltas.py \\
        --component <component_id> \\
        --gaps <path_to_integration_gaps.json> \\
        --inventory <path_to_component_inventory.json> \\
        --output <path_to_component_delta.json> \\
        --granularity <function|class|module|file>
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import re

VERSION = "2.0.0"

def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(data: Dict[str, Any], file_path: Path):
    """Save JSON file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def get_component_by_id(component_id: str, inventory: Dict) -> Dict | None:
    """Find component in inventory by ID"""
    for comp in inventory.get('components', []):
        if comp.get('component_id') == component_id:
            return comp
    return None

def calculate_version_increment(current_version: str, has_breaking_changes: bool) -> str:
    """
    Calculate new version based on semver and breaking changes

    Rules:
    - Breaking changes → increment MAJOR
    - Non-breaking changes → increment MINOR
    """
    # Parse current version (e.g., "2.3.1" or "2.3.1+2025-10-26")
    version_parts = current_version.split('+')[0].split('.')

    try:
        major = int(version_parts[0])
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
        patch = int(version_parts[2]) if len(version_parts) > 2 else 0
    except:
        # Default if parsing fails
        major, minor, patch = 1, 0, 0

    if has_breaking_changes:
        major += 1
        minor = 0
        patch = 0
    else:
        minor += 1
        patch = 0

    return f"{major}.{minor}.{patch}"

# ============================================================================
# DELTA GENERATORS BY GAP TYPE
# ============================================================================

def generate_delta_for_missing_interface(gap: Dict, component: Dict, component_id: str,
                                          is_provider: bool, granularity: str) -> List[Dict]:
    """
    Generate deltas for missing_interface gap

    Two scenarios:
    1. Component is provider (to_component) - needs to expose new interface
    2. Component is consumer (from_component) - needs to call new interface
    """
    deltas = []
    change_counter = 1

    to_comp = gap.get('to_component')
    from_comp = gap.get('from_component')

    if is_provider:
        # This component needs to expose an interface

        # Delta 1: Create new API endpoint or function
        language = component.get('constraints', {}).get('language', 'python')

        if language == 'python':
            # Check component type to determine interface style
            comp_type = component.get('component_type', 'python_package')

            if 'service' in comp_type.lower():
                # REST API endpoint
                deltas.append({
                    "change_id": f"DELTA-{component_id.upper()}-{change_counter:03d}",
                    "change_type": "new_function",
                    "tier_level": component.get('tier_classification'),
                    "location": f"src/{component_id}/api/routes.py",
                    "scope": "function",
                    "change_description": f"Add REST API endpoint for {from_comp} to call",
                    "rationale": f"Resolve gap {gap.get('gap_id')}: {from_comp} needs to communicate with this component",
                    "breaking_change": False,
                    "backward_compatible": True,
                    "new_implementation": {
                        "function_signature": f"@app.route('/api/v1/{component_id}/action', methods=['POST'])\ndef handle_{from_comp}_request():",
                        "function_body": """
    # Parse request data
    data = request.get_json()

    # Validate input
    if not data or 'required_field' not in data:
        return jsonify({'error': 'Missing required field'}), 400

    # Process request
    result = process_request(data)

    # Return response
    return jsonify(result), 200
""",
                        "dependencies_added": ["flask"],
                        "imports_added": ["from flask import request, jsonify"],
                        "docstring": f"Handle requests from {from_comp}",
                        "type_hints": True,
                        "async_function": False
                    },
                    "test_requirements": [
                        f"Unit test: test_handle_{from_comp}_request_success()",
                        f"Unit test: test_handle_{from_comp}_request_missing_field()",
                        f"Integration test: test_{from_comp}_to_{component_id}_integration()"
                    ],
                    "estimated_effort": "4 hours",
                    "priority": "critical",
                    "depends_on_changes": []
                })
            else:
                # Python function API
                deltas.append({
                    "change_id": f"DELTA-{component_id.upper()}-{change_counter:03d}",
                    "change_type": "new_function",
                    "tier_level": component.get('tier_classification'),
                    "location": f"src/{component_id}/api.py",
                    "scope": "function",
                    "change_description": f"Add Python function for {from_comp} to call",
                    "rationale": f"Resolve gap {gap.get('gap_id')}: expose functionality to {from_comp}",
                    "breaking_change": False,
                    "backward_compatible": True,
                    "new_implementation": {
                        "function_signature": f"def provide_service_to_{from_comp}(data: Dict[str, Any]) -> Dict[str, Any]:",
                        "function_body": """
    # Validate input
    if not data:
        raise ValueError('Data cannot be empty')

    # Process request
    result = process_data(data)

    return result
""",
                        "dependencies_added": [],
                        "imports_added": ["from typing import Dict, Any"],
                        "docstring": f"Provide service to {from_comp}",
                        "type_hints": True,
                        "async_function": False
                    },
                    "test_requirements": [
                        f"Unit test: test_provide_service_to_{from_comp}_success()",
                        f"Unit test: test_provide_service_to_{from_comp}_invalid_data()"
                    ],
                    "estimated_effort": "3 hours",
                    "priority": "critical"
                })
                change_counter += 1

    else:
        # This component is consumer - needs to call provider's interface

        # Delta 1: Create client/adapter to call provider
        deltas.append({
            "change_id": f"DELTA-{component_id.upper()}-{change_counter:03d}",
            "change_type": "new_module",
            "tier_level": component.get('tier_classification'),
            "location": f"src/{component_id}/clients/{to_comp}_client.py",
            "scope": "module",
            "change_description": f"Create client module to call {to_comp}",
            "rationale": f"Resolve gap {gap.get('gap_id')}: enable communication with {to_comp}",
            "breaking_change": False,
            "backward_compatible": True,
            "new_implementation": {
                "module_purpose": f"Client for communicating with {to_comp}",
                "classes": [
                    {
                        "class_name": f"{to_comp.title().replace('_', '')}Client",
                        "base_class": None,
                        "purpose": f"HTTP/API client for {to_comp}",
                        "methods": [
                            {
                                "method_name": "call_service",
                                "signature": "def call_service(self, data: Dict[str, Any]) -> Dict[str, Any]:",
                                "purpose": f"Call {to_comp} service",
                                "implementation_notes": f"Make HTTP POST to {to_comp} endpoint",
                                "returns": "Response data from service"
                            }
                        ],
                        "attributes": [
                            {
                                "name": "base_url",
                                "type": "str",
                                "default": f"os.getenv('{to_comp.upper()}_URL', 'http://localhost:8000')"
                            },
                            {
                                "name": "timeout",
                                "type": "int",
                                "default": "30"
                            }
                        ]
                    }
                ],
                "dependencies_added": ["requests>=2.31.0"],
                "imports_added": ["import requests", "import os", "from typing import Dict, Any"],
                "configuration_required": {
                    "environment_variables": [
                        {
                            "name": f"{to_comp.upper()}_URL",
                            "required": True,
                            "default": "http://localhost:8000",
                            "description": f"Base URL of {to_comp} service"
                        }
                    ]
                },
                "error_handling": {
                    "exceptions_raised": [f"{to_comp.title()}ServiceUnavailable", "RequestTimeout"],
                    "retry_logic": "Exponential backoff, max 3 retries",
                    "timeout_handling": "Raise RequestTimeout after 30 seconds"
                }
            },
            "test_requirements": [
                f"Unit test: test_{to_comp}_client_call_success()",
                f"Unit test: test_{to_comp}_client_timeout()",
                f"Integration test: test_{component_id}_to_{to_comp}_integration()"
            ],
            "estimated_effort": "5 hours",
            "priority": "critical"
        })
        change_counter += 1

        # Delta 2: Integrate client into component's main logic
        deltas.append({
            "change_id": f"DELTA-{component_id.upper()}-{change_counter:03d}",
            "change_type": "modify_function",
            "tier_level": component.get('tier_classification'),
            "location": f"src/{component_id}/main.py::main_function()",
            "scope": "function",
            "change_description": f"Integrate {to_comp}_client into main logic",
            "rationale": "Use newly created client to call provider service",
            "breaking_change": False,
            "backward_compatible": True,
            "current_state": {
                "exists": True,
                "current_code": "def main_function(): ..."
            },
            "new_implementation": {
                "changes": [
                    f"Import {to_comp}_client",
                    f"Instantiate client: client = {to_comp.title().replace('_', '')}Client()",
                    "Call client.call_service(data) at appropriate point",
                    "Handle response and errors"
                ],
                "imports_added": [f"from .clients.{to_comp}_client import {to_comp.title().replace('_', '')}Client"]
            },
            "test_requirements": [
                "Unit test: test_main_function_with_client_success()",
                "Unit test: test_main_function_client_failure_handling()"
            ],
            "estimated_effort": "2 hours",
            "priority": "high"
        })

    return deltas

def generate_delta_for_protocol_mismatch(gap: Dict, component: Dict, component_id: str, granularity: str) -> List[Dict]:
    """Generate deltas for protocol_mismatch gap"""
    deltas = []

    # Typically need adapter component - suggest creating one
    from_comp = gap.get('from_component')
    to_comp = gap.get('to_component')

    if component_id == from_comp:
        # This component needs protocol adapter
        deltas.append({
            "change_id": f"DELTA-{component_id.upper()}-001",
            "change_type": "new_module",
            "tier_level": component.get('tier_classification'),
            "location": f"src/{component_id}/adapters/protocol_adapter.py",
            "scope": "module",
            "change_description": f"Create protocol adapter to bridge {from_comp} to {to_comp}",
            "rationale": f"Resolve gap {gap.get('gap_id')}: protocol mismatch between components",
            "breaking_change": False,
            "new_implementation": {
                "module_purpose": "Protocol adapter for REST API communication",
                "classes": [
                    {
                        "class_name": "ProtocolAdapter",
                        "methods": [
                            {
                                "method_name": "adapt_request",
                                "signature": "def adapt_request(self, python_call_data: Dict) -> requests.Response:",
                                "purpose": "Convert Python function call to HTTP request"
                            }
                        ]
                    }
                ],
                "dependencies_added": ["requests>=2.31.0"]
            },
            "estimated_effort": "4 hours",
            "priority": "high"
        })

    return deltas

def generate_delta_for_version_incompatibility(gap: Dict, component: Dict, component_id: str, granularity: str) -> List[Dict]:
    """Generate deltas for version_incompatibility gap"""
    deltas = []

    # Extract version conflict info from gap description
    gap_desc = gap.get('gap_description', '')

    deltas.append({
        "change_id": f"DELTA-{component_id.upper()}-001",
        "change_type": "modify_dependencies",
        "tier_level": component.get('tier_classification'),
        "location": "requirements.txt OR setup.py OR pyproject.toml",
        "scope": "file",
        "change_description": "Update dependency versions to resolve conflicts",
        "rationale": f"Resolve gap {gap.get('gap_id')}: version incompatibility",
        "breaking_change": False,
        "new_implementation": {
            "dependency_changes": "Update to compatible version based on gap analysis",
            "testing_required": "Full regression testing after version upgrade"
        },
        "estimated_effort": "3 hours",
        "priority": "medium"
    })

    return deltas

def generate_delta_for_security_gap(gap: Dict, component: Dict, component_id: str, granularity: str) -> List[Dict]:
    """Generate deltas for security_gap gap"""
    deltas = []
    change_counter = 1

    gap_desc = gap.get('gap_description', '').lower()

    if 'authentication' in gap_desc:
        # Need to add authentication
        deltas.append({
            "change_id": f"DELTA-{component_id.upper()}-{change_counter:03d}",
            "change_type": "new_module",
            "tier_level": component.get('tier_classification'),
            "location": f"src/{component_id}/auth/authentication.py",
            "scope": "module",
            "change_description": "Add authentication module",
            "rationale": f"Resolve gap {gap.get('gap_id')}: missing authentication",
            "breaking_change": False,
            "new_implementation": {
                "module_purpose": "JWT-based authentication",
                "functions": [
                    {
                        "name": "verify_token",
                        "signature": "def verify_token(token: str) -> Dict[str, Any]:",
                        "purpose": "Verify JWT token and return user info"
                    },
                    {
                        "name": "require_auth",
                        "signature": "def require_auth(f):",
                        "purpose": "Decorator to require authentication on endpoints"
                    }
                ],
                "dependencies_added": ["PyJWT>=2.8.0"]
            },
            "configuration_changes": [
                {
                    "change_type": "new_environment_variable",
                    "variable_name": "JWT_SECRET_KEY",
                    "required": True,
                    "description": "Secret key for JWT token verification"
                }
            ],
            "estimated_effort": "6 hours",
            "priority": "critical"
        })
        change_counter += 1

        # Delta 2: Apply authentication to endpoints
        deltas.append({
            "change_id": f"DELTA-{component_id.upper()}-{change_counter:03d}",
            "change_type": "modify_function",
            "location": f"src/{component_id}/api/routes.py",
            "change_description": "Add @require_auth decorator to all endpoints",
            "rationale": "Enforce authentication on all API endpoints",
            "breaking_change": True,
            "backward_compatible": False,
            "estimated_effort": "2 hours",
            "priority": "critical"
        })

    if 'ssl' in gap_desc or 'tls' in gap_desc:
        # Need to add SSL/TLS
        deltas.append({
            "change_id": f"DELTA-{component_id.upper()}-{change_counter:03d}",
            "change_type": "configuration_change",
            "location": "deployment configuration",
            "change_description": "Enable SSL/TLS in web server configuration",
            "rationale": f"Resolve gap {gap.get('gap_id')}: missing encryption in transit",
            "breaking_change": False,
            "new_implementation": {
                "configuration_changes": "Add SSL certificate paths to server config",
                "infrastructure_changes": "Obtain and install SSL certificates"
            },
            "estimated_effort": "4 hours",
            "priority": "high"
        })

    return deltas

# ============================================================================
# MAIN DELTA GENERATION
# ============================================================================

def generate_deltas_for_component(component_id: str, gaps_data: Dict, inventory: Dict, granularity: str) -> Dict:
    """
    Generate exact deltas for a component based on integration gaps

    This is the CORE FUNCTION - generates precise code changes needed
    """

    print(f"\nGenerating deltas for component: {component_id}")
    print(f"Granularity: {granularity}")

    # Find component in inventory
    component = get_component_by_id(component_id, inventory)
    if not component:
        raise ValueError(f"Component {component_id} not found in inventory")

    # Find gaps affecting this component
    all_gaps = gaps_data.get('gaps', [])
    component_gaps = [
        g for g in all_gaps
        if g.get('from_component') == component_id or g.get('to_component') == component_id
    ]

    print(f"Found {len(component_gaps)} gaps affecting this component:")
    for gap in component_gaps:
        print(f"  - {gap.get('gap_id')}: {gap.get('gap_type')} (severity: {gap.get('severity')})")

    # Generate deltas for each gap
    all_deltas = []

    for gap in component_gaps:
        gap_type = gap.get('gap_type')
        gap_id = gap.get('gap_id')

        print(f"\nProcessing {gap_id} ({gap_type})...")

        # Determine if this component is provider or consumer
        is_provider = (gap.get('to_component') == component_id)

        # Generate deltas based on gap type
        if gap_type == 'missing_interface':
            deltas = generate_delta_for_missing_interface(gap, component, component_id, is_provider, granularity)
        elif gap_type == 'protocol_mismatch':
            deltas = generate_delta_for_protocol_mismatch(gap, component, component_id, granularity)
        elif gap_type == 'version_incompatibility':
            deltas = generate_delta_for_version_incompatibility(gap, component, component_id, granularity)
        elif gap_type == 'security_gap':
            deltas = generate_delta_for_security_gap(gap, component, component_id, granularity)
        else:
            # Generic delta for other gap types
            deltas = [{
                "change_id": f"DELTA-{component_id.upper()}-GENERIC",
                "change_type": "manual_analysis_required",
                "gap_type": gap_type,
                "gap_id": gap_id,
                "change_description": f"Manual analysis required for {gap_type}",
                "rationale": f"Gap type {gap_type} requires custom analysis",
                "estimated_effort": "TBD",
                "priority": gap.get('severity')
            }]

        print(f"  Generated {len(deltas)} delta(s)")
        all_deltas.extend(deltas)

    # Analyze breaking changes
    breaking_changes = [d for d in all_deltas if d.get('breaking_change')]
    has_breaking_changes = len(breaking_changes) > 0

    # Calculate version increment
    current_version = component.get('current_version', '1.0.0')
    target_version = calculate_version_increment(current_version, has_breaking_changes)

    # Collect dependency changes
    dependencies_added = []
    dependencies_removed = []

    for delta in all_deltas:
        impl = delta.get('new_implementation', {})
        if 'dependencies_added' in impl:
            dependencies_added.extend(impl['dependencies_added'])

    dependencies_added = list(set(dependencies_added))  # Remove duplicates

    # Collect configuration changes
    config_changes = []
    for delta in all_deltas:
        if delta.get('change_type') == 'configuration_change':
            config_changes.append(delta)
        impl = delta.get('new_implementation', {})
        if 'configuration_required' in impl:
            env_vars = impl['configuration_required'].get('environment_variables', [])
            for env_var in env_vars:
                config_changes.append({
                    "change_type": "new_environment_variable",
                    "variable_name": env_var.get('name'),
                    "required": env_var.get('required'),
                    "default_value": env_var.get('default'),
                    "description": env_var.get('description')
                })

    # Categorize changes by type
    changes_by_type = {}
    for delta in all_deltas:
        change_type = delta.get('change_type')
        if change_type not in changes_by_type:
            changes_by_type[change_type] = 0
        changes_by_type[change_type] += 1

    # Calculate total effort
    total_effort_hours = 0
    for delta in all_deltas:
        effort_str = delta.get('estimated_effort', '0 hours')
        try:
            hours = int(re.search(r'(\d+)', effort_str).group(1))
            total_effort_hours += hours
        except:
            pass

    # Assess risk level
    if has_breaking_changes or len(component_gaps) > 5:
        risk_level = "high"
    elif len(component_gaps) > 2:
        risk_level = "medium"
    else:
        risk_level = "low"

    # Create delta structure
    delta_output = {
        "delta_metadata": {
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "component_id": component_id,
            "component_name": component.get('component_name'),
            "current_version": current_version,
            "target_version": target_version,
            "delta_purpose": f"Enable integration for {component_id}",
            "based_on_gaps": [g['gap_id'] for g in component_gaps],
            "analyst": f"generate_component_deltas.py v{VERSION}",
            "granularity": granularity
        },
        "component_context": {
            "component_type": component.get('component_type'),
            "source_location": component.get('source_location') if isinstance(component.get('source_location'), str) else component.get('source_location', {}).get('url', 'Unknown'),
            "primary_language": component.get('constraints', {}).get('language', 'python'),
            "integration_role": "modified_for_integration"
        },
        "required_changes": all_deltas,
        "configuration_changes": config_changes,
        "dependency_changes": {
            "added": dependencies_added,
            "removed": dependencies_removed,
            "upgraded": []
        },
        "file_structure_changes": {
            "new_directories": list(set([str(Path(d.get('location', '')).parent) for d in all_deltas if d.get('change_type') == 'new_module'])),
            "new_files": [d.get('location') for d in all_deltas if d.get('change_type') in ['new_module', 'new_class', 'new_function']],
            "modified_files": [d.get('location') for d in all_deltas if d.get('change_type') in ['modify_function', 'modify_class', 'modify_module']]
        },
        "testing_requirements": {
            "new_unit_tests": [test for d in all_deltas for test in d.get('test_requirements', [])],
            "test_coverage_target": "≥80% for new code"
        },
        "summary": {
            "total_changes": len(all_deltas),
            "by_type": changes_by_type,
            "estimated_total_effort": f"{total_effort_hours} hours",
            "breaking_changes": len(breaking_changes),
            "backward_compatible": not has_breaking_changes,
            "test_count": len([test for d in all_deltas for test in d.get('test_requirements', [])]),
            "dependencies_added": len(dependencies_added),
            "files_affected": len(set([d.get('location') for d in all_deltas if d.get('location')])),
            "risk_level": risk_level
        },
        "next_steps": [
            "Review delta changes with component owner",
            "Implement changes following delta specifications",
            "Run tests to verify backward compatibility",
            "Update documentation"
        ]
    }

    return delta_output

# ============================================================================
# MAIN FUNCTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate exact component-level deltas for integration")
    parser.add_argument('--component', required=True, help="Component ID to generate deltas for")
    parser.add_argument('--gaps', required=True, help="Path to integration_gaps.json")
    parser.add_argument('--inventory', required=True, help="Path to component_inventory.json")
    parser.add_argument('--output', required=True, help="Path to output component delta JSON")
    parser.add_argument('--granularity', default='module',
                        choices=['function', 'class', 'module', 'file'],
                        help="Granularity of delta generation")

    args = parser.parse_args()

    print(f"=== Component Delta Generation v{VERSION} ===")

    gaps_path = Path(args.gaps)
    inventory_path = Path(args.inventory)
    output_path = Path(args.output)

    if not gaps_path.exists():
        print(f"ERROR: Gaps file not found: {gaps_path}")
        return 1

    if not inventory_path.exists():
        print(f"ERROR: Inventory file not found: {inventory_path}")
        return 1

    print(f"\nLoading integration gaps from {gaps_path}")
    gaps_data = load_json(gaps_path)

    print(f"Loading component inventory from {inventory_path}")
    inventory = load_json(inventory_path)

    try:
        delta = generate_deltas_for_component(args.component, gaps_data, inventory, args.granularity)
    except ValueError as e:
        print(f"\nERROR: {e}")
        return 1

    print(f"\nSaving component delta to {output_path}")
    save_json(delta, output_path)

    print(f"\n{'='*60}")
    print("DELTA GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Component: {args.component}")
    print(f"Total changes: {delta['summary']['total_changes']}")
    print(f"Estimated effort: {delta['summary']['estimated_total_effort']}")
    print(f"Breaking changes: {delta['summary']['breaking_changes']}")
    print(f"Risk level: {delta['summary']['risk_level']}")
    print(f"Version: {delta['delta_metadata']['current_version']} → {delta['delta_metadata']['target_version']}")

    print(f"\nChanges by type:")
    for change_type, count in delta['summary']['by_type'].items():
        print(f"  {change_type}: {count}")

    print(f"\nDependencies to add: {len(delta['dependency_changes']['added'])}")
    for dep in delta['dependency_changes']['added']:
        print(f"  - {dep}")

    if delta['summary']['breaking_changes'] > 0:
        print(f"\n⚠️  WARNING: {delta['summary']['breaking_changes']} breaking changes detected!")
        print("    Version will be incremented to MAJOR version")

    print(f"\nNext step: Review delta file and implement changes\n")

    return 0

if __name__ == "__main__":
    exit(main())
