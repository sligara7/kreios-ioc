#!/usr/bin/env python3
"""
Compare Architectures Tool - PRODUCTION VERSION
Compares two architecture graphs and generates delta report

Usage:
    python3 compare_architectures.py \
        --from specs/machine/graphs/system_of_systems_graph.json \
        --to specs/machine/graphs/system_of_systems_graph_as_built.json \
        --output specs/machine/graphs/architecture_delta_designed_to_built_20251026.json
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime

VERSION = "1.0.0"

def load_json(file_path: Path) -> Dict[str, Any]:
    """Load JSON file"""
    with open(file_path, 'r') as f:
        return json.load(f)

def save_json(data: Dict[str, Any], file_path: Path):
    """Save JSON file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def extract_nodes(graph: Dict) -> Dict[str, Dict]:
    """Extract nodes as dict {node_id: node_data}"""
    nodes = {}
    for node in graph.get('nodes', []):
        node_id = node.get('id') or node.get('service_id') or node.get('component_id')
        if node_id:
            nodes[node_id] = node
    return nodes

def extract_edges(graph: Dict) -> Dict[Tuple[str, str], Dict]:
    """Extract edges as dict {(from, to): edge_data}"""
    edges = {}
    for edge in graph.get('edges', []):
        from_node = edge.get('from') or edge.get('source')
        to_node = edge.get('to') or edge.get('target')
        if from_node and to_node:
            edges[(from_node, to_node)] = edge
    return edges

def compute_node_deltas(nodes_a: Dict, nodes_b: Dict) -> Dict:
    """Compute node deltas (added, removed, modified)"""
    set_a = set(nodes_a.keys())
    set_b = set(nodes_b.keys())

    added = set_b - set_a
    removed = set_a - set_b
    common = set_a & set_b

    modified = []
    for node_id in common:
        node_a = nodes_a[node_id]
        node_b = nodes_b[node_id]

        # Check for property changes
        changed_props = []
        for key in set(node_a.keys()) | set(node_b.keys()):
            if node_a.get(key) != node_b.get(key):
                changed_props.append(key)

        if changed_props:
            modified.append({
                "node_id": node_id,
                "changed_properties": changed_props,
                "from": {k: node_a.get(k) for k in changed_props},
                "to": {k: node_b.get(k) for k in changed_props}
            })

    return {
        "added": [{"node_id": nid, **nodes_b[nid]} for nid in added],
        "removed": [{"node_id": nid, **nodes_a[nid]} for nid in removed],
        "modified": modified
    }

def compute_edge_deltas(edges_a: Dict, edges_b: Dict) -> Dict:
    """Compute edge deltas (added, removed, modified)"""
    set_a = set(edges_a.keys())
    set_b = set(edges_b.keys())

    added = set_b - set_a
    removed = set_a - set_b
    common = set_a & set_b

    modified = []
    for edge_key in common:
        edge_a = edges_a[edge_key]
        edge_b = edges_b[edge_key]

        # Check for property changes
        changed_props = []
        for key in set(edge_a.keys()) | set(edge_b.keys()):
            if edge_a.get(key) != edge_b.get(key):
                changed_props.append(key)

        if changed_props:
            modified.append({
                "from_node": edge_key[0],
                "to_node": edge_key[1],
                "changed_properties": changed_props,
                "from": {k: edge_a.get(k) for k in changed_props},
                "to": {k: edge_b.get(k) for k in changed_props}
            })

    return {
        "added": [{"from": k[0], "to": k[1], **edges_b[k]} for k in added],
        "removed": [{"from": k[0], "to": k[1], **edges_a[k]} for k in removed],
        "modified": modified
    }

