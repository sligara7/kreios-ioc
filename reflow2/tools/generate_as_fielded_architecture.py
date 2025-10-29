#!/usr/bin/env python3
"""
Generate As-Fielded Architecture Tool - PRODUCTION VERSION
Captures architecture from deployed/running system

Usage:
    python3 generate_as_fielded_architecture.py \
        --system-root /path/to/system \
        --output specs/machine/graphs/system_of_systems_graph_as_fielded.json \
        --compare-to specs/machine/graphs/system_of_systems_graph.json \
        --environment production
"""

import json
import argparse
import subprocess
import yaml
from pathlib import Path
from typing import Dict, List, Any, Set, Optional, Tuple
from datetime import datetime
from collections import defaultdict

VERSION = "1.0.0"

class DockerComposeAnalyzer:
    """Analyzes docker-compose.yml for service definitions"""

    def __init__(self, compose_file: Path):
        self.compose_file = compose_file
        self.services = {}

    def analyze(self) -> Dict[str, Any]:
        """Parse docker-compose.yml"""
        if not self.compose_file.exists():
            print(f"Warning: docker-compose.yml not found at {self.compose_file}")
            return {}

        try:
            with open(self.compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)

            services = compose_data.get('services', {})

            for svc_name, svc_config in services.items():
                self.services[svc_name] = {
                    'service_id': svc_name,
                    'image': svc_config.get('image', 'unknown'),
                    'ports': self._extract_ports(svc_config.get('ports', [])),
                    'environment': svc_config.get('environment', {}),
                    'volumes': svc_config.get('volumes', []),
                    'networks': svc_config.get('networks', []),
                    'depends_on': svc_config.get('depends_on', []),
                    'deploy': svc_config.get('deploy', {})
                }

            return self.services

        except yaml.YAMLError as e:
            print(f"Error parsing docker-compose.yml: {e}")
            return {}
        except Exception as e:
            print(f"Unexpected error parsing docker-compose.yml: {e}")
            return {}

    def _extract_ports(self, ports_config: List) -> List[Dict[str, Any]]:
        """Extract port mappings"""
        ports = []
        for port in ports_config:
            if isinstance(port, str):
                # Format: "host:container" or "container"
                parts = port.split(':')
                if len(parts) == 2:
                    ports.append({
                        'host_port': int(parts[0]),
                        'container_port': int(parts[1]),
                        'protocol': 'tcp'
                    })
                elif len(parts) == 1:
                    ports.append({
                        'host_port': int(parts[0]),
                        'container_port': int(parts[0]),
                        'protocol': 'tcp'
                    })
            elif isinstance(port, dict):
                ports.append({
                    'host_port': port.get('published'),
                    'container_port': port.get('target'),
                    'protocol': port.get('protocol', 'tcp')
                })
        return ports


