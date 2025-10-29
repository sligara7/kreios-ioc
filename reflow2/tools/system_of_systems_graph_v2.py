#!/usr/bin/env python3
"""
System-of-Systems Graph Generator v2.0 - Framework-Agnostic Edition

Creates machine-readable JSON representation of system architecture using NetworkX.
Supports multiple architectural frameworks (UAF, Systems Biology, Social Networks, etc.)

Key Features:
- Framework-agnostic parsing via framework adapters
- Universal node/edge schema (all frameworks → same graph structure)
- Knowledge gap detection (missing nodes, edges, mediators)
- Comprehensive NetworkX analysis (centrality, paths, connectivity, clustering)
- Backward compatible with UAF-based systems

This tool builds a directed graph where:
- Nodes represent components (services, agents, genes, species, etc.)
- Edges represent connections (interfaces, relationships, interactions, etc.)
- Output is NetworkX node_link_data format + analysis results
"""

import os
import json
import networkx as nx
import sys
import argparse
from typing import Dict, List, Tuple, Any, Optional, Set
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import sanitize_path, validate_system_root, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError

# Adjust paths for reflow directory structure
REFLOW_ROOT = Path(__file__).parent.parent
TEMPLATES_PATH = REFLOW_ROOT / "templates"
DEFINITIONS_PATH = REFLOW_ROOT / "definitions"

# =============================================================================
# FRAMEWORK ADAPTER - Load and adapt framework-specific files to universal schema
# =============================================================================

def load_framework_config(system_root: Path) -> Dict[str, Any]:
    """Load framework configuration from working_memory.json.

    Returns framework metadata including field mappings for node/edge schemas.
    Falls back to UAF if no framework specified (backward compatibility).

    Args:
        system_root: System root directory (Path object, already validated)
    """
    # system_root is now a Path object from sanitize_path/validate_system_root
    working_memory_path = system_root / "context" / "working_memory.json"

    # Default to UAF for backward compatibility
    default_framework = {
        "framework_id": "uaf",
        "framework_name": "UAF 1.2",
        "component_term": "service",
        "connection_term": "interface"
    }

    if not working_memory_path.exists():
        print(f"Warning: No working_memory.json found, defaulting to UAF framework")
        return default_framework

    try:
        working_memory = safe_load_json(working_memory_path, file_type_description="working memory")

        framework_id = working_memory.get('architectural_framework', 'uaf')

        return {
            "framework_id": framework_id,
            "framework_name": working_memory.get('framework_name', 'UAF 1.2'),
            "component_term": working_memory.get('component_term', 'service'),
            "connection_term": working_memory.get('connection_term', 'interface'),
            "definitions_path": working_memory.get('definitions_path')
        }
    except Exception as e:
        print(f"Warning: Error loading working_memory.json: {e}, defaulting to UAF")
        return default_framework


def load_framework_registry(framework_id: str) -> Dict[str, Any]:
    """Load framework schema mappings from framework_registry.json."""
    registry_path = DEFINITIONS_PATH / "framework_registry.json"

    if not registry_path.exists():
        # Fallback for UAF when registry doesn't exist (backward compatibility)
        if framework_id == 'uaf':
            return {
                "node_schema": {
                    "id_field": "service_id",
                    "name_field": "service_name",
                    "type_field": "classification",
                    "functions_field": "functions",
                    "interfaces_field": "interfaces",
                    "dependencies_field": "dependencies"
                },
                "edge_schema": {
                    "id_field": "name",
                    "type_field": "interface_type",
                    "direction_field": "direction",
                    "protocol_field": "protocol"
                }
            }
        else:
            raise FileNotFoundError(f"framework_registry.json not found at {registry_path}")

    registry = safe_load_json(registry_path, file_type_description="framework registry")

    if framework_id not in registry.get('frameworks', {}):
        raise ValueError(f"Framework '{framework_id}' not found in registry. Available: {list(registry['frameworks'].keys())}")

    return registry['frameworks'][framework_id]


def adapt_component_to_universal(component_data: Dict, framework_schema: Dict) -> Dict:
    """Convert framework-specific component file to universal schema.

    All frameworks must provide:
    - node_id: unique identifier
    - node_name: human-readable name
    - node_type: classification within framework
    - functions: list of capabilities
    - interfaces: list of connections to other nodes

    Framework-specific data is preserved in 'raw' field.
    """
    node_schema = framework_schema['node_schema']

    # Extract universal properties using framework-specific field names
    universal = {
        'node_id': component_data.get(node_schema['id_field']),
        'node_name': component_data.get(node_schema['name_field']),
        'node_type': component_data.get(node_schema['type_field']),
        'functions': component_data.get(node_schema['functions_field'], []),
        'interfaces': component_data.get(node_schema['interfaces_field'], []),
        'dependencies': component_data.get(node_schema.get('dependencies_field', 'dependencies'), []),
        'raw': component_data  # Preserve full framework-specific data
    }

    # Handle missing required fields
    if not universal['node_id']:
        raise ValueError(f"Missing required field '{node_schema['id_field']}' in component data")
    if not universal['node_name']:
        universal['node_name'] = universal['node_id']  # Fallback to ID

    return universal


# =============================================================================
# INDEX LOADING
# =============================================================================

def load_component_index(index_path: str) -> Dict[str, str]:
    """Load the mapping of component_id to file path from the index file.

    Handles multiple index formats:
    - Structured index with 'components' key
    - Legacy flat format (UAF compatibility)
    - Framework-agnostic component registry

    Returns a flat mapping of component_id to file_path.
    """
    index_data = safe_load_json(index_path, file_type_description="component index")

    # Handle structured index format with metadata and components
    if isinstance(index_data, dict) and 'components' in index_data:
        return index_data['components']

    # Handle legacy flat format (service_id: file_path mapping)
    elif isinstance(index_data, dict):
        # Filter out non-component metadata keys
        metadata_keys = {'system_name', 'description', 'last_updated', 'version', 'metadata',
                        'framework', 'architectural_framework'}
        return {k: v for k, v in index_data.items() if k not in metadata_keys and isinstance(v, str)}

    else:
        raise ValueError(f"Invalid index format: expected dict with 'components' key or flat component mapping")


# =============================================================================
# GRAPH BUILDING - Framework-Agnostic
# =============================================================================