def calculate_similarity(nodes_a: Dict, nodes_b: Dict, edges_a: Dict, edges_b: Dict) -> Dict:
    """Calculate similarity scores"""
    # Node similarity (Jaccard)
    node_union = set(nodes_a.keys()) | set(nodes_b.keys())
    node_intersection = set(nodes_a.keys()) & set(nodes_b.keys())
    node_similarity = len(node_intersection) / len(node_union) if node_union else 0.0

    # Edge similarity (Jaccard)
    edge_union = set(edges_a.keys()) | set(edges_b.keys())
    edge_intersection = set(edges_a.keys()) & set(edges_b.keys())
    edge_similarity = len(edge_intersection) / len(edge_union) if edge_union else 0.0

    # Property similarity (for common nodes/edges)
    property_matches = 0
    property_total = 0

    for node_id in node_intersection:
        node_a = nodes_a[node_id]
        node_b = nodes_b[node_id]
        all_keys = set(node_a.keys()) | set(node_b.keys())
        matches = sum(1 for k in all_keys if node_a.get(k) == node_b.get(k))
        property_matches += matches
        property_total += len(all_keys)

    for edge_key in edge_intersection:
        edge_a = edges_a[edge_key]
        edge_b = edges_b[edge_key]
        all_keys = set(edge_a.keys()) | set(edge_b.keys())
        matches = sum(1 for k in all_keys if edge_a.get(k) == edge_b.get(k))
        property_matches += matches
        property_total += len(all_keys)

    property_similarity = property_matches / property_total if property_total else 0.0

    # Overall similarity (weighted average)
    overall = 0.4 * node_similarity + 0.4 * edge_similarity + 0.2 * property_similarity

    return {
        "overall": round(overall, 3),
        "breakdown": {
            "nodes": round(node_similarity, 3),
            "edges": round(edge_similarity, 3),
            "properties": round(property_similarity, 3)
        }
    }

def classify_changes(node_deltas: Dict, edge_deltas: Dict) -> Dict:
    """Classify changes as breaking or non-breaking"""
    breaking = []
    non_breaking = []

    # Removed nodes/edges are breaking
    for node in node_deltas["removed"]:
        breaking.append({
            "change_id": f"BC-NODE-{node['node_id']}",
            "type": "removed_node",
            "description": f"Node '{node['node_id']}' was removed",
            "impact": "Dependent services may fail",
            "recommendation": "Restore node or update dependents"
        })

    for edge in edge_deltas["removed"]:
        breaking.append({
            "change_id": f"BC-EDGE-{edge['from']}-{edge['to']}",
            "type": "removed_interface",
            "description": f"Interface from '{edge['from']}' to '{edge['to']}' was removed",
            "impact": "Integration broken",
            "recommendation": "Restore interface or update design"
        })

    # Added nodes/edges are non-breaking
    for node in node_deltas["added"]:
        non_breaking.append({
            "change_id": f"NBC-NODE-{node['node_id']}",
            "type": "added_node",
            "description": f"Node '{node['node_id']}' was added",
            "impact": "Backward compatible addition"
        })

    for edge in edge_deltas["added"]:
        non_breaking.append({
            "change_id": f"NBC-EDGE-{edge['from']}-{edge['to']}",
            "type": "added_interface",
            "description": f"Interface from '{edge['from']}' to '{edge['to']}' was added",
            "impact": "Backward compatible addition"
        })

    # Modified nodes/edges - check if breaking
    for mod in node_deltas["modified"]:
        # Breaking if removed capabilities or changed incompatibly
        if "capabilities" in mod["changed_properties"]:
            breaking.append({
                "change_id": f"BC-MOD-{mod['node_id']}",
                "type": "modified_capabilities",
                "description": f"Node '{mod['node_id']}' capabilities changed",
                "impact": "May break dependents",
                "recommendation": "Review capability changes"
            })
        else:
            non_breaking.append({
                "change_id": f"NBC-MOD-{mod['node_id']}",
                "type": "modified_node",
                "description": f"Node '{mod['node_id']}' properties changed",
                "impact": "Minor change"
            })

    return {
        "breaking_changes": breaking,
        "non_breaking_changes": non_breaking
    }

def generate_recommendations(similarity: Dict, classification: Dict) -> List[str]:
    """Generate actionable recommendations"""
    recommendations = []
    overall = similarity["overall"]

    # Similarity-based recommendations
    if overall >= 0.8:
        recommendations.append(f"HIGH similarity ({overall:.1%}) - excellent alignment between architectures")
    elif overall >= 0.5:
        recommendations.append(f"MEDIUM similarity ({overall:.1%}) - some drift detected, review deltas")
    else:
        recommendations.append(f"LOW similarity ({overall:.1%}) - significant drift, investigate causes")

    # Breaking changes recommendations
    breaking_count = len(classification["breaking_changes"])
    if breaking_count > 0:
        recommendations.append(f"CRITICAL: {breaking_count} breaking changes detected - version increment required")
        recommendations.append("Review each breaking change and determine if design or implementation should change")
    else:
        recommendations.append("No breaking changes detected - architectures are compatible")

    # Actionable items
    if classification["non_breaking_changes"]:
        recommendations.append(f"{len(classification['non_breaking_changes'])} non-breaking additions - consider incorporating into as-designed architecture")

    return recommendations