class DockerRuntimeAnalyzer:
    """Analyzes running Docker containers"""

    def __init__(self):
        self.containers = []

    def analyze(self) -> List[Dict[str, Any]]:
        """Inspect running containers"""
        try:
            # Check if docker is available
            result = subprocess.run(['docker', 'ps', '--format', 'json'],
                                    capture_output=True, text=True, check=True)

            if result.stdout.strip():
                # Docker ps --format json outputs one JSON per line
                for line in result.stdout.strip().split('\n'):
                    if line:
                        container = json.loads(line)
                        container_id = container.get('ID')
                        if container_id:
                            detailed = self._inspect_container(container_id)
                            if detailed:
                                self.containers.append(detailed)

            return self.containers

        except subprocess.CalledProcessError:
            print("Warning: Could not run 'docker ps'. Docker may not be running or not installed.")
            return []
        except FileNotFoundError:
            print("Warning: Docker command not found. Skipping runtime inspection.")
            return []
        except Exception as e:
            print(f"Warning: Error analyzing Docker runtime: {e}")
            return []

    def _inspect_container(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Inspect detailed container information"""
        try:
            result = subprocess.run(['docker', 'inspect', container_id],
                                    capture_output=True, text=True, check=True)

            inspect_data = json.loads(result.stdout)
            if not inspect_data:
                return None

            container = inspect_data[0]

            # Extract relevant information
            config = container.get('Config', {})
            network_settings = container.get('NetworkSettings', {})
            state = container.get('State', {})

            return {
                'container_id': container_id,
                'name': container.get('Name', '').lstrip('/'),
                'image': config.get('Image'),
                'state': state.get('Status'),
                'health': state.get('Health', {}).get('Status'),
                'ports': self._extract_port_bindings(network_settings.get('Ports', {})),
                'networks': list(network_settings.get('Networks', {}).keys()),
                'ip_addresses': {net: info.get('IPAddress') for net, info in
                                 network_settings.get('Networks', {}).items()},
                'environment': config.get('Env', []),
                'labels': config.get('Labels', {}),
                'resource_limits': {
                    'cpu': container.get('HostConfig', {}).get('NanoCpus'),
                    'memory': container.get('HostConfig', {}).get('Memory')
                }
            }

        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not inspect container {container_id}: {e}")
            return None
        except Exception as e:
            print(f"Warning: Error inspecting container {container_id}: {e}")
            return None

    def _extract_port_bindings(self, ports: Dict) -> List[Dict[str, Any]]:
        """Extract port bindings from Docker inspect output"""
        port_list = []
        for container_port, bindings in ports.items():
            if bindings:
                for binding in bindings:
                    port_list.append({
                        'container_port': int(container_port.split('/')[0]),
                        'host_port': int(binding.get('HostPort', 0)) if binding.get('HostPort') else None,
                        'host_ip': binding.get('HostIp', '0.0.0.0'),
                        'protocol': container_port.split('/')[1] if '/' in container_port else 'tcp'
                    })
        return port_list


class HealthCheckAnalyzer:
    """Checks health endpoints of running services"""

    def __init__(self, containers: List[Dict[str, Any]]):
        self.containers = containers
        self.health_status = {}

    def analyze(self) -> Dict[str, Any]:
        """Check health endpoints"""
        import urllib.request
        import urllib.error

        for container in self.containers:
            svc_name = container['name']
            ports = container.get('ports', [])

            health_endpoints = ['/health', '/ready', '/healthz']
            status = 'unknown'

            for port_info in ports:
                host_port = port_info.get('host_port')
                if not host_port:
                    continue

                for endpoint in health_endpoints:
                    url = f"http://localhost:{host_port}{endpoint}"
                    try:
                        with urllib.request.urlopen(url, timeout=2) as response:
                            if response.status == 200:
                                status = 'healthy'
                                break
                    except urllib.error.URLError:
                        pass
                    except Exception:
                        pass

                if status == 'healthy':
                    break

            # Fallback to Docker health check
            if status == 'unknown':
                status = container.get('health', 'unknown')

            self.health_status[svc_name] = {
                'status': status,
                'checked_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        return self.health_status


class NetworkTopologyAnalyzer:
    """Analyzes network connections between containers"""

    def __init__(self, containers: List[Dict[str, Any]]):
        self.containers = containers
        self.connections = []

    def analyze(self) -> List[Dict[str, Any]]:
        """Infer connections from network topology"""

        # Build network membership map
        network_members = defaultdict(list)
        for container in self.containers:
            for network in container.get('networks', []):
                network_members[network].append(container['name'])

        # Infer potential connections within same network
        for network, members in network_members.items():
            if len(members) < 2:
                continue

            # All services in same network can potentially communicate
            for i, svc_a in enumerate(members):
                for svc_b in members[i + 1:]:
                    self.connections.append({
                        'from_service': svc_a,
                        'to_service': svc_b,
                        'network': network,
                        'bidirectional': True,
                        'confidence': 'low',  # Just because they're in same network doesn't mean they communicate
                        'detected_from': 'network_topology'
                    })

        # Check depends_on from docker-compose (if available)
        # This would require passing compose data here, skipping for now

        return self.connections


def merge_compose_and_runtime(compose_services: Dict, runtime_containers: List[Dict]) -> List[Dict]:
    """Merge static compose definitions with runtime data"""

    merged = []

    # Create lookup by service name
    runtime_by_name = {c['name']: c for c in runtime_containers}

    # Merge each compose service with runtime data
    for svc_id, svc_config in compose_services.items():
        # Find matching runtime container
        runtime = runtime_by_name.get(svc_id)

        merged_svc = {
            'service_id': svc_id,
            'service_name': svc_id.replace('_', ' ').title(),
            'source': 'deployed_system',

            # From compose
            'image': svc_config.get('image'),
            'configured_ports': svc_config.get('ports', []),
            'environment_vars': svc_config.get('environment', {}),
            'networks': svc_config.get('networks', []),
            'dependencies': svc_config.get('depends_on', []),

            # From runtime (if available)
            'runtime_status': runtime.get('state') if runtime else 'not_running',
            'health_status': runtime.get('health') if runtime else 'unknown',
            'actual_ports': runtime.get('ports', []) if runtime else [],
            'ip_addresses': runtime.get('ip_addresses', {}) if runtime else {},
            'resource_usage': runtime.get('resource_limits', {}) if runtime else {}
        }

        merged.append(merged_svc)

    # Add any runtime containers not in compose (manually started containers)
    for runtime in runtime_containers:
        if runtime['name'] not in compose_services:
            merged.append({
                'service_id': runtime['name'],
                'service_name': runtime['name'].replace('_', ' ').title(),
                'source': 'runtime_only',
                'image': runtime.get('image'),
                'runtime_status': runtime.get('state'),
                'health_status': runtime.get('health'),
                'actual_ports': runtime.get('ports', []),
                'ip_addresses': runtime.get('ip_addresses', {}),
                'networks': runtime.get('networks', [])
            })

    return merged


def build_as_fielded_graph(system_root: Path, merged_services: List[Dict],
                          connections: List[Dict], health_status: Dict,
                          environment: str) -> Dict[str, Any]:
    """Build system-of-systems graph from fielded system"""

    # Build nodes
    nodes = []
    for svc in merged_services:
        node = {
            "id": svc['service_id'],
            "node_type": "deployed_service",
            "name": svc['service_name'],
            "deployment_status": svc.get('runtime_status', 'unknown'),
            "health_status": health_status.get(svc['service_id'], {}).get('status', 'unknown'),
            "image": svc.get('image'),
            "ports": svc.get('actual_ports') or svc.get('configured_ports', []),
            "networks": svc.get('networks', []),
            "ip_addresses": svc.get('ip_addresses', {}),
            "environment": environment,
            "source": svc.get('source', 'deployed_system')
        }

        # Add capabilities if ports are exposed
        capabilities = []
        for port in node['ports']:
            if isinstance(port, dict):
                capabilities.append(f"HTTP service on port {port.get('host_port') or port.get('container_port')}")
            else:
                capabilities.append(f"HTTP service on port {port}")

        node['capabilities'] = capabilities[:5]  # Top 5
        nodes.append(node)

    # Build edges from connections
    edges = []
    for conn in connections:
        edge = {
            "id": f"{conn['from_service']}_to_{conn['to_service']}",
            "from": conn['from_service'],
            "to": conn['to_service'],
            "edge_type": "runtime_connection",
            "network": conn.get('network'),
            "confidence": conn.get('confidence', 'medium'),
            "detected_from": conn.get('detected_from')
        }
        edges.append(edge)

    # Build graph
    graph = {
        "graph_metadata": {
            "graph_id": f"system_of_systems_as_fielded_{datetime.now().strftime('%Y%m%d')}",
            "architecture_type": "as_fielded",
            "deployment_date": datetime.now().strftime("%Y-%m-%d"),
            "inspection_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "environment": environment,
            "source": "runtime_inspection",
            "tool": f"generate_as_fielded_architecture.py v{VERSION}",
            "system_root": str(system_root),
            "total_services": len(nodes),
            "total_connections": len(edges),
            "health_summary": {
                "healthy": sum(1 for n in nodes if n['health_status'] == 'healthy'),
                "unhealthy": sum(1 for n in nodes if n['health_status'] in ['unhealthy', 'unknown']),
                "not_running": sum(1 for n in nodes if n['deployment_status'] != 'running')
            }
        },
        "nodes": nodes,
        "edges": edges,
        "analysis_notes": {
            "detection_method": "Docker runtime inspection + docker-compose analysis",
            "confidence_level": "high",
            "limitations": [
                "Connections inferred from network topology (actual traffic not monitored)",
                "Health checks may timeout if services are slow to respond",
                "Resource usage reflects limits, not actual consumption"
            ],
            "recommendations": [
                "Compare to as-designed and as-built architectures",
                "Monitor actual network traffic for accurate connection map",
                "Use observability tools (Prometheus, Jaeger) for complete operational picture"
            ]
        }
    }

    return graph


def compare_to_designed(as_fielded_path: Path, as_designed_path: Path, output_dir: Path):
    """Compare as-fielded to as-designed architecture"""
    if not as_designed_path.exists():
        print(f"\nWarning: As-designed architecture not found at {as_designed_path}")
        print("Skipping comparison")
        return

    print(f"\nComparing as-fielded to as-designed...")

    # Call compare_architectures.py
    delta_output = output_dir / f"architecture_delta_as_fielded_{datetime.now().strftime('%Y%m%d')}.json"

    import subprocess
    import sys

    compare_tool = Path(__file__).parent / "compare_architectures.py"

    try:
        result = subprocess.run([
            sys.executable,
            str(compare_tool),
            "--from", str(as_designed_path),
            "--to", str(as_fielded_path),
            "--output", str(delta_output)
        ], capture_output=True, text=True, check=True)

        print(result.stdout)
        print(f"\nDelta report saved to: {delta_output}")

    except subprocess.CalledProcessError as e:
        print(f"Error running comparison tool: {e}")
        print(e.stdout)
        print(e.stderr)
    except FileNotFoundError:
        print(f"Comparison tool not found at {compare_tool}")


def generate_as_fielded_architecture(system_root: Path, output_path: Path,
                                    compare_to: Optional[Path] = None,
                                    environment: str = "production"):
    """Main function to generate as-fielded architecture"""

    print(f"=== As-Fielded Architecture Generation v{VERSION} ===\n")
    print(f"System Root: {system_root}")
    print(f"Environment: {environment}")
    print(f"Output: {output_path}\n")

    # Analyze docker-compose.yml
    print("Analyzing docker-compose.yml...")
    compose_file = system_root / "docker-compose.yml"
    compose_analyzer = DockerComposeAnalyzer(compose_file)
    compose_services = compose_analyzer.analyze()
    print(f"  Found {len(compose_services)} services in docker-compose.yml\n")

    # Analyze running containers
    print("Inspecting running Docker containers...")
    runtime_analyzer = DockerRuntimeAnalyzer()
    runtime_containers = runtime_analyzer.analyze()
    print(f"  Found {len(runtime_containers)} running containers\n")

    # Check health endpoints
    print("Checking health endpoints...")
    health_analyzer = HealthCheckAnalyzer(runtime_containers)
    health_status = health_analyzer.analyze()
    print(f"  Checked {len(health_status)} services")
    healthy = sum(1 for h in health_status.values() if h['status'] == 'healthy')
    print(f"  Healthy: {healthy}/{len(health_status)}\n")

    # Analyze network topology
    print("Analyzing network topology...")
    network_analyzer = NetworkTopologyAnalyzer(runtime_containers)
    connections = network_analyzer.analyze()
    print(f"  Detected {len(connections)} potential connections\n")

    # Merge static and runtime data
    print("Merging compose definitions with runtime data...")
    merged_services = merge_compose_and_runtime(compose_services, runtime_containers)
    print(f"  Merged {len(merged_services)} services\n")

    # Build graph
    print("Building as-fielded graph...")
    graph = build_as_fielded_graph(system_root, merged_services, connections,
                                   health_status, environment)

    # Save graph
    print(f"Saving as-fielded graph to {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(graph, f, indent=2)

    print(f"\n=== Inspection Complete ===")
    print(f"Services inspected: {len(merged_services)}")
    print(f"Connections detected: {len(connections)}")
    print(f"Health status:")
    print(f"  Healthy: {graph['graph_metadata']['health_summary']['healthy']}")
    print(f"  Unhealthy: {graph['graph_metadata']['health_summary']['unhealthy']}")
    print(f"  Not running: {graph['graph_metadata']['health_summary']['not_running']}")
    print(f"Output: {output_path}\n")

    # Compare to as-designed if requested
    if compare_to:
        compare_to_designed(output_path, compare_to, output_path.parent)

    return 0


def main():
    parser = argparse.ArgumentParser(description="Generate as-fielded architecture from deployed system")
    parser.add_argument('--system-root', required=True, help="Path to system root directory")
    parser.add_argument('--output', required=True, help="Path to output as-fielded graph JSON")
    parser.add_argument('--compare-to', help="Path to as-designed graph for comparison (optional)")
    parser.add_argument('--environment', default='production',
                       help="Environment name (dev/staging/production)")

    args = parser.parse_args()

    system_root = Path(args.system_root)
    output_path = Path(args.output)
    compare_to = Path(args.compare_to) if args.compare_to else None

    if not system_root.exists():
        print(f"ERROR: System root not found: {system_root}")
        return 1

    # Make output path absolute if relative
    if not output_path.is_absolute():
        output_path = system_root / output_path

    # Make compare_to path absolute if relative
    if compare_to and not compare_to.is_absolute():
        compare_to = system_root / compare_to

    return generate_as_fielded_architecture(system_root, output_path, compare_to, args.environment)


if __name__ == "__main__":
    exit(main())
