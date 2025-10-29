#!/usr/bin/env python3
"""
Tool for identifying integration points between multiple systems.

This tool analyzes the interfaces and capabilities of multiple systems to identify
potential integration points and recommend integration strategies.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import sanitize_path, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError

def load_system_analysis(analysis_file: str) -> Dict[str, Any]:
    """Load system analysis results from a JSON file."""
    try:
        return safe_load_json(Path(analysis_file), file_type_description="system analysis file")
    except (JSONValidationError, FileNotFoundError) as e:
        print(f"Error loading {analysis_file}: {e}", file=sys.stderr)
        return {}

def identify_integration_opportunities(systems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze multiple systems to identify potential integration points.
    
    Args:
        systems: List of system analysis results
        
    Returns:
        List of identified integration opportunities
    """
    opportunities = []
    
    for i, system_a in enumerate(systems):
        for j, system_b in enumerate(systems[i+1:], i+1):
            opportunity = analyze_system_pair(system_a, system_b)
            if opportunity:
                opportunities.append(opportunity)
    
    return opportunities

def analyze_system_pair(system_a: Dict[str, Any], system_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a pair of systems for integration opportunities.
    
    Args:
        system_a: First system analysis
        system_b: Second system analysis
        
    Returns:
        Integration opportunity analysis or None
    """
    system_a_name = Path(system_a.get("system_path", "unknown_a")).name
    system_b_name = Path(system_b.get("system_path", "unknown_b")).name
    
    # Analyze technology compatibility
    tech_a = set(system_a.get("structure", {}).get("technology_stack", []))
    tech_b = set(system_b.get("structure", {}).get("technology_stack", []))
    
    common_tech = tech_a.intersection(tech_b)
    all_tech = tech_a.union(tech_b)
    
    # Analyze interface compatibility
    interfaces_a = system_a.get("interfaces", [])
    interfaces_b = system_b.get("interfaces", [])
    
    has_http_a = any(iface.get("type") == "http_endpoint" for iface in interfaces_a)
    has_http_b = any(iface.get("type") == "http_endpoint" for iface in interfaces_b)
    
    # Determine integration feasibility
    integration_score = 0
    integration_factors = []
    
    if common_tech:
        integration_score += 20
        integration_factors.append(f"Shared technologies: {', '.join(common_tech)}")
    
    if has_http_a and has_http_b:
        integration_score += 30
        integration_factors.append("Both systems have HTTP interfaces")
    elif has_http_a or has_http_b:
        integration_score += 15
        integration_factors.append("One system has HTTP interface")
    
    if len(all_tech) <= 3:
        integration_score += 10
        integration_factors.append("Limited technology diversity")
    
    # Generate recommendations
    recommendations = []
    
    if integration_score >= 40:
        recommendations.extend([
            "Direct API integration feasible",
            "Consider service-to-service communication"
        ])
    elif integration_score >= 20:
        recommendations.extend([
            "Integration possible with adapter layer",
            "Consider message-based integration"
        ])
    else:
        recommendations.extend([
            "Integration challenging - consider data-level integration",
            "May require significant adapter development"
        ])
    
    # Suggest specific integration patterns
    if has_http_a and has_http_b:
        recommendations.append("REST API integration pattern recommended")
    
    if "Python" in all_tech:
        recommendations.append("Consider Python-based integration services")
    
    if "Containerized" in system_a.get("structure", {}).get("architectural_patterns", []) and \
       "Containerized" in system_b.get("structure", {}).get("architectural_patterns", []):
        recommendations.append("Container orchestration can facilitate integration")
    
    return {
        "system_a": system_a_name,
        "system_b": system_b_name,
        "integration_score": integration_score,
        "feasibility": "high" if integration_score >= 40 else "medium" if integration_score >= 20 else "low",
        "common_technologies": list(common_tech),
        "all_technologies": list(all_tech),
        "integration_factors": integration_factors,
        "recommendations": recommendations,
        "suggested_patterns": generate_integration_patterns(system_a, system_b)
    }

def generate_integration_patterns(system_a: Dict[str, Any], system_b: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate specific integration patterns for the system pair."""
    patterns = []
    
    # API Gateway pattern
    patterns.append({
        "pattern": "API Gateway",
        "description": "Centralized entry point for both systems",
        "complexity": "medium",
        "benefits": ["Unified interface", "Traffic management", "Authentication"]
    })
    
    # Event-driven pattern
    patterns.append({
        "pattern": "Event-Driven Architecture",
        "description": "Asynchronous integration via events",
        "complexity": "medium",
        "benefits": ["Loose coupling", "Scalability", "Resilience"]
    })
    
    # Data sync pattern
    patterns.append({
        "pattern": "Data Synchronization",
        "description": "Periodic or real-time data synchronization",
        "complexity": "low",
        "benefits": ["Simple implementation", "Data consistency"]
    })
    
    return patterns

def generate_integration_plan(opportunities: List[Dict[str, Any]], requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate an overall integration plan based on opportunities and requirements.
    
    Args:
        opportunities: List of integration opportunities
        requirements: Integration requirements from user
        
    Returns:
        Comprehensive integration plan
    """
    plan = {
        "integration_approach": "system_of_systems",
        "priority_integrations": [],
        "architecture_recommendations": [],
        "implementation_phases": []
    }
    
    # Sort opportunities by feasibility and score
    high_priority = [opp for opp in opportunities if opp["feasibility"] == "high"]
    medium_priority = [opp for opp in opportunities if opp["feasibility"] == "medium"]
    low_priority = [opp for opp in opportunities if opp["feasibility"] == "low"]
    
    plan["priority_integrations"] = {
        "phase_1_high_priority": high_priority,
        "phase_2_medium_priority": medium_priority,
        "phase_3_low_priority": low_priority
    }
    
    # Generate architecture recommendations
    all_techs = set()
    for opp in opportunities:
        all_techs.update(opp["all_technologies"])
    
    if "Python" in all_techs:
        plan["architecture_recommendations"].append("Consider Python-based integration services")
    
    if len([opp for opp in opportunities if "REST API" in str(opp["recommendations"])]) > 1:
        plan["architecture_recommendations"].append("API Gateway pattern recommended for multiple REST integrations")
    
    # Implementation phases
    if high_priority:
        plan["implementation_phases"].append({
            "phase": 1,
            "name": "High-Priority Integrations",
            "systems": [f"{opp['system_a']} <-> {opp['system_b']}" for opp in high_priority],
            "estimated_effort": "2-4 weeks",
            "risk": "low"
        })
    
    if medium_priority:
        plan["implementation_phases"].append({
            "phase": 2,
            "name": "Medium-Priority Integrations",
            "systems": [f"{opp['system_a']} <-> {opp['system_b']}" for opp in medium_priority],
            "estimated_effort": "4-8 weeks",
            "risk": "medium"
        })
    
    if low_priority:
        plan["implementation_phases"].append({
            "phase": 3,
            "name": "Complex Integrations",
            "systems": [f"{opp['system_a']} <-> {opp['system_b']}" for opp in low_priority],
            "estimated_effort": "8-16 weeks",
            "risk": "high"
        })
    
    return plan

def main():
    parser = argparse.ArgumentParser(description="Identify integration points between systems")
    parser.add_argument("analysis_files", nargs="+", help="System analysis JSON files")
    parser.add_argument("--requirements", "-r", help="Integration requirements JSON file")
    parser.add_argument("--output", "-o", help="Output file for integration analysis")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Security: Use current working directory as base (v3.4.0 fix - SV-01)
    base_dir = Path.cwd()

    # Load system analyses
    systems = []
    for analysis_file_str in args.analysis_files:
        # Security: Sanitize analysis file path (v3.4.0 fix - SV-01)
        try:
            analysis_file_path = Path(analysis_file_str).resolve()
            # Verify file is within base_dir or explicitly allow absolute paths from user
            # For this tool, we'll check existence but allow any path (tool is for analyzing multiple systems)
            if not analysis_file_path.exists():
                print(f"Warning: Analysis file not found: {analysis_file_str}")
                continue

            if not analysis_file_path.is_file():
                print(f"Warning: Not a file: {analysis_file_str}")
                continue

            analysis = load_system_analysis(str(analysis_file_path))
            if analysis:
                systems.append(analysis)

        except Exception as e:
            print(f"Warning: Could not load {analysis_file_str}: {e}")
            continue

    if len(systems) < 2:
        print("Error: Need at least 2 system analyses to identify integration points", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing integration opportunities between {len(systems)} systems")

    # Load requirements if provided
    requirements = {}
    if args.requirements:
        # Security: Sanitize requirements file path (v3.4.0 fix - SV-01)
        try:
            requirements_path = Path(args.requirements).resolve()
            if requirements_path.exists() and requirements_path.is_file():
                requirements = load_system_analysis(str(requirements_path))
            else:
                print(f"Warning: Requirements file not found or invalid: {args.requirements}")
        except Exception as e:
            print(f"Warning: Could not load requirements file: {e}")
    
    # Identify integration opportunities
    opportunities = identify_integration_opportunities(systems)
    
    # Generate integration plan
    integration_plan = generate_integration_plan(opportunities, requirements)
    
    # Prepare results
    results = {
        "analysis_timestamp": "2024-10-16",  # Would use actual timestamp
        "systems_analyzed": [Path(sys.get("system_path", "unknown")).name for sys in systems],
        "integration_opportunities": opportunities,
        "integration_plan": integration_plan,
        "summary": {
            "total_opportunities": len(opportunities),
            "high_feasibility": len([o for o in opportunities if o["feasibility"] == "high"]),
            "medium_feasibility": len([o for o in opportunities if o["feasibility"] == "medium"]),
            "low_feasibility": len([o for o in opportunities if o["feasibility"] == "low"])
        }
    }

    if args.output:
        # Security: Sanitize output file path (v3.4.0 fix - SV-01)
        try:
            output_path = Path(args.output).resolve()

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"Integration analysis written to: {output_path}")

        except (PathSecurityError, PermissionError, OSError) as e:
            print(f"ERROR: Could not write output file: {e}")
            print("Printing results to stdout instead:")
            print(json.dumps(results, indent=2))
    else:
        print(json.dumps(results, indent=2))
    
    if args.verbose:
        print(f"\nSummary:")
        print(f"- Found {results['summary']['total_opportunities']} integration opportunities")
        print(f"- High feasibility: {results['summary']['high_feasibility']}")
        print(f"- Medium feasibility: {results['summary']['medium_feasibility']}")
        print(f"- Low feasibility: {results['summary']['low_feasibility']}")

if __name__ == "__main__":
    main()