def build_universal_graph(index: Dict[str, str], framework_schema: Dict, system_root: Path) -> nx.DiGraph:
    """Build a directed graph from component architecture files using universal schema.

    All frameworks map to the same structure:
    - Nodes: components with id, name, type, functions, interfaces
    - Edges: connections between components with type and direction

    Args:
        index: Dictionary mapping component_id to file paths
        framework_schema: Schema from framework_registry.json
        system_root: System root directory (Path object, already validated)

    Returns:
        NetworkX DiGraph with universal node/edge attributes
    """
    G = nx.DiGraph()
    component_data_cache = {}

    # Pass 1: Load all components and add as nodes
    print(f"Loading {len(index)} components...")
    for component_id, file_path in index.items():
        # Sanitize file path (security fix - SV-01)
        try:
            safe_file_path = sanitize_path(file_path, system_root, must_exist=True)
        except (PathSecurityError, FileNotFoundError) as e:
            print(f"Warning: Could not validate path {file_path} for component {component_id}: {e}")
            continue

        try:
            raw_data = safe_load_json(safe_file_path, file_type_description=f"component architecture '{component_id}'")
        except JSONValidationError:
            print(f"Warning: Invalid JSON in {safe_file_path} for component {component_id}")
            continue

        try:
            # Convert to universal schema
            universal_node = adapt_component_to_universal(raw_data, framework_schema)
            component_data_cache[component_id] = universal_node

            # Add node to graph with universal attributes
            G.add_node(
                component_id,
                name=universal_node['node_name'],
                type=universal_node['node_type'],
                functions=universal_node['functions'],
                interfaces=universal_node['interfaces'],
                dependencies=universal_node['dependencies'],
                raw=universal_node['raw']
            )

        except Exception as e:
            print(f"Warning: Error processing {component_id}: {e}")
            continue

    print(f"Added {G.number_of_nodes()} nodes to graph")

    # Pass 2: Add edges based on dependencies and interfaces
    print("Building edges from dependencies and interfaces...")
    for component_id, universal_node in component_data_cache.items():
        if component_id not in G:
            continue

        # Add edges from dependencies
        for dep in universal_node['dependencies']:
            # Try to match dependency to component_id
            dep_id = match_dependency_to_component(dep, component_data_cache)
            if dep_id and dep_id in G:
                G.add_edge(component_id, dep_id, type='dependency', interaction_type='requires')

        # Add edges from interfaces
        for interface in universal_node['interfaces']:
            if not isinstance(interface, dict):
                continue

            # Check for explicit connections in interface
            connected_to = interface.get('connects_to', interface.get('connected_services',
                                        interface.get('target_components', [])))

            if isinstance(connected_to, str):
                connected_to = [connected_to]

            for target in connected_to:
                target_id = match_dependency_to_component(target, component_data_cache)
                if target_id and target_id in G:
                    edge_type = interface.get('type', interface.get('interface_type',
                                             interface.get('interaction_type', 'connection')))
                    direction = interface.get('direction', 'directed')

                    G.add_edge(component_id, target_id,
                              type='interface',
                              interaction_type=edge_type,
                              direction=direction)

    print(f"Added {G.number_of_edges()} edges to graph")

    return G


def match_dependency_to_component(dependency_name: str, components: Dict[str, Dict]) -> Optional[str]:
    """Match a dependency string to a component_id.

    Tries multiple matching strategies:
    - Exact match on component_id
    - Match on node_name (case-insensitive, underscore/space normalized)
    - Partial match on node_name
    """
    if not dependency_name:
        return None

    dep_normalized = dependency_name.lower().replace(' ', '_').replace('-', '_')

    # Exact match on component_id
    if dependency_name in components:
        return dependency_name

    # Try normalized matching
    for comp_id, comp_data in components.items():
        # Match on component_id normalized
        if comp_id.lower().replace(' ', '_').replace('-', '_') == dep_normalized:
            return comp_id

        # Match on node_name normalized
        node_name = comp_data.get('node_name', '').lower().replace(' ', '_').replace('-', '_')
        if node_name == dep_normalized:
            return comp_id

    # Partial match (for cases like "rules_service" matching "game_rules_service")
    for comp_id, comp_data in components.items():
        if dep_normalized in comp_id.lower():
            return comp_id
        node_name = comp_data.get('node_name', '').lower().replace(' ', '_')
        if dep_normalized in node_name:
            return comp_id

    return None


# =============================================================================
# KNOWLEDGE GAP DETECTION
# =============================================================================

def detect_knowledge_gaps(G: nx.DiGraph, component_data: Dict[str, Dict]) -> Dict[str, List[Dict]]:
    """Identify missing nodes or edges based on graph structure and component data.

    Detects:
    1. Orphaned interfaces: Consumed interface with no provider
    2. Unmet dependencies: Required capability not provided by any component
    3. Implied mediators: Two components interact but incompatible interfaces (missing translator)
    4. Missing feedback: Known effect without path in graph
    5. Structural holes: High betweenness nodes (fragile single points of contact)
    6. Unexplained outputs: Component provides interface but no function generates it

    Returns dictionary of gap types with detected instances.
    """
    gaps = {
        'orphaned_interfaces': [],
        'unmet_dependencies': [],
        'implied_mediators': [],
        'structural_holes': [],
        'unexplained_outputs': [],
        'missing_bidirectional': []
    }

    # Collect all provided and consumed interfaces
    provided_interfaces = defaultdict(list)  # interface_type -> [component_ids]
    consumed_interfaces = defaultdict(list)  # interface_type -> [component_ids]

    for node_id in G.nodes():
        node_data = G.nodes[node_id]
        interfaces = node_data.get('interfaces', [])

        for iface in interfaces:
            if not isinstance(iface, dict):
                continue

            iface_type = iface.get('type', iface.get('interface_type', iface.get('name', 'unknown')))
            direction = iface.get('direction', 'unknown')

            if direction in ['provided', 'out', 'provides']:
                provided_interfaces[iface_type].append(node_id)
            elif direction in ['consumed', 'in', 'requires']:
                consumed_interfaces[iface_type].append(node_id)
            elif direction == 'bidirectional':
                provided_interfaces[iface_type].append(node_id)
                consumed_interfaces[iface_type].append(node_id)

    # 1. Detect orphaned interfaces (consumed but not provided)
    for iface_type, consumers in consumed_interfaces.items():
        if iface_type not in provided_interfaces or len(provided_interfaces[iface_type]) == 0:
            gaps['orphaned_interfaces'].append({
                'interface_type': iface_type,
                'consumers': consumers,
                'severity': 'warning',
                'description': f"Interface '{iface_type}' is consumed by {len(consumers)} component(s) but not provided by any",
                'implication': "Missing component that should provide this interface, or interface type mismatch",
                'recommendation': f"Add component that provides '{iface_type}' interface or verify interface naming"
            })

    # 2. Detect unmet dependencies
    all_provided_capabilities = set()
    for node_id in G.nodes():
        functions = G.nodes[node_id].get('functions', [])
        all_provided_capabilities.update(functions)

    for node_id in G.nodes():
        dependencies = G.nodes[node_id].get('dependencies', [])
        for dep in dependencies:
            # Check if any component provides this capability
            if dep not in G.nodes() and dep not in all_provided_capabilities:
                gaps['unmet_dependencies'].append({
                    'component': node_id,
                    'required_capability': dep,
                    'severity': 'warning',
                    'description': f"Component '{node_id}' requires '{dep}' but no component provides it",
                    'implication': "Missing component or function",
                    'recommendation': f"Add component that provides '{dep}' or add function to existing component"
                })

    # 3. Detect structural holes (high betweenness centrality)
    if G.number_of_nodes() > 2:
        try:
            betweenness = nx.betweenness_centrality(G)
            # Find nodes with exceptionally high betweenness (top 10% or > 0.5)
            threshold = 0.5
            high_betweenness_nodes = [(node, score) for node, score in betweenness.items() if score > threshold]

            for node, score in high_betweenness_nodes:
                # Check if removing this node disconnects the graph
                G_copy = G.copy()
                G_copy.remove_node(node)
                num_components = nx.number_weakly_connected_components(G_copy)

                if num_components > 1:
                    gaps['structural_holes'].append({
                        'broker_node': node,
                        'betweenness_centrality': round(score, 3),
                        'severity': 'info',
                        'description': f"Component '{node}' is a critical broker (betweenness={score:.3f})",
                        'implication': "System fragile; if this component fails, network disconnects",
                        'recommendation': f"Add redundant connections to bypass '{node}' or strengthen this component"
                    })
        except:
            pass  # Graph might not be suitable for betweenness calculation

    # 4. Detect unexplained outputs
    for node_id in G.nodes():
        node_data = G.nodes[node_id]
        interfaces = node_data.get('interfaces', [])
        functions = node_data.get('functions', [])

        for iface in interfaces:
            if not isinstance(iface, dict):
                continue

            direction = iface.get('direction', '')
            if direction in ['provided', 'out', 'provides']:
                iface_name = iface.get('name', iface.get('type', 'unknown'))

                # Check if any function mentions this interface
                function_str = ' '.join(str(f).lower() for f in functions)
                if iface_name.lower() not in function_str:
                    gaps['unexplained_outputs'].append({
                        'component': node_id,
                        'interface': iface_name,
                        'severity': 'info',
                        'description': f"Component '{node_id}' provides '{iface_name}' but no function describes how",
                        'implication': "Missing function documentation or hidden internal mechanism",
                        'recommendation': f"Document function that produces '{iface_name}' interface"
                    })

    # 5. Detect missing bidirectional connections
    # If A->B exists and B->A should exist (bidirectional) but doesn't
    for u, v, data in G.edges(data=True):
        if data.get('direction') == 'bidirectional':
            if not G.has_edge(v, u):
                gaps['missing_bidirectional'].append({
                    'from': u,
                    'to': v,
                    'severity': 'warning',
                    'description': f"Edge {u}->{v} marked bidirectional but reverse edge {v}->{u} missing",
                    'implication': "Inconsistent bidirectional relationship",
                    'recommendation': f"Add edge from '{v}' to '{u}' or change direction to 'directed'"
                })

    return gaps


