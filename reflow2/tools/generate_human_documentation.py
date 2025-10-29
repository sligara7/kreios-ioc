#!/usr/bin/env python3
"""
Generate human-readable documentation from machine-readable service architectures.

Usage:
    python3 generate_human_documentation.py --system-root /path/to/system
    python3 generate_human_documentation.py --system-root /path/to/system --output-dir /custom/path
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import sys


def load_service_architecture(arch_path: Path) -> dict:
    """Load service architecture JSON."""
    with open(arch_path, 'r') as f:
        return json.load(f)


def generate_human_doc(service_arch: dict) -> str:
    """Generate human-readable markdown from service architecture."""

    # Extract metadata
    service_id = service_arch.get('service_id', 'unknown')
    service_name = service_arch.get('service_name', 'Unknown Service')
    version = service_arch.get('version', '1.0.0')
    description = service_arch.get('description', 'No description')
    framework = service_arch.get('framework', 'uaf')

    # Extract interfaces
    interfaces = service_arch.get('interfaces', {})
    provided = interfaces.get('provided_interfaces', [])
    required = interfaces.get('required_interfaces', [])

    # Extract deployment
    deployment = service_arch.get('deployment', {})
    container = deployment.get('container_name', 'N/A')
    ports = deployment.get('ports', {})

    # Extract dependencies
    dependencies = service_arch.get('dependencies', {})
    services_consumed = dependencies.get('services_consumed', [])

    # Generate markdown
    doc = f"""---
service_id: {service_id}
version: {version}
last_updated: {datetime.now().strftime('%Y-%m-%d')}
framework: {framework}
---

# {service_name}

## Overview

{description}

**Service ID**: `{service_id}`
**Version**: {version}
**Type**: {service_arch.get('service_type', 'service')}
**Framework**: {framework}

## Provides

"""

    if provided:
        for ifc in provided:
            ifc_name = ifc.get('interface_name', 'Unnamed')
            ifc_id = ifc.get('interface_id', 'unknown')
            doc += f"### {ifc_name} (`{ifc_id}`)\n\n"
            doc += f"- **Protocol**: {ifc.get('protocol', 'N/A')}\n"
            doc += f"- **Data Format**: {ifc.get('data_format', 'N/A')}\n"

            if 'port' in ifc:
                doc += f"- **Port**: {ifc.get('port')}\n"

            if 'description' in ifc:
                doc += f"- **Description**: {ifc.get('description')}\n"

            doc += "\n"
    else:
        doc += "No interfaces provided.\n\n"

    doc += "## Requires\n\n"

    if required:
        for ifc in required:
            ifc_name = ifc.get('interface_name', ifc.get('interface_id', 'Unnamed'))
            ifc_id = ifc.get('interface_id', 'unknown')
            doc += f"### {ifc_name} (`{ifc_id}`)\n\n"

            if 'provider_service_id' in ifc:
                doc += f"- **Provider**: {ifc.get('provider_service_id')}\n"

            doc += f"- **Criticality**: {ifc.get('criticality', 'medium')}\n\n"
    else:
        doc += "No external interfaces required.\n\n"

    doc += "## Dependencies\n\n"

    if services_consumed:
        for dep in services_consumed:
            dep_id = dep.get('service_id', 'unknown') if isinstance(dep, dict) else str(dep)
            dep_type = dep.get('dependency_type', 'unknown') if isinstance(dep, dict) else 'dependency'
            doc += f"- **{dep_id}**: {dep_type}\n"
    else:
        doc += "No service dependencies.\n"

    doc += "\n## Deployment\n\n"
    doc += f"- **Container**: `{container}`\n"

    if ports:
        primary = ports.get('primary', {})
        if primary:
            doc += f"- **Port**: {primary.get('port', 'N/A')} ({primary.get('protocol', 'N/A')})\n"
            doc += f"- **Exposure**: {primary.get('exposure', 'internal')}\n"

    health_checks = deployment.get('health_checks', {})
    if health_checks:
        endpoint = health_checks.get('endpoint', '/health')
        status = health_checks.get('expected_status', 200)
        doc += f"- **Health Check**: `{endpoint}` → {status}\n"

    doc += "\n## Configuration\n\n"

    env_vars = deployment.get('environment_variables', [])
    if env_vars:
        for var in env_vars:
            var_name = var.get('name', 'UNKNOWN')
            var_desc = var.get('description', 'No description')
            doc += f"- `{var_name}`: {var_desc}\n"
    else:
        doc += "No environment variables configured.\n"

    doc += f"""

## Version History

- **{version}** ({datetime.now().strftime('%Y-%m-%d')}): Current version

---

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Machine Spec**: `specs/machine/service_arch/{service_id}/service_architecture.json`
"""

    return doc


def main():
    parser = argparse.ArgumentParser(
        description='Generate human-readable documentation from machine-readable service architectures',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate docs for all services
  python3 generate_human_documentation.py --system-root /path/to/system

  # Custom output directory
  python3 generate_human_documentation.py --system-root /path/to/system --output-dir /custom/path
        """
    )
    parser.add_argument('--system-root', required=True, help='System root directory')
    parser.add_argument('--output-dir', help='Output directory (default: specs/human/documentation/services)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()

    system_root = Path(args.system_root)
    if not system_root.exists():
        print(f"❌ System root does not exist: {system_root}")
        return 1

    output_dir = Path(args.output_dir) if args.output_dir else system_root / 'specs/human/documentation/services'
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.verbose:
        print(f"System Root: {system_root}")
        print(f"Output Dir: {output_dir}")

    # Find all service architectures
    arch_dir = system_root / 'specs/machine/service_arch'
    if not arch_dir.exists():
        print(f"❌ No service architectures found at {arch_dir}")
        return 1

    count = 0
    errors = 0

    for service_dir in sorted(arch_dir.iterdir()):
        if not service_dir.is_dir():
            continue

        # Find symlink (current version)
        arch_file = service_dir / 'service_architecture.json'
        if not arch_file.exists():
            if args.verbose:
                print(f"⚠️  Skipping {service_dir.name}: No service_architecture.json")
            continue

        try:
            # Load and generate
            service_arch = load_service_architecture(arch_file)
            human_doc = generate_human_doc(service_arch)

            # Write to output
            service_id = service_arch.get('service_id', service_dir.name)
            output_file = output_dir / f"{service_id}.md"

            with open(output_file, 'w') as f:
                f.write(human_doc)

            print(f"✅ Generated: {output_file.relative_to(system_root)}")
            count += 1

        except Exception as e:
            print(f"❌ Error processing {service_dir.name}: {e}")
            errors += 1
            if args.verbose:
                import traceback
                traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"✅ Generated {count} human documentation files")
    if errors > 0:
        print(f"❌ {errors} errors encountered")
    print(f"📁 Output: {output_dir}")

    return 0 if errors == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
