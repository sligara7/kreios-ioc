#!/usr/bin/env python3
"""
Port Registry Validator

Validates port_registry.json for conflicts and compliance with port allocation rules.
Prevents the common "Address already in use" deployment errors by catching port
conflicts during architecture phase.

Usage:
    python3 validate_port_registry.py <system_root>/specs/machine/port_registry.json
    python3 validate_port_registry.py <system_root> (auto-locates port_registry.json)

Author: Reflow v3.1+
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set
from collections import defaultdict

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import sanitize_path, validate_system_root, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError


class PortRegistryValidator:
    def __init__(self, port_registry_path: Path):
        """
        Initialize validator with pre-validated port registry path.

        Args:
            port_registry_path: Pre-validated Path object
        """
        self.port_registry_path = port_registry_path
        self.port_registry = None
        self.errors = []
        self.warnings = []
        self.info_messages = []

    def load_registry(self) -> bool:
        """Load and parse port_registry.json"""
        try:
            self.port_registry = safe_load_json(
                self.port_registry_path,
                file_type_description="port registry"
            )
            return True
        except FileNotFoundError as e:
            self.errors.append(str(e))
            return False
        except JSONValidationError as e:
            self.errors.append(str(e))
            return False

    def validate(self) -> Tuple[bool, Dict]:
        """Run all validation checks"""
        if not self.load_registry():
            return False, self._build_report()

        # Run validation checks
        self._check_duplicate_ports()
        self._check_port_ranges()
        self._check_privileged_ports()
        self._check_port_overlap()
        self._check_docker_mapping_consistency()
        self._check_required_fields()
        self._check_well_known_port_conflicts()

        # Determine overall pass/fail
        passed = len(self.errors) == 0
        return passed, self._build_report()

    def _check_duplicate_ports(self):
        """PC-01: No duplicate primary ports across services"""
        if 'service_ports' not in self.port_registry:
            self.warnings.append("No service_ports section found in registry")
            return

        port_to_services = defaultdict(list)

        for service_id, service_data in self.port_registry.get('service_ports', {}).items():
            if service_id == "EXAMPLE_SERVICE_ID":  # Skip template example
                continue

            ports = service_data.get('ports', {})
            primary_port_info = ports.get('primary', {})
            primary_port = primary_port_info.get('port')

            if primary_port:
                port_to_services[primary_port].append({
                    'service_id': service_id,
                    'service_name': service_data.get('service_name', service_id),
                    'port_type': 'primary'
                })

        # Check for duplicates
        for port, services in port_to_services.items():
            if len(services) > 1:
                service_names = ', '.join([s['service_name'] for s in services])
                self.errors.append(
                    f"PC-01 VIOLATION: Port {port} assigned to multiple services: {service_names}"
                )

    def _check_port_overlap(self):
        """PC-02: No port overlap between any service ports (primary, metrics, admin)"""
        all_ports = defaultdict(list)

        for service_id, service_data in self.port_registry.get('service_ports', {}).items():
            if service_id == "EXAMPLE_SERVICE_ID":
                continue

            service_name = service_data.get('service_name', service_id)
            ports = service_data.get('ports', {})

            for port_type, port_info in ports.items():
                port = port_info.get('port')
                if port and isinstance(port, int):
                    all_ports[port].append({
                        'service_id': service_id,
                        'service_name': service_name,
                        'port_type': port_type
                    })

        # Check for ANY port conflicts (across primary, metrics, admin, etc.)
        for port, assignments in all_ports.items():
            if len(assignments) > 1:
                conflict_desc = ', '.join([
                    f"{a['service_name']} ({a['port_type']})" for a in assignments
                ])
                self.errors.append(
                    f"PC-02 VIOLATION: Port {port} conflict: {conflict_desc}"
                )

    def _check_port_ranges(self):
        """PC-03: Services should use ports within designated ranges"""
        port_ranges = self.port_registry.get('port_ranges', {})

        range_mapping = {}
        for category, info in port_ranges.items():
            if isinstance(info, dict) and 'range' in info:
                range_str = info['range']
                if '-' in range_str:
                    start, end = map(int, range_str.split('-'))
                    range_mapping[category] = (start, end)

        for service_id, service_data in self.port_registry.get('service_ports', {}).items():
            if service_id == "EXAMPLE_SERVICE_ID":
                continue

            classification = service_data.get('classification', '').replace('_services', '')
            ports = service_data.get('ports', {})
            primary_port = ports.get('primary', {}).get('port')

            if classification in range_mapping and primary_port:
                start, end = range_mapping[classification]
                if not (start <= primary_port <= end):
                    self.warnings.append(
                        f"PC-03: Service '{service_data.get('service_name')}' port {primary_port} "
                        f"outside recommended range {start}-{end} for {classification} services"
                    )

    def _check_privileged_ports(self):
        """PC-04: Avoid well-known ports below 1024"""
        for service_id, service_data in self.port_registry.get('service_ports', {}).items():
            if service_id == "EXAMPLE_SERVICE_ID":
                continue

            ports = service_data.get('ports', {})
            for port_type, port_info in ports.items():
                port = port_info.get('port')
                if port and isinstance(port, int) and port < 1024:
                    self.warnings.append(
                        f"PC-04: Service '{service_data.get('service_name')}' uses privileged port {port} ({port_type}). "
                        f"This requires root privileges and may conflict with system services."
                    )

    def _check_docker_mapping_consistency(self):
        """PC-05: Docker host-container port mappings should typically match"""
        for service_id, service_data in self.port_registry.get('service_ports', {}).items():
            if service_id == "EXAMPLE_SERVICE_ID":
                continue

            ports = service_data.get('ports', {})
            primary_port = ports.get('primary', {}).get('port')
            docker_mapping = ports.get('primary', {}).get('docker_mapping', {})

            host_port = docker_mapping.get('host_port')
            container_port = docker_mapping.get('container_port')

            if host_port and container_port:
                if host_port != container_port:
                    self.info_messages.append(
                        f"PC-05: Service '{service_data.get('service_name')}' has different host ({host_port}) "
                        f"and container ({container_port}) ports. This is valid but can be confusing."
                    )
                if primary_port and primary_port != container_port:
                    self.warnings.append(
                        f"Service '{service_data.get('service_name')}' primary port ({primary_port}) "
                        f"doesn't match container port ({container_port}) in docker_mapping"
                    )

    def _check_required_fields(self):
        """Check that all services have required port fields"""
        for service_id, service_data in self.port_registry.get('service_ports', {}).items():
            if service_id == "EXAMPLE_SERVICE_ID":
                continue

            service_name = service_data.get('service_name', service_id)

            # Check for ports section
            if 'ports' not in service_data:
                self.errors.append(f"Service '{service_name}' missing 'ports' section")
                continue

            ports = service_data.get('ports', {})

            # Check for primary port
            if 'primary' not in ports:
                self.errors.append(f"Service '{service_name}' missing 'primary' port definition")
                continue

            primary = ports['primary']
            required_primary_fields = ['port', 'protocol', 'purpose']
            for field in required_primary_fields:
                if field not in primary or not primary[field]:
                    self.errors.append(
                        f"Service '{service_name}' primary port missing required field: '{field}'"
                    )

    def _check_well_known_port_conflicts(self):
        """Warn about conflicts with common well-known ports"""
        well_known_ports = {
            22: "SSH",
            80: "HTTP",
            443: "HTTPS",
            3306: "MySQL",
            5432: "PostgreSQL",
            27017: "MongoDB",
            6379: "Redis",
            9200: "Elasticsearch",
            9090: "Prometheus",
            3000: "Grafana/Node.js dev server"
        }

        used_ports = set()
        for service_id, service_data in self.port_registry.get('service_ports', {}).items():
            if service_id == "EXAMPLE_SERVICE_ID":
                continue

            ports = service_data.get('ports', {})
            for port_type, port_info in ports.items():
                port = port_info.get('port')
                if port:
                    used_ports.add(port)

        for port in used_ports:
            if port in well_known_ports:
                service_name = well_known_ports[port]
                self.info_messages.append(
                    f"Port {port} is commonly used by {service_name}. "
                    f"Ensure no conflict if {service_name} is also running."
                )

    def _build_report(self) -> Dict:
        """Build validation report"""
        return {
            'passed': len(self.errors) == 0,
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'total_info': len(self.info_messages),
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info_messages,
            'port_registry_path': self.port_registry_path
        }

    def print_report(self, report: Dict):
        """Pretty print validation report"""
        print("\n" + "="*70)
        print("PORT REGISTRY VALIDATION REPORT")
        print("="*70)
        print(f"Registry: {report['port_registry_path']}")
        print(f"Status: {'✓ PASSED' if report['passed'] else '✗ FAILED'}")
        print(f"Errors: {report['total_errors']}, Warnings: {report['total_warnings']}, Info: {report['total_info']}")
        print("="*70)

        if report['errors']:
            print("\n❌ ERRORS (must fix):")
            for i, error in enumerate(report['errors'], 1):
                print(f"  {i}. {error}")

        if report['warnings']:
            print("\n⚠️  WARNINGS (should fix):")
            for i, warning in enumerate(report['warnings'], 1):
                print(f"  {i}. {warning}")

        if report['info']:
            print("\nℹ️  INFORMATION:")
            for i, info in enumerate(report['info'], 1):
                print(f"  {i}. {info}")

        if report['passed']:
            print("\n✓ Port registry validation passed! No port conflicts detected.")
        else:
            print(f"\n✗ Port registry validation failed with {report['total_errors']} error(s).")
            print("   Fix errors before deploying services.")
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_port_registry.py <port_registry.json>")
        print("   or: python3 validate_port_registry.py <system_root>")
        sys.exit(1)

    input_path_str = sys.argv[1]

    # Security: Validate and determine port_registry.json path (v3.4.0 fix - SV-01)
    try:
        input_path = Path(input_path_str).resolve()

        if input_path.is_file():
            # Direct file path provided - validate it
            # Get system_root (parent of specs/machine)
            if input_path.name == "port_registry.json" and input_path.parent.name == "machine":
                system_root = input_path.parent.parent.parent
                system_root = validate_system_root(system_root)
                port_registry_path = sanitize_path(
                    "specs/machine/port_registry.json",
                    system_root,
                    must_exist=True
                )
            else:
                print(f"Error: File must be port_registry.json in specs/machine/ directory")
                sys.exit(1)

        elif input_path.is_dir():
            # Directory provided - assume it's system_root
            system_root = validate_system_root(input_path)
            port_registry_path = sanitize_path(
                "specs/machine/port_registry.json",
                system_root,
                must_exist=True
            )

        else:
            print(f"Error: {input_path_str} is not a file or directory")
            sys.exit(1)

    except PathSecurityError as e:
        print(f"ERROR: Path security violation: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e}")
        sys.exit(1)

    # Run validation
    validator = PortRegistryValidator(port_registry_path)
    passed, report = validator.validate()
    validator.print_report(report)

    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