# =============================================================================
# NETWORKX ANALYSIS - Comprehensive Graph Theory Methods
# =============================================================================

def analyze_centrality(G: nx.DiGraph) -> Dict[str, Any]:
    """Calculate all centrality measures.

    Returns:
        - degree_centrality: Number of connections (in + out)
        - betweenness_centrality: Frequency on shortest paths (brokerage)
        - closeness_centrality: Average distance to all others (reach)
        - eigenvector_centrality: Connected to well-connected nodes (influence)
        - pagerank: Importance based on incoming links
    """
    results = {}

    try:
        results['degree_centrality'] = nx.degree_centrality(G)
    except:
        results['degree_centrality'] = "Error computing degree centrality"

    try:
        results['betweenness_centrality'] = nx.betweenness_centrality(G)
    except:
        results['betweenness_centrality'] = "Error computing betweenness centrality"

    try:
        results['closeness_centrality'] = nx.closeness_centrality(G)
    except:
        results['closeness_centrality'] = "Error computing closeness centrality"

    try:
        results['eigenvector_centrality'] = nx.eigenvector_centrality(G, max_iter=1000)
    except:
        results['eigenvector_centrality'] = "Error computing eigenvector centrality (may not converge)"

    try:
        results['pagerank'] = nx.pagerank(G)
    except:
        results['pagerank'] = "Error computing PageRank"

    # Top nodes for each measure
    top_k = 5
    results['top_nodes'] = {}
    for measure, scores in results.items():
        if isinstance(scores, dict):
            top_nodes = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
            results['top_nodes'][measure] = top_nodes

    return results


def analyze_paths(G: nx.DiGraph) -> Dict[str, Any]:
    """Analyze path-related metrics.

    Returns:
        - shortest_paths: All-pairs shortest paths
        - diameter: Longest shortest path
        - average_path_length: Mean shortest path length
        - eccentricity: Maximum distance from each node
    """
    results = {}

    # For directed graphs, use weakly connected component
    if nx.is_weakly_connected(G):
        try:
            results['diameter'] = nx.diameter(G.to_undirected())
        except:
            results['diameter'] = "Graph not connected or empty"

        try:
            results['average_path_length'] = nx.average_shortest_path_length(G.to_undirected())
        except:
            results['average_path_length'] = "Error computing average path length"
    else:
        results['diameter'] = "Graph not connected (multiple components)"
        results['average_path_length'] = "Graph not connected"

    # Eccentricity (for each node)
    try:
        results['eccentricity'] = nx.eccentricity(G.to_undirected())
    except:
        results['eccentricity'] = "Error computing eccentricity"

    return results


def analyze_connectivity(G: nx.DiGraph) -> Dict[str, Any]:
    """Analyze graph connectivity.

    Returns:
        - connected_components: Number and size of components
        - node_connectivity: Min nodes to remove to disconnect
        - edge_connectivity: Min edges to remove to disconnect
        - bridges: Edges whose removal disconnects graph
    """
    results = {}

    # Connected components (use weakly connected for directed graphs)
    components = list(nx.weakly_connected_components(G))
    results['num_components'] = len(components)
    results['component_sizes'] = [len(c) for c in components]
    results['largest_component_size'] = max(results['component_sizes']) if components else 0

    # Node and edge connectivity (for largest component)
    if len(components) > 0:
        largest_component = max(components, key=len)
        subgraph = G.subgraph(largest_component)

        try:
            results['node_connectivity'] = nx.node_connectivity(subgraph.to_undirected())
        except:
            results['node_connectivity'] = "Error computing node connectivity"

        try:
            results['edge_connectivity'] = nx.edge_connectivity(subgraph.to_undirected())
        except:
            results['edge_connectivity'] = "Error computing edge connectivity"

        # Bridges
        try:
            bridges = list(nx.bridges(subgraph.to_undirected()))
            results['bridges'] = [{"from": u, "to": v} for u, v in bridges]
            results['num_bridges'] = len(bridges)
        except:
            results['bridges'] = "Error finding bridges"

    return results


def analyze_clustering(G: nx.DiGraph) -> Dict[str, Any]:
    """Analyze clustering and community structure.

    Returns:
        - clustering_coefficient: Degree of node clustering
        - transitivity: Global clustering coefficient
        - triangles: Number of triangles per node
    """
    results = {}

    # Convert to undirected for clustering
    G_undirected = G.to_undirected()

    try:
        results['clustering_coefficient'] = nx.clustering(G_undirected)
        results['average_clustering'] = nx.average_clustering(G_undirected)
    except:
        results['clustering_coefficient'] = "Error computing clustering coefficient"

    try:
        results['transitivity'] = nx.transitivity(G_undirected)
    except:
        results['transitivity'] = "Error computing transitivity"

    try:
        results['triangles'] = nx.triangles(G_undirected)
    except:
        results['triangles'] = "Error counting triangles"

    return results


