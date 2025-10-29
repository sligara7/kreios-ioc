#!/usr/bin/env python3
"""
Parse human-readable documentation back to machine-readable service architectures.

Usage:
    python3 parse_human_documentation.py --system-root /path/to/system
    python3 parse_human_documentation.py --system-root /path/to/system --validate
    python3 parse_human_documentation.py --system-root /path/to/system --dry-run
"""

import json
import argparse
import re
from pathlib import Path
from datetime import datetime
import sys

try:
    import yaml
except ImportError:
    print("⚠️  Warning: PyYAML not installed. Install with: pip install pyyaml")
    print("Attempting to parse frontmatter without YAML library...")
    yaml = None


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown."""
    if not content.startswith('---'):
        return {}, content

    parts = content.split('---', 2)
    if len(parts) < 3:
        return {}, content

    try:
        if yaml:
            frontmatter = yaml.safe_load(parts[1])
        else:
            # Fallback: simple key-value parsing
            frontmatter = {}
            for line in parts[1].strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
        body = parts[2].strip()
        return frontmatter, body
    except Exception as e:
        print(f"⚠️  Warning: Could not parse frontmatter: {e}")
        return {}, content


def parse_section(body: str, section_name: str) -> str:
    """Extract section content from markdown."""
    pattern = f'## {section_name}\\n(.+?)(?=\\n## |$)'
    match = re.search(pattern, body, re.DOTALL)
    return match.group(1).strip() if match else ''


def parse_interfaces(section: str, interface_type: str) -> list:
    """Parse interface definitions from markdown section."""
    interfaces = []

    # Find all ### headers (interface names)
    pattern = r'### (.+?) \(`(.+?)`\)\n(.+?)(?=\n### |\Z)'
    matches = re.finditer(pattern, section, re.DOTALL)

    for match in matches:
        name = match.group(1).strip()
        ifc_id = match.group(2).strip()
        content = match.group(3).strip()

        # Parse bullet points
        protocol = re.search(r'\*\*Protocol\*\*: (.+)', content)
        data_format = re.search(r'\*\*Data Format\*\*: (.+)', content)
        port = re.search(r'\*\*Port\*\*: (.+)', content)
        description = re.search(r'\*\*Description\*\*: (.+)', content)
        provider = re.search(r'\*\*Provider\*\*: (.+)', content)
        criticality = re.search(r'\*\*Criticality\*\*: (.+)', content)

        ifc = {
            'interface_id': ifc_id,
            'interface_name': name,
        }

        if protocol:
            ifc['protocol'] = protocol.group(1).strip()
        if data_format:
            ifc['data_format'] = data_format.group(1).strip()
        if port:
            try:
                ifc['port'] = int(port.group(1).strip())
            except ValueError:
                ifc['port'] = port.group(1).strip()
        if description:
            ifc['description'] = description.group(1).strip()
        if provider:
            ifc['provider_service_id'] = provider.group(1).strip()
        if criticality:
            ifc['criticality'] = criticality.group(1).strip()

        interfaces.append(ifc)

    return interfaces


def parse_human_doc(md_content: str) -> dict:
    """Parse human documentation to service architecture dict."""

    frontmatter, body = parse_frontmatter(md_content)

    # Extract sections
    overview = parse_section(body, 'Overview')
    provides = parse_section(body, 'Provides')
    requires = parse_section(body, 'Requires')
    dependencies = parse_section(body, 'Dependencies')
    deployment = parse_section(body, 'Deployment')
    configuration = parse_section(body, 'Configuration')

    # Extract service name from first H1
    service_name_match = re.search(r'^# (.+?)$', body, re.MULTILINE)
    service_name = service_name_match.group(1).strip() if service_name_match else 'Unknown Service'

    # Extract description (first paragraph after Overview)
    description = overview.split('\n')[0] if overview else 'No description'

    # Build service architecture
    service_arch = {
        'service_id': frontmatter.get('service_id', 'unknown'),
        'service_name': service_name,
        'version': frontmatter.get('version', '1.0.0'),
        'framework': frontmatter.get('framework', 'uaf'),
        'description': description,
        'service_type': 'service',
        'interfaces': {
            'provided_interfaces': parse_interfaces(provides, 'provided'),
            'required_interfaces': parse_interfaces(requires, 'required')
        },
        'deployment': {},
        'dependencies': {}
    }

    # Parse deployment section
    container_match = re.search(r'\*\*Container\*\*: `(.+?)`', deployment)
    if container_match:
        service_arch['deployment']['container_name'] = container_match.group(1)

    port_match = re.search(r'\*\*Port\*\*: (\d+) \((.+?)\)', deployment)
    if port_match:
        service_arch['deployment']['ports'] = {
            'primary': {
                'port': int(port_match.group(1)),
                'protocol': port_match.group(2)
            }
        }

    health_check_match = re.search(r'\*\*Health Check\*\*: `(.+?)` → (\d+)', deployment)
    if health_check_match:
        service_arch['deployment']['health_checks'] = {
            'endpoint': health_check_match.group(1),
            'expected_status': int(health_check_match.group(2))
        }

    # Parse configuration (environment variables)
    env_vars = []
    env_pattern = r'- `(.+?)`: (.+)'
    for match in re.finditer(env_pattern, configuration):
        env_vars.append({
            'name': match.group(1).strip(),
            'description': match.group(2).strip()
        })
    if env_vars:
        service_arch['deployment']['environment_variables'] = env_vars

    return service_arch


def detect_changes(old_arch: dict, new_arch: dict) -> list:
    """Detect changes between old and new architecture."""
    changes = []

    # Compare service name
    if old_arch.get('service_name') != new_arch.get('service_name'):
        changes.append({
            'type': 'service_name_changed',
            'old': old_arch.get('service_name'),
            'new': new_arch.get('service_name')
        })

    # Compare version
    if old_arch.get('version') != new_arch.get('version'):
        changes.append({
            'type': 'version_changed',
            'old': old_arch.get('version'),
            'new': new_arch.get('version')
        })

    # Compare interfaces
    old_provided = old_arch.get('interfaces', {}).get('provided_interfaces', [])
    new_provided = new_arch.get('interfaces', {}).get('provided_interfaces', [])

    old_ids = {i['interface_id'] for i in old_provided}
    new_ids = {i['interface_id'] for i in new_provided}

    added = new_ids - old_ids
    removed = old_ids - new_ids

    for ifc_id in added:
        changes.append({'type': 'interface_added', 'new': ifc_id})
    for ifc_id in removed:
        changes.append({'type': 'interface_removed', 'old': ifc_id})

    # Compare ports
    old_port = old_arch.get('deployment', {}).get('ports', {}).get('primary', {}).get('port')
    new_port = new_arch.get('deployment', {}).get('ports', {}).get('primary', {}).get('port')

    if old_port and new_port and old_port != new_port:
        changes.append({
            'type': 'port_changed',
            'old': old_port,
            'new': new_port
        })

    return changes


def main():
    parser = argparse.ArgumentParser(
        description='Parse human-readable documentation back to machine-readable service architectures',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse all human docs and show changes (dry-run)
  python3 parse_human_documentation.py --system-root /path/to/system --dry-run

  # Parse and update machine specs
  python3 parse_human_documentation.py --system-root /path/to/system

  # Parse, update, and validate
  python3 parse_human_documentation.py --system-root /path/to/system --validate
        """
    )
    parser.add_argument('--system-root', required=True, help='System root directory')
    parser.add_argument('--validate', action='store_true', help='Run validation after parsing')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without writing')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    system_root = Path(args.system_root)
    human_docs_dir = system_root / 'specs/human/documentation/services'
    machine_specs_dir = system_root / 'specs/machine/service_arch'

    if not human_docs_dir.exists():
        print(f"❌ No human documentation found at {human_docs_dir}")
        return 1

    changes_summary = []
    count = 0

    for human_doc in sorted(human_docs_dir.glob('*.md')):
        try:
            with open(human_doc, 'r') as f:
                md_content = f.read()

            # Parse
            new_arch = parse_human_doc(md_content)
            service_id = new_arch['service_id']

            # Load old architecture
            old_arch_file = machine_specs_dir / service_id / 'service_architecture.json'
            if old_arch_file.exists():
                with open(old_arch_file, 'r') as f:
                    old_arch = json.load(f)
            else:
                old_arch = {}

            # Detect changes
            changes = detect_changes(old_arch, new_arch)

            if changes:
                changes_summary.append({
                    'service_id': service_id,
                    'changes': changes
                })

                print(f"\n📝 {service_id}:")
                for change in changes:
                    old_val = change.get('old', '')
                    new_val = change.get('new', '')
                    if old_val and new_val:
                        print(f"  - {change['type']}: {old_val} → {new_val}")
                    else:
                        print(f"  - {change['type']}: {old_val}{new_val}")

                if not args.dry_run:
                    # Write new version
                    version = new_arch['version']
                    new_version_file = machine_specs_dir / service_id / f"service_architecture_v{version}-{datetime.now().strftime('%Y%m%d')}.json"
                    new_version_file.parent.mkdir(parents=True, exist_ok=True)

                    with open(new_version_file, 'w') as f:
                        json.dump(new_arch, f, indent=2)

                    # Update symlink
                    symlink = machine_specs_dir / service_id / 'service_architecture.json'
                    if symlink.exists() or symlink.is_symlink():
                        symlink.unlink()
                    symlink.symlink_to(new_version_file.name)

                    print(f"  ✅ Updated: {new_version_file.relative_to(system_root)}")
                    count += 1
            else:
                if args.verbose:
                    print(f"✓ {service_id}: No changes detected")

        except Exception as e:
            print(f"❌ Error processing {human_doc.name}: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    if args.validate and not args.dry_run:
        print("\n🔍 Running validation...")
        # Run system_of_systems_graph_v2.py validation
        import subprocess
        tools_path = system_root.parent / 'tools' if (system_root.parent / 'tools').exists() else Path('tools')
        index_path = system_root / 'specs/machine/index.json'

        if not index_path.exists():
            print(f"⚠️  Warning: index.json not found at {index_path}, skipping validation")
        else:
            result = subprocess.run([
                'python3', str(tools_path / 'system_of_systems_graph_v2.py'),
                str(index_path),
                '--detect-gaps'
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Validation PASSED")
            else:
                print("❌ Validation FAILED:")
                print(result.stderr)
                return 1

    print(f"\n{'='*60}")
    if args.dry_run:
        print(f"[DRY-RUN] Would update {len(changes_summary)} services")
    else:
        print(f"✅ Updated {count} services with changes")
    if changes_summary == [] and not args.dry_run:
        print("✓ No changes detected in any service")

    return 0


if __name__ == '__main__':
    sys.exit(main())
