#!/usr/bin/env python3
"""
Safely swap one component for another in system architecture.

Checks interface compatibility, updates index.json, generates compatibility report.

Usage:
    python3 component_swap.py --index specs/machine/index.json \\
        --remove apache_proxy --add haproxy_proxy --dry-run

    python3 component_swap.py --index specs/machine/index.json \\
        --remove apache_proxy --add haproxy_proxy --validate
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import sys


def load_service_architecture(arch_path: Path) -> dict:
    """Load service architecture."""
    with open(arch_path, 'r') as f:
        return json.load(f)


def check_interface_compatibility(old_arch: dict, new_arch: dict) -> tuple[bool, list]:
    """Check if new component provides compatible interfaces."""
    issues = []

    old_provided = old_arch.get('interfaces', {}).get('provided_interfaces', [])
    new_provided = new_arch.get('interfaces', {}).get('provided_interfaces', [])

    old_ids = {i['interface_id'] for i in old_provided}
    new_ids = {i['interface_id'] for i in new_provided}

    # Check for missing interfaces
    missing = old_ids - new_ids
    if missing:
        issues.append({
            'severity': 'ERROR',
            'message': f"New component missing interfaces: {', '.join(missing)}"
        })

    # Check for protocol compatibility
    for old_ifc in old_provided:
        old_id = old_ifc['interface_id']
        new_ifc = next((i for i in new_provided if i['interface_id'] == old_id), None)

        if new_ifc:
            # Protocol check
            if old_ifc.get('protocol') != new_ifc.get('protocol'):
                issues.append({
                    'severity': 'WARNING',
                    'message': f"Protocol mismatch on {old_id}: {old_ifc.get('protocol')} vs {new_ifc.get('protocol')}"
                })

            # Data format check
            if old_ifc.get('data_format') != new_ifc.get('data_format'):
                issues.append({
                    'severity': 'WARNING',
                    'message': f"Data format mismatch on {old_id}: {old_ifc.get('data_format')} vs {new_ifc.get('data_format')}"
                })

    # Check for additional interfaces (informational)
    added = new_ids - old_ids
    if added:
        issues.append({
            'severity': 'INFO',
            'message': f"New component provides additional interfaces: {', '.join(added)}"
        })

    compatible = not any(i['severity'] == 'ERROR' for i in issues)
    return compatible, issues


def update_index(index_path: Path, old_service: str, new_service: str, dry_run: bool = False) -> bool:
    """Update index.json to reference new service."""
    with open(index_path, 'r') as f:
        index = json.load(f)

    components = index.get('components', {})

    if old_service not in components:
        print(f"❌ Service {old_service} not found in index")
        return False

    old_path = components[old_service]
    new_path = old_path.replace(old_service, new_service)

    if not dry_run:
        components[new_service] = new_path
        del components[old_service]

        with open(index_path, 'w') as f:
            json.dump(index, f, indent=2)

        print(f"✅ Updated index: {old_service} → {new_service}")
    else:
        print(f"[DRY-RUN] Would update index: {old_service} → {new_service}")
        print(f"  Old path: {old_path}")
        print(f"  New path: {new_path}")

    return True


def generate_report(old_service: str, new_service: str, compatible: bool, issues: list, output_path: Path):
    """Generate component swap compatibility report."""

    report = f"""# Component Swap Report

**Old Component**: {old_service}
**New Component**: {new_service}
**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Compatibility Summary

"""

    if compatible:
        report += "✅ **Status**: COMPATIBLE - Swap can proceed\n\n"
    else:
        report += "❌ **Status**: INCOMPATIBLE - Swap blocked\n\n"

    report += "## Issues\n\n"

    if not issues:
        report += "No issues detected. Components are fully compatible.\n"
    else:
        # Group by severity
        errors = [i for i in issues if i['severity'] == 'ERROR']
        warnings = [i for i in issues if i['severity'] == 'WARNING']
        infos = [i for i in issues if i['severity'] == 'INFO']

        if errors:
            report += "### Errors (Blocking)\n\n"
            for issue in errors:
                report += f"❌ {issue['message']}\n\n"

        if warnings:
            report += "### Warnings (Review Required)\n\n"
            for issue in warnings:
                report += f"⚠️  {issue['message']}\n\n"

        if infos:
            report += "### Informational\n\n"
            for issue in infos:
                report += f"ℹ️  {issue['message']}\n\n"

    report += """---