def analyze_properties(G: nx.DiGraph) -> Dict[str, Any]:
    """Calculate general graph properties.

    Returns:
        - density: How close to complete graph
        - assortativity: Tendency of similar nodes to connect
        - reciprocity: Fraction of bidirectional edges
    """
    results = {}

    # Basic stats
    results['num_nodes'] = G.number_of_nodes()
    results['num_edges'] = G.number_of_edges()

    # Density
    try:
        results['density'] = nx.density(G)
    except:
        results['density'] = "Error computing density"

    # Degree assortativity
    try:
        results['degree_assortativity'] = nx.degree_assortativity_coefficient(G)
    except:
        results['degree_assortativity'] = "Error computing assortativity"

    # Reciprocity (for directed graphs)
    try:
        results['reciprocity'] = nx.reciprocity(G)
    except:
        results['reciprocity'] = "Error computing reciprocity"

    # Degree distribution
    degrees = [d for n, d in G.degree()]
    if degrees:
        results['degree_distribution'] = {
            'min': min(degrees),
            'max': max(degrees),
            'mean': sum(degrees) / len(degrees),
            'median': sorted(degrees)[len(degrees) // 2]
        }

    return results


def analyze_communities(G: nx.DiGraph) -> Dict[str, Any]:
    """Detect communities and modules within the graph.

    Returns:
        - louvain_communities: Community detection using Louvain algorithm
        - label_propagation: Fast community detection via label propagation
        - community_count: Number of communities detected
        - modularity: Quality of community division
    """
    results = {}

    # Convert to undirected for community detection
    G_undirected = G.to_undirected()

    # Louvain community detection
    try:
        import networkx.algorithms.community as nx_comm

        # Louvain (greedy modularity optimization)
        communities_louvain = list(nx_comm.greedy_modularity_communities(G_undirected))
        results['louvain_communities'] = {
            'num_communities': len(communities_louvain),
            'sizes': [len(c) for c in communities_louvain],
            'communities': [list(c) for c in communities_louvain[:10]]  # Top 10 only
        }

        # Calculate modularity
        results['modularity'] = nx_comm.modularity(G_undirected, communities_louvain)

    except Exception as e:
        results['louvain_communities'] = f"Error in Louvain: {e}"

    # Label propagation (fast)
    try:
        import networkx.algorithms.community as nx_comm
        communities_lp = list(nx_comm.label_propagation_communities(G_undirected))
        results['label_propagation'] = {
            'num_communities': len(communities_lp),
            'sizes': [len(c) for c in communities_lp]
        }
    except Exception as e:
        results['label_propagation'] = f"Error in label propagation: {e}"

    # Girvan-Newman (slower, limit iterations)
    try:
        import networkx.algorithms.community as nx_comm
        # Only do first few splits for performance
        comp = nx_comm.girvan_newman(G_undirected)
        limited_communities = []
        for i, communities in enumerate(comp):
            if i >= 3:  # Limit to 3 iterations
                break
            limited_communities.append(communities)

        if limited_communities:
            results['girvan_newman'] = {
                'iterations': len(limited_communities),
                'final_num_communities': len(limited_communities[-1]),
                'note': 'Limited to 3 iterations for performance'
            }
    except Exception as e:
        results['girvan_newman'] = f"Error in Girvan-Newman: {e}"

    return results


def analyze_cycles(G: nx.DiGraph) -> Dict[str, Any]:
    """Find cycles and feedback loops in the graph.

    Returns:
        - simple_cycles: All elementary cycles
        - cycle_basis: Fundamental cycles (for undirected)
        - has_cycles: Boolean indicating if cycles exist
        - cycle_count: Number of cycles detected
    """
    results = {}

    # Find simple cycles (directed)
    try:
        cycles = list(nx.simple_cycles(G))
        results['has_cycles'] = len(cycles) > 0
        results['cycle_count'] = len(cycles)

        # Categorize by length
        cycle_lengths = {}
        for cycle in cycles:
            length = len(cycle)
            if length not in cycle_lengths:
                cycle_lengths[length] = 0
            cycle_lengths[length] += 1

        results['cycle_length_distribution'] = cycle_lengths

        # Sample cycles (limit output)
        if len(cycles) <= 20:
            results['cycles'] = cycles
        else:
            results['cycles'] = cycles[:20]
            results['note'] = f"Showing 20 of {len(cycles)} total cycles"

    except Exception as e:
        results['simple_cycles'] = f"Error finding cycles: {e}"

    # Cycle basis (for undirected view)
    try:
        G_undirected = G.to_undirected()
        cycle_basis = nx.cycle_basis(G_undirected)
        results['cycle_basis'] = {
            'num_fundamental_cycles': len(cycle_basis),
            'basis_cycles': cycle_basis[:10]  # Limit to 10
        }
    except Exception as e:
        results['cycle_basis'] = f"Error computing cycle basis: {e}"

    # Identify feedback loops (cycles of length 2-4, common in biological/social networks)
    if 'cycles' in results:
        feedback_loops = [c for c in cycles if 2 <= len(c) <= 4]
        results['feedback_loops'] = {
            'count': len(feedback_loops),
            'examples': feedback_loops[:10]
        }

    return results


def analyze_strongly_connected(G: nx.DiGraph) -> Dict[str, Any]:
    """Analyze strongly connected components (mutually reachable nodes).

    Returns:
        - is_strongly_connected: Boolean for whole graph
        - num_sccs: Number of strongly connected components
        - scc_sizes: Size distribution of SCCs
        - largest_scc: Nodes in largest SCC
        - condensation_graph: DAG of SCCs
    """
    results = {}

    # Check if entire graph is strongly connected
    try:
        results['is_strongly_connected'] = nx.is_strongly_connected(G)
    except:
        results['is_strongly_connected'] = "Error checking strong connectivity"

    # Find all strongly connected components
    try:
        sccs = list(nx.strongly_connected_components(G))
        results['num_sccs'] = len(sccs)

        # Sort by size
        sccs_sorted = sorted(sccs, key=len, reverse=True)
        scc_sizes = [len(scc) for scc in sccs_sorted]

        results['scc_sizes'] = scc_sizes
        results['largest_scc_size'] = scc_sizes[0] if scc_sizes else 0
        results['largest_scc_nodes'] = list(sccs_sorted[0]) if sccs_sorted else []

        # If many small SCCs, likely not well-connected
        single_node_sccs = sum(1 for size in scc_sizes if size == 1)
        results['single_node_sccs'] = single_node_sccs
        results['multi_node_sccs'] = len(sccs) - single_node_sccs

    except Exception as e:
        results['sccs'] = f"Error finding SCCs: {e}"

    # Create condensation graph (DAG of SCCs)
    try:
        condensation = nx.condensation(G)
        results['condensation'] = {
            'num_nodes': condensation.number_of_nodes(),
            'num_edges': condensation.number_of_edges(),
            'is_dag': nx.is_directed_acyclic_graph(condensation),
            'note': 'Each node represents an SCC from original graph'
        }
    except Exception as e:
        results['condensation'] = f"Error creating condensation: {e}"

    return results


def analyze_dag(G: nx.DiGraph) -> Dict[str, Any]:
    """Analyze directed acyclic graph properties.

    Returns:
        - is_dag: Boolean indicating if graph is a DAG
        - topological_sort: Node ordering (if DAG)
        - longest_path: Longest path through DAG
        - levels: Nodes grouped by topological level
    """
    results = {}

    # Check if DAG
    try:
        is_dag = nx.is_directed_acyclic_graph(G)
        results['is_dag'] = is_dag
    except:
        results['is_dag'] = "Error checking DAG property"
        return results

    if not is_dag:
        results['note'] = "Graph is not a DAG (contains cycles). Remove cycles for DAG analysis."
        # Try to identify cycles blocking DAG
        try:
            cycles = list(nx.simple_cycles(G))
            results['blocking_cycles'] = {
                'count': len(cycles),
                'sample': cycles[:5]
            }
        except:
            pass
        return results

    # Topological sort
    try:
        topo_sort = list(nx.topological_sort(G))
        results['topological_sort'] = topo_sort
        results['num_nodes_sorted'] = len(topo_sort)
    except Exception as e:
        results['topological_sort'] = f"Error in topological sort: {e}"

    # Longest path
    try:
        longest = nx.dag_longest_path(G)
        results['longest_path'] = {
            'path': longest,
            'length': len(longest) - 1  # Number of edges
        }

        # Try to compute longest path length with weights if available
        try:
            longest_len = nx.dag_longest_path_length(G)
            results['longest_path']['weighted_length'] = longest_len
        except:
            pass

    except Exception as e:
        results['longest_path'] = f"Error computing longest path: {e}"

    # Topological generations (levels)
    try:
        generations = list(nx.topological_generations(G))
        results['topological_levels'] = {
            'num_levels': len(generations),
            'nodes_per_level': [len(gen) for gen in generations],
            'levels': [list(gen) for gen in generations[:10]]  # Limit to 10 levels
        }
    except Exception as e:
        results['topological_levels'] = f"Error computing levels: {e}"

    # Antichains (nodes with no ordering relation)
    try:
        antichains = list(nx.antichains(G))
        results['antichains'] = {
            'count': len(antichains),
            'note': 'Sets of nodes with no ordering relationship'
        }
    except Exception as e:
        results['antichains'] = f"Error finding antichains: {e}"

    return results


def analyze_flow(G: nx.DiGraph) -> Dict[str, Any]:
    """Analyze flow and capacity in the graph.

    Returns:
        - maximum_flow: Max flow between high-degree nodes
        - flow_algorithms: Different flow algorithms applied
        - cut_sets: Minimum cuts
    """
    results = {}

    # For flow analysis, we need source and sink nodes
    # Heuristic: Use nodes with highest out-degree and in-degree

    try:
        # Find potential sources (high out-degree, low in-degree)
        out_degrees = dict(G.out_degree())
        in_degrees = dict(G.in_degree())

        # Source candidates: high out-degree
        source_candidates = sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
        # Sink candidates: high in-degree
        sink_candidates = sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]

        if not source_candidates or not sink_candidates:
            results['note'] = "No suitable source/sink nodes for flow analysis"
            return results

        source = source_candidates[0][0]
        sink = sink_candidates[0][0]

        if source == sink:
            # Pick different sink
            sink = sink_candidates[1][0] if len(sink_candidates) > 1 else sink_candidates[0][0]

        results['flow_analysis_nodes'] = {
            'source': source,
            'sink': sink,
            'source_out_degree': out_degrees[source],
            'sink_in_degree': in_degrees[sink]
        }

    except Exception as e:
        results['node_selection'] = f"Error selecting source/sink: {e}"
        return results

    # Maximum flow (assume capacity=1 for unweighted, or use 'weight' attribute)
    try:
        flow_value, flow_dict = nx.maximum_flow(G, source, sink)
        results['maximum_flow'] = {
            'value': flow_value,
            'source': source,
            'sink': sink,
            'note': 'Assuming unit capacity on all edges (or weight attribute if present)'
        }

        # Count non-zero flows
        non_zero_flows = sum(1 for node_flows in flow_dict.values()
                            for flow in node_flows.values() if flow > 0)
        results['maximum_flow']['edges_with_flow'] = non_zero_flows

    except Exception as e:
        results['maximum_flow'] = f"Error computing max flow: {e}"

    # Minimum cut
    try:
        cut_value, partition = nx.minimum_cut(G, source, sink)
        results['minimum_cut'] = {
            'cut_value': cut_value,
            'partition_sizes': [len(partition[0]), len(partition[1])],
            'note': 'Minimum capacity to separate source from sink'
        }
    except Exception as e:
        results['minimum_cut'] = f"Error computing min cut: {e}"

    # For directed graphs, check if flow is feasible
    try:
        # Node connectivity (min nodes to remove to disconnect)
        node_conn = nx.node_connectivity(G, source, sink)
        results['node_connectivity'] = {
            'source_to_sink': node_conn,
            'note': 'Minimum nodes to remove to disconnect source from sink'
        }
    except Exception as e:
        results['node_connectivity'] = f"Error: {e}"

    return results


