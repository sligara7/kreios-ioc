#!/usr/bin/env python3
"""
Workflow Complexity Analyzer
Analyzes Reflow workflow files for size, complexity, and refactoring opportunities
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

def analyze_workflow(workflow_path):
    """Analyze a single workflow file"""
    with open(workflow_path) as f:
        workflow = json.load(f)

    workflow_id = workflow['workflow_metadata']['workflow_id']
    steps = workflow['workflow_steps']

    # Calculate basic metrics
    num_steps = len(steps)
    file_size = workflow_path.stat().st_size
    line_count = len(workflow_path.read_text().split('\n'))

    # Calculate average lines per step
    avg_lines_per_step = line_count / num_steps if num_steps > 0 else 0

    # Count actions across all steps
    total_actions = sum(len(step.get('actions', [])) for step in steps)
    avg_actions_per_step = total_actions / num_steps if num_steps > 0 else 0

    # Analyze step dependencies (in-degree)
    step_ids = {step['step_id'] for step in steps}
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)

    for step in steps:
        step_id = step['step_id']
        next_step = step.get('next_step')

        if next_step and next_step in step_ids:
            in_degree[next_step] += 1
            out_degree[step_id] += 1

    # Find bottleneck steps (high in-degree)
    bottlenecks = [(sid, deg) for sid, deg in in_degree.items() if deg > 2]

    # Analyze phases
    phases = defaultdict(list)
    for step in steps:
        phase = step.get('phase', 'unknown')
        phases[phase].append(step['step_id'])

    return {
        'workflow_id': workflow_id,
        'file_path': str(workflow_path.name),
        'num_steps': num_steps,
        'line_count': line_count,
        'file_size_kb': file_size / 1024,
        'avg_lines_per_step': round(avg_lines_per_step, 1),
        'total_actions': total_actions,
        'avg_actions_per_step': round(avg_actions_per_step, 1),
        'num_phases': len(phases),
        'phases': dict(phases),
        'bottlenecks': bottlenecks,
        'max_in_degree': max(in_degree.values()) if in_degree else 0,
        'steps': [{'step_id': s['step_id'], 'phase': s.get('phase', 'unknown')} for s in steps]
    }

def calculate_complexity_score(metrics):
    """Calculate complexity score (higher = more complex)"""
    score = 0

    # Size factors
    score += metrics['num_steps'] * 2  # 2 points per step
    score += metrics['line_count'] / 100  # 1 point per 100 lines
    score += metrics['total_actions']  # 1 point per action

    # Complexity factors
    score += metrics['max_in_degree'] * 5  # High in-degree is problematic
    score += metrics['num_phases'] * 3  # More phases = more complexity

    # Context usage factor (most important!)
    context_factor = metrics['line_count'] / 1000
    score += context_factor * 20  # Heavy penalty for large files

    return round(score, 1)

def identify_refactoring_opportunities(metrics):
    """Identify potential refactoring opportunities"""
    opportunities = []

    # Check for large workflows
    if metrics['line_count'] > 1000:
        opportunities.append({
            'type': 'SIZE',
            'severity': 'HIGH',
            'description': f"Large workflow ({metrics['line_count']} lines) consuming significant LLM context",
            'recommendation': 'Consider splitting into multiple workflows by phase'
        })

    # Check for many steps
    if metrics['num_steps'] > 10:
        opportunities.append({
            'type': 'STEPS',
            'severity': 'MEDIUM',
            'description': f"Many steps ({metrics['num_steps']}) may indicate monolithic design",
            'recommendation': 'Review if steps can be grouped into separate workflows'
        })

    # Check for bottlenecks
    if metrics['bottlenecks']:
        for step_id, degree in metrics['bottlenecks']:
            opportunities.append({
                'type': 'BOTTLENECK',
                'severity': 'MEDIUM',
                'description': f"Step {step_id} has high in-degree ({degree}) - potential bottleneck",
                'recommendation': 'Consider simplifying dependencies or splitting step'
            })

    # Check for multiple phases (natural split point)
    if metrics['num_phases'] > 3:
        opportunities.append({
            'type': 'PHASES',
            'severity': 'LOW',
            'description': f"Multiple phases ({metrics['num_phases']}) suggest natural boundaries",
            'recommendation': f"Consider splitting by phase: {', '.join(metrics['phases'].keys())}"
        })

    # Check average lines per step
    if metrics['avg_lines_per_step'] > 150:
        opportunities.append({
            'type': 'STEP_SIZE',
            'severity': 'LOW',
            'description': f"High average lines per step ({metrics['avg_lines_per_step']})",
            'recommendation': 'Individual steps may be too detailed - consider simplification'
        })

    return opportunities

def main():
    workflows_dir = Path('/home/user/reflow/workflows')

    print("=" * 80)
    print("REFLOW WORKFLOW COMPLEXITY ANALYSIS")
    print("=" * 80)
    print()

    all_metrics = []

    # Analyze each workflow
    for workflow_file in sorted(workflows_dir.glob('*.json')):
        print(f"Analyzing: {workflow_file.name}")
        print("-" * 80)

        metrics = analyze_workflow(workflow_file)
        complexity = calculate_complexity_score(metrics)
        metrics['complexity_score'] = complexity
        all_metrics.append(metrics)

        # Print metrics
        print(f"  Steps: {metrics['num_steps']}")
        print(f"  Lines: {metrics['line_count']}")
        print(f"  Size: {metrics['file_size_kb']:.1f} KB")
        print(f"  Avg lines/step: {metrics['avg_lines_per_step']}")
        print(f"  Total actions: {metrics['total_actions']}")
        print(f"  Phases: {metrics['num_phases']} ({', '.join(metrics['phases'].keys())})")
        print(f"  Max in-degree: {metrics['max_in_degree']}")
        print(f"  Complexity score: {complexity}")

        # Identify refactoring opportunities
        opportunities = identify_refactoring_opportunities(metrics)
        if opportunities:
            print(f"  ⚠️  Refactoring opportunities: {len(opportunities)}")
            for opp in opportunities:
                severity_icon = "🔴" if opp['severity'] == 'HIGH' else "🟡" if opp['severity'] == 'MEDIUM' else "🟢"
                print(f"     {severity_icon} [{opp['type']}] {opp['description']}")
        else:
            print(f"  ✅ No refactoring needed")

        print()

    # Summary
    print("=" * 80)
    print("SUMMARY - Workflows by Complexity")
    print("=" * 80)
    print()

    sorted_metrics = sorted(all_metrics, key=lambda x: x['complexity_score'], reverse=True)

    print(f"{'Workflow':<40} {'Steps':>6} {'Lines':>6} {'Score':>8} {'Status'}")
    print("-" * 80)

    for m in sorted_metrics:
        status = "🔴 HIGH" if m['complexity_score'] > 80 else "🟡 MEDIUM" if m['complexity_score'] > 40 else "✅ OK"
        print(f"{m['workflow_id']:<40} {m['num_steps']:>6} {m['line_count']:>6} {m['complexity_score']:>8.1f} {status}")

    print()
    print("=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    print()

    # Generate overall recommendations
    high_complexity = [m for m in all_metrics if m['complexity_score'] > 80]

    if high_complexity:
        print("🔴 HIGH PRIORITY: The following workflows should be refactored:")
        print()
        for m in sorted(high_complexity, key=lambda x: x['complexity_score'], reverse=True):
            print(f"  {m['workflow_id']} (score: {m['complexity_score']})")
            opportunities = identify_refactoring_opportunities(m)
            for opp in opportunities:
                if opp['severity'] in ['HIGH', 'MEDIUM']:
                    print(f"    • {opp['recommendation']}")
            print()

    # Context usage analysis
    print("📊 LLM CONTEXT USAGE ANALYSIS:")
    print()
    total_lines = sum(m['line_count'] for m in all_metrics)
    print(f"  Total workflow lines: {total_lines}")
    print(f"  Estimated tokens (×0.3): ~{int(total_lines * 0.3)}")
    print()

    large_workflows = [m for m in all_metrics if m['line_count'] > 1000]
    if large_workflows:
        print(f"  ⚠️  {len(large_workflows)} workflow(s) exceed 1000 lines:")
        for m in sorted(large_workflows, key=lambda x: x['line_count'], reverse=True):
            pct = (m['line_count'] / total_lines) * 100
            print(f"    • {m['workflow_id']}: {m['line_count']} lines ({pct:.1f}% of total)")

    print()

if __name__ == '__main__':
    main()