def compare_architectures(from_path: Path, to_path: Path, output_path: Path):
    """Main comparison function"""

    print(f"=== Architecture Comparison v{VERSION} ===\n")
    print(f"Loading FROM: {from_path}")
    graph_a = load_json(from_path)
    from_type = graph_a.get('graph_metadata', {}).get('architecture_type', 'unknown')

    print(f"Loading TO: {to_path}")
    graph_b = load_json(to_path)
    to_type = graph_b.get('graph_metadata', {}).get('architecture_type', 'unknown')

    print("\nExtracting nodes and edges...")
    nodes_a = extract_nodes(graph_a)
    nodes_b = extract_nodes(graph_b)
    edges_a = extract_edges(graph_a)
    edges_b = extract_edges(graph_b)

    print(f"  FROM: {len(nodes_a)} nodes, {len(edges_a)} edges")
    print(f"  TO:   {len(nodes_b)} nodes, {len(edges_b)} edges")

    print("\nComputing deltas...")
    node_deltas = compute_node_deltas(nodes_a, nodes_b)
    edge_deltas = compute_edge_deltas(edges_a, edges_b)

    print(f"  Nodes: +{len(node_deltas['added'])} / -{len(node_deltas['removed'])} / ~{len(node_deltas['modified'])}")
    print(f"  Edges: +{len(edge_deltas['added'])} / -{len(edge_deltas['removed'])} / ~{len(edge_deltas['modified'])}")

    print("\nCalculating similarity...")
    similarity = calculate_similarity(nodes_a, nodes_b, edges_a, edges_b)
    print(f"  Overall: {similarity['overall']:.1%}")
    print(f"  Nodes:   {similarity['breakdown']['nodes']:.1%}")
    print(f"  Edges:   {similarity['breakdown']['edges']:.1%}")
    print(f"  Props:   {similarity['breakdown']['properties']:.1%}")

    print("\nClassifying changes...")
    classification = classify_changes(node_deltas, edge_deltas)
    print(f"  Breaking: {len(classification['breaking_changes'])}")
    print(f"  Non-breaking: {len(classification['non_breaking_changes'])}")

    print("\nGenerating recommendations...")
    recommendations = generate_recommendations(similarity, classification)
    for rec in recommendations:
        print(f"  - {rec}")

    # Build delta report
    delta_report = {
        "delta_metadata": {
            "report_id": f"DELTA-{datetime.now().strftime('%Y%m%d')}-{from_type}-{to_type}",
            "comparison_date": datetime.now().strftime("%Y-%m-%d"),
            "from_architecture": {
                "file_path": str(from_path),
                "architecture_type": from_type,
                "generation_date": graph_a.get('graph_metadata', {}).get('generation_date', 'unknown')
            },
            "to_architecture": {
                "file_path": str(to_path),
                "architecture_type": to_type,
                "generation_date": graph_b.get('graph_metadata', {}).get('generation_date', 'unknown')
            },
            "comparison_tool": f"compare_architectures.py v{VERSION}"
        },
        "similarity_score": {
            **similarity,
            "interpretation": "HIGH" if similarity["overall"] >= 0.8 else "MEDIUM" if similarity["overall"] >= 0.5 else "LOW"
        },
        "node_deltas": node_deltas,
        "edge_deltas": edge_deltas,
        "change_classification": classification,
        "recommendations": recommendations
    }

    print(f"\nSaving delta report to {output_path}")
    save_json(delta_report, output_path)
    print("\n=== Comparison Complete ===\n")

def main():
    parser = argparse.ArgumentParser(description="Compare two architecture graphs and generate delta report")
    parser.add_argument('--from', dest='from_graph', required=True, help="Path to FROM architecture graph (e.g., as-designed)")
    parser.add_argument('--to', dest='to_graph', required=True, help="Path to TO architecture graph (e.g., as-built, as-fielded)")
    parser.add_argument('--output', required=True, help="Path to output delta report JSON")

    args = parser.parse_args()

    from_path = Path(args.from_graph)
    to_path = Path(args.to_graph)
    output_path = Path(args.output)

    if not from_path.exists():
        print(f"ERROR: FROM graph not found: {from_path}")
        return 1

    if not to_path.exists():
        print(f"ERROR: TO graph not found: {to_path}")
        return 1

    compare_architectures(from_path, to_path, output_path)
    return 0

if __name__ == "__main__":
    exit(main())