def analyze_context_flow(G: nx.DiGraph, threshold: int = 40000) -> Dict[str, Any]:
    """Analyze LLM context flow through workflow paths (v3.9.0).

    Models LLM context as a flow parameter, predicting cumulative token
    accumulation and identifying bottlenecks before overflow occurs.

    Args:
        G: Directed graph with workflow steps
        threshold: Context threshold in tokens (default: 40000)

    Returns:
        - paths: All workflow paths with cumulative context
        - bottlenecks: Steps exceeding threshold
        - refresh_points: Recommended context refresh locations
        - optimization_opportunities: Suggestions for reducing context cost
    """
    results = {
        'metadata': {
            'threshold_tokens': threshold,
            'analysis_date': datetime.now().isoformat()
        }
    }

    try:
        # Find start and end nodes (nodes with 0 in-degree and 0 out-degree)
        in_degrees = dict(G.in_degree())
        out_degrees = dict(G.out_degree())

        start_nodes = [n for n, d in in_degrees.items() if d == 0]
        end_nodes = [n for n, d in out_degrees.items() if d == 0]

        if not start_nodes:
            # No pure start nodes, use nodes with lowest in-degree
            start_nodes = sorted(in_degrees.items(), key=lambda x: x[1])[:3]
            start_nodes = [n for n, d in start_nodes]

        if not end_nodes:
            # No pure end nodes, use nodes with lowest out-degree
            end_nodes = sorted(out_degrees.items(), key=lambda x: x[1])[:3]
            end_nodes = [n for n, d in end_nodes]

        results['workflow_endpoints'] = {
            'start_nodes': start_nodes,
            'end_nodes': end_nodes
        }

    except Exception as e:
        results['error'] = f"Error identifying workflow endpoints: {e}"
        return results

    # Analyze paths from each start to each end
    all_paths = []
    bottlenecks = []
    refresh_recommendations = []

    for start in start_nodes:
        for end in end_nodes:
            if start == end:
                continue

            try:
                # Find all simple paths (no cycles)
                paths = list(nx.all_simple_paths(G, start, end, cutoff=50))  # Max 50 steps

                for path in paths[:10]:  # Analyze first 10 paths to avoid explosion
                    path_analysis = {
                        'path': path,
                        'length': len(path),
                        'steps': []
                    }

                    cumulative_context = 0
                    step_bottlenecks = []

                    for i, step_id in enumerate(path):
                        node_data = G.nodes[step_id]

                        # Extract context cost from node metadata
                        context_cost = 0
                        if 'context_metadata' in node_data:
                            context_cost = node_data['context_metadata'].get('context_cost', 0)
                        elif 'context_cost' in node_data:
                            context_cost = node_data['context_cost']
                        else:
                            # Default estimates based on step type
                            if 'SE-06' in step_id or 'GraphGeneration' in str(node_data.get('step_name', '')):
                                context_cost = 15000  # Heavy step
                            elif 'SE-' in step_id or 'BU-' in step_id:
                                context_cost = 8000   # Architecture steps
                            elif 'D-' in step_id:
                                context_cost = 10000  # Development steps
                            elif 'AV-' in step_id:
                                context_cost = 5000   # Visualization steps
                            else:
                                context_cost = 3000   # Default steps

                        cumulative_context += context_cost

                        step_info = {
                            'step_id': step_id,
                            'step_name': node_data.get('step_name', 'Unknown'),
                            'context_cost': context_cost,
                            'cumulative_context': cumulative_context,
                            'position': i
                        }

                        # Check for bottleneck
                        if cumulative_context > threshold:
                            severity = 'CRITICAL' if cumulative_context > threshold * 1.25 else 'WARNING'
                            step_bottlenecks.append({
                                **step_info,
                                'severity': severity,
                                'overflow_tokens': cumulative_context - threshold
                            })

                        path_analysis['steps'].append(step_info)

                    path_analysis['total_cumulative_context'] = cumulative_context
                    path_analysis['bottlenecks'] = step_bottlenecks

                    # Generate refresh recommendations for this path
                    if step_bottlenecks:
                        for bottleneck in step_bottlenecks:
                            # Recommend refresh before the bottleneck step
                            refresh_point = path[max(0, bottleneck['position'] - 1)]
                            refresh_recommendations.append({
                                'path_id': f"{start}_to_{end}",
                                'refresh_before_step': bottleneck['step_id'],
                                'refresh_after_step': refresh_point,
                                'reason': f"Predicted overflow ({bottleneck['cumulative_context']} tokens > {threshold} threshold)",
                                'severity': bottleneck['severity']
                            })

                    all_paths.append(path_analysis)
                    bottlenecks.extend(step_bottlenecks)

            except nx.NetworkXNoPath:
                pass  # No path exists between these nodes
            except Exception as e:
                results['path_analysis_errors'] = results.get('path_analysis_errors', [])
                results['path_analysis_errors'].append(f"Error analyzing path {start}→{end}: {e}")

    # Summarize results
    results['paths_analyzed'] = len(all_paths)
    results['paths'] = all_paths[:5]  # Include first 5 paths in detail
    results['bottlenecks'] = {
        'total_count': len(bottlenecks),
        'critical_count': len([b for b in bottlenecks if b.get('severity') == 'CRITICAL']),
        'warning_count': len([b for b in bottlenecks if b.get('severity') == 'WARNING']),
        'details': bottlenecks[:10]  # First 10 bottlenecks
    }
    results['refresh_recommendations'] = {
        'total_count': len(refresh_recommendations),
        'recommendations': refresh_recommendations[:10]  # First 10 recommendations
    }

    # Optimization opportunities
    if all_paths:
        max_cumulative = max(p['total_cumulative_context'] for p in all_paths)
        min_cumulative = min(p['total_cumulative_context'] for p in all_paths)
        avg_cumulative = sum(p['total_cumulative_context'] for p in all_paths) / len(all_paths)

        results['optimization_opportunities'] = {
            'max_cumulative_context': max_cumulative,
            'min_cumulative_context': min_cumulative,
            'avg_cumulative_context': avg_cumulative,
            'context_efficiency': 'HIGH' if avg_cumulative < threshold else ('MEDIUM' if avg_cumulative < threshold * 1.5 else 'LOW'),
            'suggestions': []
        }

        if max_cumulative > threshold * 2:
            results['optimization_opportunities']['suggestions'].append(
                "Consider splitting high-context steps or inserting additional refresh points"
            )

        if max_cumulative - min_cumulative > threshold:
            results['optimization_opportunities']['suggestions'].append(
                f"Path variation is high ({max_cumulative - min_cumulative} tokens). Consider workflow refactoring for consistency."
            )

    return results


