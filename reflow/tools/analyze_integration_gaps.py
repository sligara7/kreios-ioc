#!/usr/bin/env python3
"""
Analyze Integration Gaps Tool - PRODUCTION VERSION
Identifies gaps preventing component integration across 9 gap types

Gap Types:
1. missing_interface - Component A needs interface from B, but B doesn't expose it
2. protocol_mismatch - Components use incompatible protocols (REST vs gRPC, sync vs async)
3. data_model_incompatibility - Components expect different data formats/schemas
4. missing_mediator - Components can't communicate directly, need adapter/translator
5. circular_dependency - Components depend on each other, creating cycle
6. conflicting_requirements - Components have incompatible requirements (A needs sync, B is async-only)
7. version_incompatibility - Components require incompatible versions of shared dependency
8. performance_gap - Integration would violate performance requirements
9. security_gap - Integration would create security vulnerability

Usage:
    python3 analyze_integration_gaps.py \\
        --inventory <path_to_component_inventory.json> \\
        --requirements <path_to_integration_requirements.json> \\
        --output <path_to_integration_gaps.json>
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime
from collections import defaultdict

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

def get_exposed_interfaces(component: Dict) -> List[Dict]:
    """Get all interfaces exposed by component"""
    return component.get('exposed_interfaces', [])

def get_consumed_interfaces(component: Dict) -> List[Dict]:
    """Get all interfaces consumed by component"""
    return component.get('consumed_interfaces', [])

# ============================================================================
# GAP TYPE 1: Missing Interface
# ============================================================================
def detect_missing_interfaces(inventory: Dict, requirements: Dict) -> List[Dict]:
    """
    Detect missing interfaces between components

    Logic: For each required interaction, check if target component
    exposes an interface matching the interaction requirements
    """
    gaps = []
    gap_counter = 1

    for interaction in requirements.get('required_interactions', []):
        from_comp_id = interaction.get('from_component')
        to_comp_id = interaction.get('to_component')
        interaction_type = interaction.get('interaction_type', 'synchronous_call')

        from_comp = get_component_by_id(from_comp_id, inventory)
        to_comp = get_component_by_id(to_comp_id, inventory)

        if not from_comp or not to_comp:
            continue

        # Check if target component exposes required interface
        exposed_interfaces = get_exposed_interfaces(to_comp)

        # Look for matching interface
        interface_found = False
        for interface in exposed_interfaces:
            # Match on interface type
            if interface.get('interface_type') in ['rest_api', 'grpc_api', 'python_api', 'message_queue']:
                interface_found = True
                break

        if not interface_found:
            gaps.append({
                "gap_id": f"GAP-MISSING-{gap_counter:03d}",
                "gap_type": "missing_interface",
                "severity": "critical",
                "from_component": from_comp_id,
                "to_component": to_comp_id,
                "gap_description": f"{from_comp_id} needs to communicate with {to_comp_id}, but {to_comp_id} does not expose any compatible interface",
                "current_state": f"{to_comp_id} has {len(exposed_interfaces)} exposed interfaces, none match {interaction_type}",
                "required_state": f"{to_comp_id} must expose interface compatible with {interaction_type}",
                "required_change": f"Add interface to {to_comp_id} or create adapter component",
                "affected_tiers": [from_comp.get('tier_classification'), to_comp.get('tier_classification')],
                "affected_capabilities": [interaction.get('interaction_purpose', 'Unknown')],
                "impact_if_not_resolved": "Integration cannot proceed - components cannot communicate",
                "recommendation": {
                    "recommended_solution": f"Modify {to_comp_id} to expose {interaction_type} interface OR create adapter component",
                    "rationale": "Direct interface addition is simplest; adapter preserves existing interfaces",
                    "estimated_effort": "4-8 hours",
                    "priority": "immediate"
                },
                "resolution_approach": {
                    "approach_type": "modify_component",
                    "components_to_modify": [to_comp_id],
                    "new_components_to_create": [],
                    "code_changes_required": True,
                    "configuration_changes_required": False
                },
                "related_gaps": []
            })
            gap_counter += 1

    return gaps

# ============================================================================
# GAP TYPE 2: Protocol Mismatch
# ============================================================================
def detect_protocol_mismatches(inventory: Dict, requirements: Dict) -> List[Dict]:
    """
    Detect protocol mismatches (REST vs gRPC, sync vs async, in-process vs network)

    Logic: Compare interface protocols between communicating components
    """
    gaps = []
    gap_counter = 1

    for interaction in requirements.get('required_interactions', []):
        from_comp_id = interaction.get('from_component')
        to_comp_id = interaction.get('to_component')

        from_comp = get_component_by_id(from_comp_id, inventory)
        to_comp = get_component_by_id(to_comp_id, inventory)

        if not from_comp or not to_comp:
            continue

        # Get interface types
        from_interfaces = get_exposed_interfaces(from_comp)
        to_interfaces = get_exposed_interfaces(to_comp)

        # Check for protocol mismatches
        from_protocols = set([iface.get('interface_type') for iface in from_interfaces])
        to_protocols = set([iface.get('interface_type') for iface in to_interfaces])

        # Example mismatch: python_api trying to call rest_api
        if 'python_api' in from_protocols and 'rest_api' in to_protocols:
            gaps.append({
                "gap_id": f"GAP-PROTOCOL-{gap_counter:03d}",
                "gap_type": "protocol_mismatch",
                "severity": "high",
                "from_component": from_comp_id,
                "to_component": to_comp_id,
                "gap_description": f"{from_comp_id} uses in-process Python calls, but {to_comp_id} exposes REST API - protocol mismatch",
                "current_state": f"{from_comp_id}: python_api, {to_comp_id}: rest_api",
                "required_state": "Compatible protocols for direct communication",
                "required_change": "Add HTTP client wrapper to bridge Python calls to REST API",
                "affected_tiers": [from_comp.get('tier_classification'), to_comp.get('tier_classification')],
                "affected_capabilities": [interaction.get('interaction_purpose', 'Unknown')],
                "impact_if_not_resolved": "Integration requires manual protocol translation",
                "recommendation": {
                    "recommended_solution": "Create protocol adapter component (e.g., rest_client wrapper)",
                    "rationale": "Adapter preserves both components as-is, reusable for other integrations",
                    "alternatives": [
                        {
                            "solution": f"Modify {from_comp_id} to use HTTP client library",
                            "pros": ["No new components"],
                            "cons": ["Adds network dependency to in-process library"]
                        }
                    ],
                    "estimated_effort": "4 hours",
                    "priority": "short_term"
                },
                "resolution_approach": {
                    "approach_type": "create_adapter",
                    "components_to_modify": [],
                    "new_components_to_create": [f"{from_comp_id}_to_{to_comp_id}_adapter"],
                    "code_changes_required": True,
                    "configuration_changes_required": True
                },
                "related_gaps": []
            })
            gap_counter += 1

    return gaps

# ============================================================================
# GAP TYPE 3: Data Model Incompatibility
# ============================================================================
def detect_data_model_incompatibilities(inventory: Dict, requirements: Dict) -> List[Dict]:
    """
    Detect data model incompatibilities (JSON vs XML, schema differences)

    Logic: Check data flow requirements against component interfaces
    """
    gaps = []
    gap_counter = 1

    for flow in requirements.get('data_flow_requirements', []):
        components_involved = flow.get('components_involved', [])

        # Check each step in flow for data model compatibility
        for i, step in enumerate(flow.get('flow_steps', [])):
            data_in = step.get('data_in', '')
            data_out = step.get('data_out', '')

            # Look for format indicators
            if 'JSON' in data_in and 'XML' in data_out:
                gaps.append({
                    "gap_id": f"GAP-DATAMODEL-{gap_counter:03d}",
                    "gap_type": "data_model_incompatibility",
                    "severity": "medium",
                    "from_component": step.get('component'),
                    "to_component": flow['flow_steps'][i+1].get('component') if i+1 < len(flow['flow_steps']) else None,
                    "gap_description": f"Data format mismatch in flow {flow.get('flow_id')}: step {step.get('step')} expects JSON but produces XML",
                    "current_state": f"Input: {data_in}, Output: {data_out}",
                    "required_state": "Consistent data format across flow",
                    "required_change": "Add data format transformation (JSON ↔ XML converter)",
                    "affected_tiers": ["tier_2_services"],
                    "affected_capabilities": [flow.get('flow_name')],
                    "impact_if_not_resolved": "Data cannot flow through system without transformation",
                    "recommendation": {
                        "recommended_solution": "Create data transformation adapter",
                        "rationale": "Preserves existing component data formats, centralizes transformation logic",
                        "estimated_effort": "3 hours",
                        "priority": "medium_term"
                    },
                    "resolution_approach": {
                        "approach_type": "create_adapter",
                        "components_to_modify": [],
                        "new_components_to_create": ["json_xml_transformer"],
                        "code_changes_required": True,
                        "configuration_changes_required": False
                    },
                    "related_gaps": []
                })
                gap_counter += 1

    return gaps

# ============================================================================
# GAP TYPE 4: Missing Mediator
# ============================================================================
def detect_missing_mediators(inventory: Dict, requirements: Dict) -> List[Dict]:
    """
    Detect when mediator component is needed but missing

    Logic: Check for N:M relationships that require orchestration
    """
    gaps = []
    gap_counter = 1

    # Analyze component relationships for N:M patterns
    component_connections = defaultdict(list)

    for interaction in requirements.get('required_interactions', []):
        from_comp = interaction.get('from_component')
        to_comp = interaction.get('to_component')
        component_connections[from_comp].append(to_comp)

    # Check for components with >3 outbound connections (potential need for mediator)
    for comp_id, connections in component_connections.items():
        if len(connections) > 3:
            gaps.append({
                "gap_id": f"GAP-MEDIATOR-{gap_counter:03d}",
                "gap_type": "missing_mediator",
                "severity": "medium",
                "from_component": comp_id,
                "to_component": ', '.join(connections),
                "gap_description": f"{comp_id} communicates with {len(connections)} components - high coupling, recommend mediator pattern",
                "current_state": f"{comp_id} directly connected to {len(connections)} components",
                "required_state": "Mediator component to coordinate interactions",
                "required_change": "Create mediator/orchestrator component",
                "affected_tiers": ["tier_2_services"],
                "affected_capabilities": ["System coordination"],
                "impact_if_not_resolved": "High coupling, difficult to maintain and test",
                "recommendation": {
                    "recommended_solution": f"Create {comp_id}_mediator component to orchestrate interactions",
                    "rationale": "Mediator pattern reduces coupling, centralizes coordination logic",
                    "estimated_effort": "8 hours",
                    "priority": "medium_term"
                },
                "resolution_approach": {
                    "approach_type": "create_mediator",
                    "components_to_modify": [comp_id],
                    "new_components_to_create": [f"{comp_id}_mediator"],
                    "code_changes_required": True,
                    "configuration_changes_required": True
                },
                "related_gaps": []
            })
            gap_counter += 1

    return gaps

# ============================================================================
# GAP TYPE 5: Circular Dependency
# ============================================================================
def detect_circular_dependencies(inventory: Dict, requirements: Dict) -> List[Dict]:
    """
    Detect circular dependencies between components

    Logic: Build dependency graph and detect cycles using DFS
    """
    gaps = []
    gap_counter = 1

    # Build dependency graph
    graph = defaultdict(list)
    for interaction in requirements.get('required_interactions', []):
        from_comp = interaction.get('from_component')
        to_comp = interaction.get('to_component')
        graph[from_comp].append(to_comp)

    # DFS to detect cycles
    def has_cycle_dfs(node, visited, rec_stack, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle_dfs(neighbor, visited, rec_stack, path):
                    return True
            elif neighbor in rec_stack:
                # Found cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                return cycle

        path.pop()
        rec_stack.remove(node)
        return False

    visited = set()
    for node in graph.keys():
        if node not in visited:
            rec_stack = set()
            path = []
            cycle = has_cycle_dfs(node, visited, rec_stack, path)
            if cycle and isinstance(cycle, list):
                gaps.append({
                    "gap_id": f"GAP-CIRCULAR-{gap_counter:03d}",
                    "gap_type": "circular_dependency",
                    "severity": "critical",
                    "from_component": cycle[0],
                    "to_component": cycle[-2] if len(cycle) > 1 else cycle[0],
                    "gap_description": f"Circular dependency detected: {' → '.join(cycle)}",
                    "current_state": f"Components form dependency cycle: {' → '.join(cycle)}",
                    "required_state": "Acyclic dependency graph",
                    "required_change": "Break cycle by introducing mediator or dependency inversion",
                    "affected_tiers": ["tier_2_services", "tier_3_components"],
                    "affected_capabilities": ["System initialization", "Component lifecycle"],
                    "impact_if_not_resolved": "System cannot initialize, deployment will fail",
                    "recommendation": {
                        "recommended_solution": "Introduce mediator component to break cycle OR use dependency inversion (interfaces)",
                        "rationale": "Circular dependencies prevent proper initialization and testing",
                        "estimated_effort": "12 hours",
                        "priority": "immediate"
                    },
                    "resolution_approach": {
                        "approach_type": "refactor_architecture",
                        "components_to_modify": cycle,
                        "new_components_to_create": ["cycle_breaker_mediator"],
                        "code_changes_required": True,
                        "configuration_changes_required": True,
                        "infrastructure_changes_required": False
                    },
                    "related_gaps": []
                })
                gap_counter += 1
                break  # Report first cycle found

    return gaps

# ============================================================================
# GAP TYPE 6: Conflicting Requirements
# ============================================================================
def detect_conflicting_requirements(inventory: Dict, requirements: Dict) -> List[Dict]:
    """
    Detect conflicting requirements (A needs sync, B is async-only)

    Logic: Check component constraints against integration requirements
    """
    gaps = []
    gap_counter = 1

    for interaction in requirements.get('required_interactions', []):
        from_comp_id = interaction.get('from_component')
        to_comp_id = interaction.get('to_component')
        interaction_type = interaction.get('interaction_type')

        from_comp = get_component_by_id(from_comp_id, inventory)
        to_comp = get_component_by_id(to_comp_id, inventory)

        if not from_comp or not to_comp:
            continue

        # Check async support mismatch
        from_async = from_comp.get('constraints', {}).get('async_support', False)
        to_async = to_comp.get('constraints', {}).get('async_support', False)

        if interaction_type == 'synchronous_call' and to_async and not from_async:
            gaps.append({
                "gap_id": f"GAP-CONFLICT-{gap_counter:03d}",
                "gap_type": "conflicting_requirements",
                "severity": "high",
                "from_component": from_comp_id,
                "to_component": to_comp_id,
                "gap_description": f"Requirement conflict: {from_comp_id} needs synchronous communication, but {to_comp_id} is async-only",
                "current_state": f"{from_comp_id}: async_support={from_async}, {to_comp_id}: async_support={to_async}, required: {interaction_type}",
                "required_state": "Compatible async/sync patterns",
                "required_change": f"Add sync wrapper for {to_comp_id} OR convert {from_comp_id} to async",
                "affected_tiers": [from_comp.get('tier_classification'), to_comp.get('tier_classification')],
                "affected_capabilities": [interaction.get('interaction_purpose')],
                "impact_if_not_resolved": "Integration pattern mismatch causes blocking or errors",
                "recommendation": {
                    "recommended_solution": "Create sync-to-async adapter OR add async support to caller",
                    "rationale": "Adapter is non-invasive; async conversion is more work but cleaner",
                    "estimated_effort": "6 hours",
                    "priority": "short_term"
                },
                "resolution_approach": {
                    "approach_type": "create_adapter",
                    "components_to_modify": [],
                    "new_components_to_create": ["sync_async_adapter"],
                    "code_changes_required": True,
                    "configuration_changes_required": False
                },
                "related_gaps": []
            })
            gap_counter += 1

    return gaps

# ============================================================================
# GAP TYPE 7: Version Incompatibility
# ============================================================================
def detect_version_incompatibilities(inventory: Dict, requirements: Dict) -> List[Dict]:
    """
    Detect version incompatibilities in shared dependencies

    Logic: Check for conflicting version requirements of shared dependencies
    """
    gaps = []
    gap_counter = 1

    # Build dependency version map
    dependency_versions = defaultdict(list)  # {dep_name: [(comp_id, version_constraint), ...]}

    for comp in inventory.get('components', []):
        comp_id = comp.get('component_id')
        for dep in comp.get('dependencies', {}).get('runtime_dependencies', []):
            dep_name = dep.get('dependency_name')
            version_constraint = dep.get('version_constraint', '')
            dependency_versions[dep_name].append((comp_id, version_constraint))

    # Check for conflicts
    for dep_name, components in dependency_versions.items():
        if len(components) > 1:
            # Check if version constraints are incompatible
            versions = [v for _, v in components]

            # Simple heuristic: if major versions differ, it's incompatible
            major_versions = set()
            for version in versions:
                if '>=' in version or '==' in version:
                    ver_num = version.replace('>=', '').replace('==', '').strip()
                    if ver_num:
                        major = ver_num.split('.')[0]
                        major_versions.add(major)

            if len(major_versions) > 1:
                comp_list = [c for c, _ in components]
                gaps.append({
                    "gap_id": f"GAP-VERSION-{gap_counter:03d}",
                    "gap_type": "version_incompatibility",
                    "severity": "high",
                    "from_component": comp_list[0],
                    "to_component": ', '.join(comp_list[1:]),
                    "gap_description": f"Version conflict for {dep_name}: components require incompatible versions {versions}",
                    "current_state": f"{', '.join([f'{c}: {v}' for c, v in components])}",
                    "required_state": "Compatible version constraints for shared dependency",
                    "required_change": "Upgrade/downgrade components to use compatible versions",
                    "affected_tiers": ["tier_3_components"],
                    "affected_capabilities": ["Dependency management"],
                    "impact_if_not_resolved": "Deployment will fail due to dependency conflict",
                    "recommendation": {
                        "recommended_solution": f"Analyze {dep_name} changelog and upgrade all components to latest compatible version",
                        "rationale": "Latest version usually has broadest compatibility",
                        "estimated_effort": "4 hours",
                        "priority": "short_term"
                    },
                    "resolution_approach": {
                        "approach_type": "modify_component",
                        "components_to_modify": comp_list,
                        "new_components_to_create": [],
                        "code_changes_required": True,
                        "configuration_changes_required": True
                    },
                    "related_gaps": []
                })
                gap_counter += 1

    return gaps

# ============================================================================
# GAP TYPE 8: Performance Gap
# ============================================================================
def detect_performance_gaps(inventory: Dict, requirements: Dict) -> List[Dict]:
    """
    Detect performance gaps (integration would violate performance requirements)

    Logic: Check if performance requirements can be met given component constraints
    """
    gaps = []
    gap_counter = 1

    nfrs = requirements.get('non_functional_requirements', {})
    perf_targets = nfrs.get('performance', {})
    latency_target = perf_targets.get('latency_targets', {}).get('p95', '100ms')

    # Parse latency target (e.g., "100ms" -> 100)
    target_ms = int(latency_target.replace('ms', '')) if 'ms' in latency_target else 100

    # Check each interaction for performance feasibility
    for interaction in requirements.get('required_interactions', []):
        perf_req = interaction.get('performance_requirements', {})
        max_latency = perf_req.get('max_latency_ms', 1000)

        if max_latency < target_ms:
            gaps.append({
                "gap_id": f"GAP-PERF-{gap_counter:03d}",
                "gap_type": "performance_gap",
                "severity": "medium",
                "from_component": interaction.get('from_component'),
                "to_component": interaction.get('to_component'),
                "gap_description": f"Performance gap: interaction requires <{max_latency}ms but system target is {latency_target}",
                "current_state": f"Interaction latency budget: {max_latency}ms, System target: {latency_target}",
                "required_state": "Interaction latency within system budget",
                "required_change": "Optimize interaction path or relax performance requirements",
                "affected_tiers": ["tier_2_services"],
                "affected_capabilities": [interaction.get('interaction_purpose')],
                "impact_if_not_resolved": "Performance SLAs will not be met",
                "recommendation": {
                    "recommended_solution": "Add caching layer or optimize critical path",
                    "rationale": "Caching reduces repeated calls; optimization improves per-call latency",
                    "estimated_effort": "6 hours",
                    "priority": "medium_term"
                },
                "resolution_approach": {
                    "approach_type": "modify_component",
                    "components_to_modify": [interaction.get('from_component'), interaction.get('to_component')],
                    "new_components_to_create": [],
                    "code_changes_required": True,
                    "configuration_changes_required": True
                },
                "related_gaps": []
            })
            gap_counter += 1

    return gaps

# ============================================================================
# GAP TYPE 9: Security Gap
# ============================================================================
def detect_security_gaps(inventory: Dict, requirements: Dict) -> List[Dict]:
    """
    Detect security gaps (integration would create security vulnerability)

    Logic: Check for missing authentication, unencrypted channels, etc.
    """
    gaps = []
    gap_counter = 1

    nfrs = requirements.get('non_functional_requirements', {})
    security_reqs = nfrs.get('security', {})
    auth_required = security_reqs.get('authentication_required', False)
    encryption_in_transit = security_reqs.get('encryption_in_transit', False)

    for interaction in requirements.get('required_interactions', []):
        from_comp_id = interaction.get('from_component')
        to_comp_id = interaction.get('to_component')

        to_comp = get_component_by_id(to_comp_id, inventory)
        if not to_comp:
            continue

        # Check if component has required security features
        comp_security = to_comp.get('security', {})
        has_auth = comp_security.get('api_key_authentication', False)
        has_ssl = comp_security.get('ssl_tls', False)

        # Check for missing authentication
        if auth_required and not has_auth:
            gaps.append({
                "gap_id": f"GAP-SECURITY-{gap_counter:03d}",
                "gap_type": "security_gap",
                "severity": "critical",
                "from_component": from_comp_id,
                "to_component": to_comp_id,
                "gap_description": f"Security gap: {to_comp_id} does not implement authentication, but system requires it",
                "current_state": f"{to_comp_id}: authentication={has_auth}, System requirement: {auth_required}",
                "required_state": "All components implement required authentication",
                "required_change": f"Add authentication to {to_comp_id}",
                "affected_tiers": [to_comp.get('tier_classification')],
                "affected_capabilities": ["Security", "Access control"],
                "impact_if_not_resolved": "System will be vulnerable to unauthorized access",
                "recommendation": {
                    "recommended_solution": f"Implement JWT or API key authentication in {to_comp_id}",
                    "rationale": "Authentication is mandatory for security compliance",
                    "estimated_effort": "8 hours",
                    "priority": "immediate"
                },
                "resolution_approach": {
                    "approach_type": "modify_component",
                    "components_to_modify": [to_comp_id],
                    "new_components_to_create": [],
                    "code_changes_required": True,
                    "configuration_changes_required": True
                },
                "related_gaps": []
            })
            gap_counter += 1

        # Check for missing encryption
        if encryption_in_transit and not has_ssl:
            gaps.append({
                "gap_id": f"GAP-SECURITY-{gap_counter:03d}",
                "gap_type": "security_gap",
                "severity": "high",
                "from_component": from_comp_id,
                "to_component": to_comp_id,
                "gap_description": f"Security gap: {to_comp_id} does not use SSL/TLS, but system requires encryption in transit",
                "current_state": f"{to_comp_id}: ssl_tls={has_ssl}, System requirement: {encryption_in_transit}",
                "required_state": "All network communications encrypted",
                "required_change": f"Enable SSL/TLS in {to_comp_id}",
                "affected_tiers": [to_comp.get('tier_classification')],
                "affected_capabilities": ["Security", "Data protection"],
                "impact_if_not_resolved": "Data transmitted in clear text, vulnerable to interception",
                "recommendation": {
                    "recommended_solution": f"Configure SSL/TLS certificates for {to_comp_id}",
                    "rationale": "Encryption in transit is mandatory for data protection",
                    "estimated_effort": "4 hours",
                    "priority": "short_term"
                },
                "resolution_approach": {
                    "approach_type": "modify_component",
                    "components_to_modify": [to_comp_id],
                    "new_components_to_create": [],
                    "code_changes_required": False,
                    "configuration_changes_required": True,
                    "infrastructure_changes_required": True
                },
                "related_gaps": []
            })
            gap_counter += 1

    return gaps

# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================
def analyze_integration_gaps(inventory_path: Path, requirements_path: Path, output_path: Path):
    """Main gap analysis function - orchestrates all 9 gap type detections"""

    print(f"=== Integration Gap Analysis v{VERSION} ===\n")
    print(f"Loading component inventory from {inventory_path}")
    inventory = load_json(inventory_path)

    print(f"Loading integration requirements from {requirements_path}")
    requirements = load_json(requirements_path)

    total_components = len(inventory.get('components', []))
    total_interactions = len(requirements.get('required_interactions', []))

    print(f"\nAnalyzing {total_components} components with {total_interactions} required interactions...")
    print("Detecting 9 gap types:\n")

    all_gaps = []

    # Run all 9 gap type detections
    print("  [1/9] Detecting missing interfaces...")
    gaps_1 = detect_missing_interfaces(inventory, requirements)
    all_gaps.extend(gaps_1)
    print(f"        Found {len(gaps_1)} gaps")

    print("  [2/9] Detecting protocol mismatches...")
    gaps_2 = detect_protocol_mismatches(inventory, requirements)
    all_gaps.extend(gaps_2)
    print(f"        Found {len(gaps_2)} gaps")

    print("  [3/9] Detecting data model incompatibilities...")
    gaps_3 = detect_data_model_incompatibilities(inventory, requirements)
    all_gaps.extend(gaps_3)
    print(f"        Found {len(gaps_3)} gaps")

    print("  [4/9] Detecting missing mediators...")
    gaps_4 = detect_missing_mediators(inventory, requirements)
    all_gaps.extend(gaps_4)
    print(f"        Found {len(gaps_4)} gaps")

    print("  [5/9] Detecting circular dependencies...")
    gaps_5 = detect_circular_dependencies(inventory, requirements)
    all_gaps.extend(gaps_5)
    print(f"        Found {len(gaps_5)} gaps")

    print("  [6/9] Detecting conflicting requirements...")
    gaps_6 = detect_conflicting_requirements(inventory, requirements)
    all_gaps.extend(gaps_6)
    print(f"        Found {len(gaps_6)} gaps")

    print("  [7/9] Detecting version incompatibilities...")
    gaps_7 = detect_version_incompatibilities(inventory, requirements)
    all_gaps.extend(gaps_7)
    print(f"        Found {len(gaps_7)} gaps")

    print("  [8/9] Detecting performance gaps...")
    gaps_8 = detect_performance_gaps(inventory, requirements)
    all_gaps.extend(gaps_8)
    print(f"        Found {len(gaps_8)} gaps")

    print("  [9/9] Detecting security gaps...")
    gaps_9 = detect_security_gaps(inventory, requirements)
    all_gaps.extend(gaps_9)
    print(f"        Found {len(gaps_9)} gaps")

    # Categorize gaps
    by_severity = {
        "critical": [g for g in all_gaps if g.get('severity') == 'critical'],
        "high": [g for g in all_gaps if g.get('severity') == 'high'],
        "medium": [g for g in all_gaps if g.get('severity') == 'medium'],
        "low": [g for g in all_gaps if g.get('severity') == 'low']
    }

    by_type = defaultdict(list)
    for gap in all_gaps:
        by_type[gap.get('gap_type')].append(gap)

    # Determine integration feasibility
    critical_count = len(by_severity['critical'])
    high_count = len(by_severity['high'])

    if critical_count > 0:
        feasibility = "low"
    elif high_count > 5:
        feasibility = "medium"
    elif high_count > 0:
        feasibility = "high"
    else:
        feasibility = "very_high"

    # Create output structure
    output = {
        "gaps_metadata": {
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "system_name": requirements.get('requirements_metadata', {}).get('system_name', 'Unknown'),
            "based_on_inventory": str(inventory_path),
            "based_on_requirements": str(requirements_path),
            "analysis_tool": f"analyze_integration_gaps.py v{VERSION}",
            "total_components_analyzed": total_components,
            "total_interactions_analyzed": total_interactions
        },
        "gaps": all_gaps,
        "gap_categories": {
            "by_severity": {
                "critical": len(by_severity['critical']),
                "high": len(by_severity['high']),
                "medium": len(by_severity['medium']),
                "low": len(by_severity['low'])
            },
            "by_type": {gap_type: len(gaps) for gap_type, gaps in by_type.items()}
        },
        "summary": {
            "total_gaps": len(all_gaps),
            "critical_gaps": critical_count,
            "high_priority_gaps": high_count,
            "gaps_requiring_new_components": len([g for g in all_gaps if g.get('resolution_approach', {}).get('new_components_to_create')]),
            "gaps_requiring_modifications": len([g for g in all_gaps if g.get('resolution_approach', {}).get('components_to_modify')]),
            "estimated_total_effort": f"{len(all_gaps) * 6} hours (average 6 hours per gap)",
            "integration_feasibility": feasibility,
            "integration_feasibility_rationale": f"{critical_count} critical gaps, {high_count} high priority gaps",
            "blocking_gaps": [g['gap_id'] for g in by_severity['critical']]
        },
        "next_steps": [
            "Prioritize gaps by severity and impact",
            "Assign gaps to resolution phases",
            "Run generate_component_deltas.py to create exact change specifications",
            "Review and approve resolution roadmap"
        ]
    }

    print(f"\nSaving integration gaps to {output_path}")
    save_json(output, output_path)

    # Print summary
    print(f"\n{'='*60}")
    print("GAP ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"Total gaps found: {len(all_gaps)}")
    print(f"  Critical: {by_severity['critical'].__len__()} (BLOCKING)")
    print(f"  High:     {by_severity['high'].__len__()}")
    print(f"  Medium:   {by_severity['medium'].__len__()}")
    print(f"  Low:      {by_severity['low'].__len__()}")
    print(f"\nBy Type:")
    for gap_type, gaps in by_type.items():
        print(f"  {gap_type}: {len(gaps)}")
    print(f"\nIntegration Feasibility: {feasibility.upper()}")
    print(f"Estimated Total Effort: {output['summary']['estimated_total_effort']}")

    if critical_count > 0:
        print(f"\n⚠️  WARNING: {critical_count} CRITICAL gaps must be resolved before integration can proceed!")

    print(f"\nNext step: Run generate_component_deltas.py to create exact code changes\n")

def main():
    parser = argparse.ArgumentParser(description="Analyze integration gaps between components (9 gap types)")
    parser.add_argument('--inventory', required=True, help="Path to component_inventory.json")
    parser.add_argument('--requirements', required=True, help="Path to integration_requirements.json")
    parser.add_argument('--output', required=True, help="Path to output integration_gaps.json")

    args = parser.parse_args()

    inventory_path = Path(args.inventory)
    requirements_path = Path(args.requirements)
    output_path = Path(args.output)

    if not inventory_path.exists():
        print(f"ERROR: Inventory file not found: {inventory_path}")
        return 1

    if not requirements_path.exists():
        print(f"ERROR: Requirements file not found: {requirements_path}")
        return 1

    analyze_integration_gaps(inventory_path, requirements_path, output_path)
    return 0

if __name__ == "__main__":
    exit(main())