## Next Steps

"""

    if compatible:
        report += """- Review warnings and ensure compatibility
- Run validation: `--validate` flag
- Update dependent services if needed
- Test integration after swap
"""
    else:
        report += """- Address ERROR-level issues
- Update new component to provide missing interfaces
- Re-run compatibility check
- Consider alternative component
"""

    with open(output_path, 'w') as f:
        f.write(report)

    print(f"📄 Report: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Component swap tool with interface compatibility checking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check compatibility (dry-run)
  python3 component_swap.py --index specs/machine/index.json \\
      --remove apache_proxy --add haproxy_proxy --dry-run

  # Perform swap with validation
  python3 component_swap.py --index specs/machine/index.json \\
      --remove apache_proxy --add haproxy_proxy --validate
        """
    )
    parser.add_argument('--index', required=True, help='Path to index.json')
    parser.add_argument('--remove', required=True, help='Old service ID to remove')
    parser.add_argument('--add', required=True, help='New service ID to add')
    parser.add_argument('--validate', action='store_true', help='Run validation after swap')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')
    args = parser.parse_args()

    index_path = Path(args.index)
    system_root = index_path.parent.parent

    if not index_path.exists():
        print(f"❌ Index file not found: {index_path}")
        return 1

    # Load architectures
    old_arch_path = system_root / 'specs/machine/service_arch' / args.remove / 'service_architecture.json'
    new_arch_path = system_root / 'specs/machine/service_arch' / args.add / 'service_architecture.json'

    if not old_arch_path.exists():
        print(f"❌ Old service architecture not found: {old_arch_path}")
        return 1

    if not new_arch_path.exists():
        print(f"❌ New service architecture not found: {new_arch_path}")
        return 1

    old_arch = load_service_architecture(old_arch_path)
    new_arch = load_service_architecture(new_arch_path)

    # Check compatibility
    compatible, issues = check_interface_compatibility(old_arch, new_arch)

    print(f"\n{'='*60}")
    print(f"🔍 Compatibility Check: {args.remove} → {args.add}")
    print(f"{'='*60}\n")

    if issues:
        for issue in issues:
            icon = "❌" if issue['severity'] == 'ERROR' else ("⚠️ " if issue['severity'] == 'WARNING' else "ℹ️ ")
            print(f"{icon} {issue['severity']}: {issue['message']}")
    else:
        print("✅ No issues detected")

    print()

    if not compatible:
        print("❌ Components are INCOMPATIBLE - swap cannot proceed")
        print("   Address ERROR-level issues before attempting swap\n")

        # Generate report even on failure
        report_path = system_root / 'context' / f"component_swap_{args.remove}_to_{args.add}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        generate_report(args.remove, args.add, compatible, issues, report_path)

        return 1

    print("✅ Components are COMPATIBLE\n")

    # Update index
    success = update_index(index_path, args.remove, args.add, args.dry_run)

    if not success:
        return 1

    # Generate report
    report_path = system_root / 'context' / f"component_swap_{args.remove}_to_{args.add}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    generate_report(args.remove, args.add, compatible, issues, report_path)

    if args.validate and not args.dry_run:
        print("\n🔍 Running validation...")
        import subprocess

        # Find tools directory
        tools_path = system_root.parent / 'tools' if (system_root.parent / 'tools').exists() else Path('tools')

        result = subprocess.run([
            'python3', str(tools_path / 'system_of_systems_graph_v2.py'),
            str(index_path),
            '--detect-gaps'
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Validation PASSED - swap successful")
        else:
            print("❌ Validation FAILED - rolling back swap")
            print(result.stderr)

            # Rollback
            print("\n🔄 Rolling back changes...")
            update_index(index_path, args.add, args.remove, dry_run=False)
            print("✅ Rollback complete")

            return 1

    print(f"\n{'='*60}")
    if args.dry_run:
        print("[DRY-RUN] No changes were made")
    else:
        print("✅ Component swap complete")
    print(f"{'='*60}\n")

    return 0


if __name__ == '__main__':
    sys.exit(main())