def run_all_analysis(G: nx.DiGraph) -> Dict[str, Any]:
    """Run all NetworkX analysis methods and return comprehensive results."""
    print("Running comprehensive NetworkX analysis...")

    analysis_results = {
        'metadata': {
            'analysis_date': datetime.now().isoformat(),
            'num_nodes': G.number_of_nodes(),
            'num_edges': G.number_of_edges()
        }
    }

    print("  - Computing centrality measures...")
    analysis_results['centrality'] = analyze_centrality(G)

    print("  - Analyzing paths and distances...")
    analysis_results['paths'] = analyze_paths(G)

    print("  - Analyzing connectivity...")
    analysis_results['connectivity'] = analyze_connectivity(G)

    print("  - Analyzing clustering...")
    analysis_results['clustering'] = analyze_clustering(G)

    print("  - Computing graph properties...")
    analysis_results['properties'] = analyze_properties(G)

    print("  - Detecting communities...")
    analysis_results['communities'] = analyze_communities(G)

    print("  - Finding cycles and feedback loops...")
    analysis_results['cycles'] = analyze_cycles(G)

    print("  - Analyzing strongly connected components...")
    analysis_results['strongly_connected'] = analyze_strongly_connected(G)

    print("  - Analyzing DAG properties...")
    analysis_results['dag'] = analyze_dag(G)

    print("  - Analyzing flow and capacity...")
    analysis_results['flow'] = analyze_flow(G)

    return analysis_results


# =============================================================================
# ARCHITECTURAL ISSUE DETECTION (from v1, enhanced)
# =============================================================================

def detect_architectural_issues(G: nx.DiGraph, system_root: Optional[Path] = None) -> Dict[str, List[Dict]]:
    """Detect architectural problems (circular deps, orphans, etc.).

    Enhanced version from v1 with framework-agnostic support.
    Includes detection of unimplemented services (scaffolding without code).

    Args:
        G: NetworkX DiGraph
        system_root: System root directory (Path object, already validated)
    """
    issues = {
        'circular_dependencies': [],
        'orphaned_nodes': [],
        'unimplemented_services': [],
        'missing_interfaces': [],
        'inconsistent_protocols': [],
        'security_gaps': [],
        'performance_bottlenecks': [],
        'async_sync_consistency': []
    }

    # 1. Circular dependencies
    try:
        cycles = list(nx.simple_cycles(G))
        for cycle in cycles:
            if len(cycle) > 1:  # Ignore self-loops
                issues['circular_dependencies'].append({
                    'cycle': cycle,
                    'severity': 'error',
                    'description': f"Circular dependency detected: {' -> '.join(cycle)} -> {cycle[0]}",
                    'recommendation': "Break cycle by introducing interface, reversing dependency, or using event-driven pattern"
                })
    except:
        pass

    # 2. Orphaned nodes (no connections)
    for node in G.nodes():
        if G.degree(node) == 0:
            issues['orphaned_nodes'].append({
                'node': node,
                'severity': 'warning',
                'description': f"Component '{node}' has no connections to other components",
                'recommendation': "Verify if component should be connected or remove if unused"
            })

    # 3. Performance bottlenecks (high in-degree)
    for node in G.nodes():
        in_degree = G.in_degree(node)
        if in_degree > 5:
            issues['performance_bottlenecks'].append({
                'node': node,
                'in_degree': in_degree,
                'severity': 'info',
                'description': f"Component '{node}' has high fan-in ({in_degree} dependencies)",
                'recommendation': "Consider load testing, caching, or splitting into multiple components"
            })

    # 4. Unimplemented services (architecture defined but no code)
    if system_root:
        services_dir = system_root / 'services'
        if services_dir.exists():
            for node in G.nodes():
                node_data = G.nodes[node]
                node_type = node_data.get('type', '')

                # Only check for services/components that should have implementations
                # Skip external services and interface protocols
                if node_type in ['external', 'interface_protocol']:
                    continue

                # Check if implementation directory exists
                service_impl_dir = services_dir / node

                if not service_impl_dir.exists():
                    issues['unimplemented_services'].append({
                        'node': node,
                        'severity': 'error',
                        'description': f"Service '{node}' has architecture defined but no implementation found",
                        'expected_path': service_impl_dir,
                        'recommendation': f"Implement service in {service_impl_dir} or remove from architecture if not needed"
                    })
                else:
                    # Check if directory has actual code (not just scaffolding)
                    has_code = False
                    code_extensions = ['.py', '.java', '.ts', '.js', '.go', '.rs', '.cpp', '.c']

                    try:
                        for root, dirs, files in os.walk(service_impl_dir):
                            for file in files:
                                if any(file.endswith(ext) for ext in code_extensions):
                                    # Check if file has substantial content (more than just imports/scaffolding)
                                    file_path = os.path.join(root, file)
                                    try:
                                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                            content = f.read()
                                            # Basic heuristic: more than 50 lines or contains "def"/"function"/"class"
                                            if len(content.splitlines()) > 50 or \
                                               any(keyword in content for keyword in ['def ', 'function ', 'class ', 'public class', 'func ']):
                                                has_code = True
                                                break
                                    except:
                                        pass
                            if has_code:
                                break

                        if not has_code:
                            issues['unimplemented_services'].append({
                                'node': node,
                                'severity': 'warning',
                                'description': f"Service '{node}' has scaffolding but appears to lack substantial implementation",
                                'service_path': service_impl_dir,
                                'recommendation': f"Complete implementation in {service_impl_dir} or mark as in-progress"
                            })
                    except:
                        pass

    return issues


# =============================================================================
# OUTPUT GENERATION
# =============================================================================

def generate_output(G: nx.DiGraph, output_path: str, framework_config: Dict,
                   knowledge_gaps: Optional[Dict] = None,
                   architectural_issues: Optional[Dict] = None,
                   analysis_results: Optional[Dict] = None):
    """Generate system-of-systems graph JSON output."""

    # Convert graph to node-link format
    graph_data = nx.node_link_data(G)

    # Build output structure
    output = {
        'metadata': {
            'generated': datetime.now().isoformat(),
            'framework': framework_config.get('framework_name', 'Unknown'),
            'framework_id': framework_config.get('framework_id', 'unknown'),
            'component_term': framework_config.get('component_term', 'component'),
            'connection_term': framework_config.get('connection_term', 'connection'),
            'num_nodes': G.number_of_nodes(),
            'num_edges': G.number_of_edges(),
            'tool_version': '2.0'
        },
        'graph': graph_data
    }

    if knowledge_gaps:
        output['knowledge_gaps'] = knowledge_gaps
        # Summary
        total_gaps = sum(len(v) for v in knowledge_gaps.values())
        output['knowledge_gaps_summary'] = {
            'total_gaps': total_gaps,
            'by_type': {k: len(v) for k, v in knowledge_gaps.items()}
        }

    if architectural_issues:
        output['architectural_issues'] = architectural_issues
        # Summary
        total_issues = sum(len(v) for v in architectural_issues.values())
        output['architectural_issues_summary'] = {
            'total_issues': total_issues,
            'by_type': {k: len(v) for k, v in architectural_issues.items()}
        }

    if analysis_results:
        output['graph_analysis'] = analysis_results

    # Write output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput written to: {output_path}")
    print(f"Framework: {framework_config.get('framework_name')}")
    print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

    if knowledge_gaps:
        total_gaps = sum(len(v) for v in knowledge_gaps.values())
        print(f"Knowledge gaps detected: {total_gaps}")

    if architectural_issues:
        total_issues = sum(len(v) for v in architectural_issues.values())
        print(f"Architectural issues detected: {total_issues}")


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='System-of-Systems Graph Generator v2.0 - Framework-Agnostic Edition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Basic usage (UAF framework, auto-detected from working_memory.json)
  python3 system_of_systems_graph_v2.py /path/to/system/specs/machine/index.json

  # With knowledge gap detection
  python3 system_of_systems_graph_v2.py index.json --detect-gaps

  # With comprehensive NetworkX analysis
  python3 system_of_systems_graph_v2.py index.json --analyze-all

  # Specific analysis methods
  python3 system_of_systems_graph_v2.py index.json --centrality --paths --clustering

  # Custom output location
  python3 system_of_systems_graph_v2.py index.json -o custom_graph.json

Supported Frameworks:
  - UAF 1.2 (Unified Architecture Framework) - default
  - Systems Biology (gene networks, metabolic pathways)
  - Social Network Analysis (organizations, communities)
  - Ecological Systems (food webs, ecosystems)
  - Complex Adaptive Systems (markets, emergent systems)
  - Custom (user-defined frameworks)
        '''
    )

    parser.add_argument('index_file', help='Path to index.json file')
    parser.add_argument('-o', '--output', help='Output file path (default: system_of_systems_graph.json)')
    parser.add_argument('--system-root', help='System root directory (if not provided, derived from index.json location or read from working_memory.json)')

    # Analysis flags
    parser.add_argument('--detect-gaps', action='store_true',
                       help='Enable knowledge gap detection')
    parser.add_argument('--analyze-issues', action='store_true',
                       help='Detect architectural issues (circular deps, orphans, etc.)')

    # NetworkX analysis options
    parser.add_argument('--centrality', action='store_true',
                       help='Compute centrality measures (degree, betweenness, closeness, eigenvector, PageRank)')
    parser.add_argument('--paths', action='store_true',
                       help='Analyze paths (shortest paths, diameter, average path length)')
    parser.add_argument('--connectivity', action='store_true',
                       help='Analyze connectivity (components, bridges, connectivity metrics)')
    parser.add_argument('--clustering', action='store_true',
                       help='Analyze clustering (clustering coefficient, transitivity)')
    parser.add_argument('--properties', action='store_true',
                       help='Compute graph properties (density, assortativity, reciprocity)')
    parser.add_argument('--community', action='store_true',
                       help='Detect communities (Louvain, label propagation, Girvan-Newman)')
    parser.add_argument('--cycles', action='store_true',
                       help='Find cycles and feedback loops')
    parser.add_argument('--scc', action='store_true',
                       help='Analyze strongly connected components')
    parser.add_argument('--dag', action='store_true',
                       help='Analyze DAG properties (topological sort, longest path, levels)')
    parser.add_argument('--flow', action='store_true',
                       help='Analyze flow (maximum flow, minimum cut, node connectivity)')
    parser.add_argument('--context-flow', action='store_true',
                       help='Analyze context flow (LLM token accumulation, bottlenecks, refresh points) - v3.9.0')
    parser.add_argument('--context-threshold', type=int, default=40000,
                       help='Context threshold in tokens for bottleneck detection (default: 40000)')
    parser.add_argument('--analyze-all', action='store_true',
                       help='Run all analysis methods (centrality, paths, connectivity, clustering, properties, community, cycles, scc, dag, flow)')

    args = parser.parse_args()

    # Security: Validate and sanitize all paths (v3.4.0 fix - SV-01)
    try:
        # Determine system root first (needed for path validation)
        if args.system_root:
            # Use explicitly provided system root (validate it exists and is a directory)
            system_root = validate_system_root(args.system_root)
            print(f"System root: {system_root} (explicitly provided)")
        else:
            # Try to derive from index file location or working_memory.json
            # First resolve index_file to find potential system_root
            index_path_preliminary = Path(args.index_file).resolve()

            # Try specs/machine/index.json → go up to system root
            if index_path_preliminary.name == 'index.json' and index_path_preliminary.parent.name == 'machine':
                potential_system_root = index_path_preliminary.parent.parent.parent
            else:
                potential_system_root = Path.cwd()

            # Try to read from working_memory.json
            possible_wm_paths = [
                potential_system_root / 'context' / 'working_memory.json',
                Path.cwd() / 'context' / 'working_memory.json',
            ]

            system_root_from_wm = None
            for wm_path in possible_wm_paths:
                if wm_path.exists():
                    try:
                        wm_data = safe_load_json(wm_path, file_type_description="working memory")
                        system_root_str = wm_data.get('path_configuration', {}).get('system_root')
                        if system_root_str:
                            system_root_from_wm = Path(system_root_str).resolve()
                            print(f"System root: {system_root_from_wm} (from working_memory.json)")
                            break
                    except Exception as e:
                        pass  # Continue to next option

            if system_root_from_wm:
                system_root = validate_system_root(system_root_from_wm)
            else:
                # Fall back to deriving from index file path
                system_root = validate_system_root(potential_system_root)
                print(f"System root: {system_root} (derived from index.json location)")

        # Now validate index_file path relative to system_root
        index_path = sanitize_path(args.index_file, system_root, must_exist=True)
        print(f"Index file: {index_path}")

    except PathSecurityError as e:
        print(f"ERROR: Path security violation: {e}", file=sys.stderr)
        print(f"Paths must be within system root or explicitly trusted.", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    # Load framework configuration
    print("\nLoading framework configuration...")
    framework_config = load_framework_config(system_root)
    print(f"Framework: {framework_config['framework_name']} ({framework_config['framework_id']})")
    print(f"Terminology: {framework_config['component_term']} nodes connected by {framework_config['connection_term']} edges")

    # Load framework schema
    framework_schema = load_framework_registry(framework_config['framework_id'])

    # Load index
    print("\nLoading component index...")
    index = load_component_index(index_path)
    print(f"Found {len(index)} components in index")

    # Build graph
    print("\nBuilding system-of-systems graph...")
    G = build_universal_graph(index, framework_schema, system_root)

    # Optional: Detect knowledge gaps
    knowledge_gaps = None
    if args.detect_gaps:
        print("\nDetecting knowledge gaps...")
        # Need component data for gap detection
        component_data = {}
        for comp_id in G.nodes():
            raw_data = G.nodes[comp_id].get('raw', {})
            component_data[comp_id] = {
                'node_id': comp_id,
                'node_name': G.nodes[comp_id].get('name'),
                'node_type': G.nodes[comp_id].get('type'),
                'functions': G.nodes[comp_id].get('functions', []),
                'interfaces': G.nodes[comp_id].get('interfaces', []),
                'raw': raw_data
            }

        knowledge_gaps = detect_knowledge_gaps(G, component_data)
        total_gaps = sum(len(v) for v in knowledge_gaps.values())
        print(f"Detected {total_gaps} potential knowledge gaps")
        for gap_type, gaps in knowledge_gaps.items():
            if gaps:
                print(f"  - {gap_type}: {len(gaps)}")

    # Optional: Detect architectural issues
    architectural_issues = None
    if args.analyze_issues:
        print("\nDetecting architectural issues...")
        architectural_issues = detect_architectural_issues(G, system_root)
        total_issues = sum(len(v) for v in architectural_issues.values())
        print(f"Detected {total_issues} architectural issues")
        for issue_type, issues in architectural_issues.items():
            if issues:
                print(f"  - {issue_type}: {len(issues)}")

    # Optional: Run NetworkX analysis
    analysis_results = None
    if args.analyze_all or any([args.centrality, args.paths, args.connectivity,
                                args.clustering, args.properties, args.community,
                                args.cycles, args.scc, args.dag, args.flow]):
        analysis_results = {}

        if args.analyze_all or args.centrality:
            analysis_results['centrality'] = analyze_centrality(G)

        if args.analyze_all or args.paths:
            analysis_results['paths'] = analyze_paths(G)

        if args.analyze_all or args.connectivity:
            analysis_results['connectivity'] = analyze_connectivity(G)

        if args.analyze_all or args.clustering:
            analysis_results['clustering'] = analyze_clustering(G)

        if args.analyze_all or args.properties:
            analysis_results['properties'] = analyze_properties(G)

        if args.analyze_all or args.community:
            analysis_results['communities'] = analyze_communities(G)

        if args.analyze_all or args.cycles:
            analysis_results['cycles'] = analyze_cycles(G)

        if args.analyze_all or args.scc:
            analysis_results['strongly_connected'] = analyze_strongly_connected(G)

        if args.analyze_all or args.dag:
            analysis_results['dag'] = analyze_dag(G)

        if args.analyze_all or args.flow:
            analysis_results['flow'] = analyze_flow(G)

        if args.context_flow:
            print("\nAnalyzing context flow...")

            # v3.9.1: Try to load LLM-specific threshold from working_memory.json
            detected_threshold = None
            llm_model_name = "Unknown LLM"

            possible_wm_paths = [
                system_root / 'context' / 'working_memory.json',
                Path.cwd() / 'context' / 'working_memory.json',
            ]

            for wm_path in possible_wm_paths:
                if wm_path.exists():
                    try:
                        with open(wm_path, 'r') as f:
                            wm_data = json.load(f)

                        llm_caps = wm_data.get('context_management', {}).get('llm_capabilities', {})
                        if llm_caps.get('recommended_threshold'):
                            detected_threshold = llm_caps['recommended_threshold']
                            llm_model_name = llm_caps.get('model_name', 'Unknown LLM')
                            print(f"✅ Using auto-detected threshold for {llm_model_name}: {detected_threshold:,} tokens")
                            break
                    except Exception as e:
                        pass  # Continue to next option or use default

            # Use detected threshold if available, otherwise use command-line argument
            threshold_to_use = detected_threshold if detected_threshold else args.context_threshold

            if not detected_threshold:
                print(f"ℹ️  Using default threshold: {threshold_to_use:,} tokens")
                print(f"   Tip: Run detect_llm_capabilities.py for model-specific thresholds")

            analysis_results['context_flow'] = analyze_context_flow(G, threshold=threshold_to_use)
            cf = analysis_results['context_flow']
            print(f"Analyzed {cf.get('paths_analyzed', 0)} workflow paths")
            print(f"Found {cf.get('bottlenecks', {}).get('total_count', 0)} context bottlenecks")
            print(f"Generated {cf.get('refresh_recommendations', {}).get('total_count', 0)} refresh recommendations")

    # Generate output (with path security validation)
    try:
        if args.output:
            # Validate user-provided output path
            output_path = sanitize_path(args.output, system_root, must_exist=False)
        else:
            # Default output location
            output_dir = sanitize_path('specs/machine/graphs', system_root, must_exist=False)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / 'system_of_systems_graph.json'

        generate_output(G, str(output_path), framework_config, knowledge_gaps,
                       architectural_issues, analysis_results)
    except PathSecurityError as e:
        print(f"ERROR: Output path security violation: {e}", file=sys.stderr)
        sys.exit(1)

    print("\n✓ Graph generation complete!")


if __name__ == '__main__':
    main()
