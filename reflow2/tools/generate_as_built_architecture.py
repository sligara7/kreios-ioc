#!/usr/bin/env python3
"""
Generate As-Built Architecture Tool - PRODUCTION VERSION
Reverse-engineers architecture from implemented code

Usage:
    python3 generate_as_built_architecture.py \
        --system-root /path/to/system \
        --output specs/machine/graphs/system_of_systems_graph_as_built.json \
        --compare-to specs/machine/graphs/system_of_systems_graph.json
"""

import json
import ast
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Optional
from datetime import datetime
from collections import defaultdict

VERSION = "1.0.0"

class CodeAnalyzer:
    """Analyzes Python code to extract architectural information"""

    def __init__(self, service_path: Path):
        self.service_path = service_path
        self.service_name = service_path.name
        self.endpoints = []
        self.functions = []
        self.dependencies = set()
        self.database_connections = []
        self.message_queues = []

    def analyze(self) -> Dict[str, Any]:
        """Perform complete code analysis"""
        self._scan_python_files()
        self._parse_requirements()
        self._detect_databases()
        self._detect_message_queues()

        return {
            "service_id": self.service_name,
            "service_name": self.service_name.replace('_', ' ').title(),
            "endpoints": self.endpoints,
            "functions": self.functions,
            "dependencies": sorted(list(self.dependencies)),
            "database_connections": self.database_connections,
            "message_queues": self.message_queues
        }

    def _scan_python_files(self):
        """Scan all Python files in service directory"""
        src_dir = self.service_path / "src"
        if not src_dir.exists():
            return

        for py_file in src_dir.rglob("*.py"):
            if py_file.name.startswith('_') and py_file.name != '__init__.py':
                continue
            self._parse_python_file(py_file)

    def _parse_python_file(self, file_path: Path):
        """Parse Python file using AST"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.dependencies.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self.dependencies.add(node.module.split('.')[0])

            # Extract decorators (Flask/FastAPI routes)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self._extract_endpoint(node)
                    self._extract_function_signature(node)

        except SyntaxError:
            print(f"  Warning: Could not parse {file_path} (syntax error)")
        except Exception as e:
            print(f"  Warning: Error parsing {file_path}: {e}")

    def _extract_endpoint(self, func_node: ast.FunctionDef):
        """Extract REST endpoint from function decorators"""
        for decorator in func_node.decorator_list:
            # Handle Flask: @app.route('/path', methods=['GET'])
            if isinstance(decorator, ast.Call):
                if hasattr(decorator.func, 'attr') and decorator.func.attr == 'route':
                    path = self._extract_string_arg(decorator, 0)
                    methods = self._extract_methods(decorator)
                    if path:
                        self.endpoints.append({
                            "path": path,
                            "methods": methods or ["GET"],
                            "function": func_node.name,
                            "framework": "flask"
                        })

            # Handle FastAPI: @app.get('/path'), @app.post('/path')
            elif hasattr(decorator, 'attr') and decorator.attr in ['get', 'post', 'put', 'delete', 'patch']:
                if hasattr(decorator, 'value'):
                    # @app.get('/path')
                    method = decorator.attr.upper()
                    # Try to get path from subsequent call
                    for node in ast.walk(func_node):
                        if isinstance(node, ast.Str):
                            self.endpoints.append({
                                "path": node.s,
                                "methods": [method],
                                "function": func_node.name,
                                "framework": "fastapi"
                            })
                            break

    def _extract_string_arg(self, call_node: ast.Call, index: int) -> Optional[str]:
        """Extract string argument from function call"""
        if len(call_node.args) > index:
            arg = call_node.args[index]
            if isinstance(arg, ast.Str):
                return arg.s
            elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
        return None

    def _extract_methods(self, call_node: ast.Call) -> Optional[List[str]]:
        """Extract methods from route decorator"""
        for keyword in call_node.keywords:
            if keyword.arg == 'methods':
                if isinstance(keyword.value, ast.List):
                    methods = []
                    for elt in keyword.value.elts:
                        if isinstance(elt, ast.Str):
                            methods.append(elt.s)
                        elif isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            methods.append(elt.value)
                    return methods
        return None

    def _extract_function_signature(self, func_node: ast.FunctionDef):
        """Extract function signature"""
        # Skip private functions and decorators already counted as endpoints
        if func_node.name.startswith('_'):
            return

        # Build argument list
        args = []
        for arg in func_node.args.args:
            arg_name = arg.arg
            arg_type = None
            if arg.annotation:
                arg_type = ast.unparse(arg.annotation) if hasattr(ast, 'unparse') else 'Any'
            args.append({"name": arg_name, "type": arg_type or "Any"})

        # Get return type
        return_type = None
        if func_node.returns:
            return_type = ast.unparse(func_node.returns) if hasattr(ast, 'unparse') else 'Any'

        self.functions.append({
            "name": func_node.name,
            "arguments": args,
            "return_type": return_type or "Any",
            "line_number": func_node.lineno
        })

    def _parse_requirements(self):
        """Parse requirements.txt for dependencies"""
        req_file = self.service_path / "requirements.txt"
        if not req_file.exists():
            return

        try:
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name (before ==, >=, etc.)
                        pkg = re.split(r'[=<>!]', line)[0].strip()
                        self.dependencies.add(pkg)
        except Exception as e:
            print(f"  Warning: Could not parse requirements.txt: {e}")

    def _detect_databases(self):
        """Detect database connections from dependencies"""
        db_indicators = {
            'psycopg2': 'postgresql',
            'asyncpg': 'postgresql',
            'pymongo': 'mongodb',
            'motor': 'mongodb',
            'redis': 'redis',
            'mysql': 'mysql',
            'sqlalchemy': 'relational_db'
        }

        for dep in self.dependencies:
            dep_lower = dep.lower()
            for indicator, db_type in db_indicators.items():
                if indicator in dep_lower:
                    self.database_connections.append({
                        "type": db_type,
                        "driver": dep,
                        "detected_from": "dependencies"
                    })

    def _detect_message_queues(self):
        """Detect message queue usage from dependencies"""
        mq_indicators = {
            'pika': 'rabbitmq',
            'kombu': 'rabbitmq',
            'celery': 'rabbitmq_or_redis',
            'kafka-python': 'kafka',
            'aiokafka': 'kafka'
        }

        for dep in self.dependencies:
            dep_lower = dep.lower()
            for indicator, mq_type in mq_indicators.items():
                if indicator in dep_lower:
                    self.message_queues.append({
                        "type": mq_type,
                        "client": dep,
                        "detected_from": "dependencies"
                    })


def discover_services(system_root: Path) -> List[Path]:
    """Discover all service directories"""
    services_dir = system_root / "services"
    if not services_dir.exists():
        print(f"Warning: No services directory found at {services_dir}")
        return []

    services = []
    for item in services_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            # Verify it has source code
            src_dir = item / "src"
            if src_dir.exists() and any(src_dir.glob("*.py")):
                services.append(item)

    return services


def analyze_service(service_path: Path) -> Dict[str, Any]:
    """Analyze a single service"""
    analyzer = CodeAnalyzer(service_path)
    return analyzer.analyze()


def infer_interfaces(services_data: List[Dict]) -> List[Dict]:
    """Infer interfaces between services"""
    interfaces = []

    # Build service endpoint map
    service_endpoints = {}
    for svc in services_data:
        service_endpoints[svc['service_id']] = {
            'endpoints': svc['endpoints'],
            'dependencies': svc['dependencies']
        }

    # Detect API calls between services
    # Look for service names in dependencies or hardcoded URLs
    for svc in services_data:
        for other_svc in services_data:
            if svc['service_id'] == other_svc['service_id']:
                continue

            # Check if service name appears in dependencies (proxy for API calls)
            # This is heuristic-based
            if any(other_svc['service_id'] in str(dep) for dep in svc.get('dependencies', [])):
                interfaces.append({
                    "interface_id": f"{svc['service_id']}_to_{other_svc['service_id']}",
                    "from_service": svc['service_id'],
                    "to_service": other_svc['service_id'],
                    "interface_type": "rest_api",
                    "detected_from": "code_analysis",
                    "confidence": "medium"
                })

    return interfaces


def build_as_built_graph(system_root: Path, services_data: List[Dict], interfaces: List[Dict]) -> Dict[str, Any]:
    """Build system-of-systems graph from analyzed code"""

    # Build nodes
    nodes = []
    for svc in services_data:
        node = {
            "id": svc['service_id'],
            "node_type": "service",
            "name": svc['service_name'],
            "endpoints": svc['endpoints'],
            "capabilities": [f"{ep['methods'][0]} {ep['path']}" for ep in svc['endpoints'][:5]],  # Top 5
            "dependencies": svc['dependencies'],
            "database_connections": svc['database_connections'],
            "message_queues": svc['message_queues'],
            "source": "code_analysis"
        }
        nodes.append(node)

    # Build edges
    edges = []
    for iface in interfaces:
        edge = {
            "id": iface['interface_id'],
            "from": iface['from_service'],
            "to": iface['to_service'],
            "edge_type": "interface",
            "interface_type": iface['interface_type'],
            "confidence": iface['confidence']
        }
        edges.append(edge)

    # Build graph
    graph = {
        "graph_metadata": {
            "graph_id": f"system_of_systems_as_built_{datetime.now().strftime('%Y%m%d')}",
            "architecture_type": "as_built",
            "generation_date": datetime.now().strftime("%Y-%m-%d"),
            "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "code_analysis",
            "tool": f"generate_as_built_architecture.py v{VERSION}",
            "system_root": str(system_root),
            "total_services": len(nodes),
            "total_interfaces": len(edges)
        },
        "nodes": nodes,
        "edges": edges,
        "analysis_notes": {
            "detection_method": "AST parsing + dependency analysis",
            "confidence_level": "medium",
            "limitations": [
                "Cannot detect runtime-only connections",
                "Hardcoded URLs may not be detected",
                "Dynamic routing not captured",
                "Interface confidence is heuristic-based"
            ],
            "recommendations": [
                "Validate against as-designed architecture",
                "Use runtime inspection (as-fielded) for complete picture",
                "Manual review recommended for critical interfaces"
            ]
        }
    }

    return graph


def compare_to_designed(as_built_path: Path, as_designed_path: Path, output_dir: Path):
    """Compare as-built to as-designed architecture"""
    if not as_designed_path.exists():
        print(f"\nWarning: As-designed architecture not found at {as_designed_path}")
        print("Skipping comparison")
        return

    print(f"\nComparing as-built to as-designed...")

    # Call compare_architectures.py
    delta_output = output_dir / f"architecture_delta_as_built_{datetime.now().strftime('%Y%m%d')}.json"

    import subprocess
    import sys

    compare_tool = Path(__file__).parent / "compare_architectures.py"

    try:
        result = subprocess.run([
            sys.executable,
            str(compare_tool),
            "--from", str(as_designed_path),
            "--to", str(as_built_path),
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


def generate_as_built_architecture(system_root: Path, output_path: Path, compare_to: Optional[Path] = None):
    """Main function to generate as-built architecture"""

    print(f"=== As-Built Architecture Generation v{VERSION} ===\n")
    print(f"System Root: {system_root}")
    print(f"Output: {output_path}\n")

    # Discover services
    print("Discovering services...")
    services = discover_services(system_root)
    print(f"  Found {len(services)} services\n")

    if not services:
        print("No services found. Exiting.")
        return 1

    # Analyze each service
    print("Analyzing services...")
    services_data = []
    for svc_path in services:
        print(f"  Analyzing {svc_path.name}...")
        svc_data = analyze_service(svc_path)
        services_data.append(svc_data)
        print(f"    - {len(svc_data['endpoints'])} endpoints")
        print(f"    - {len(svc_data['functions'])} functions")
        print(f"    - {len(svc_data['dependencies'])} dependencies")

    # Infer interfaces
    print("\nInferring interfaces...")
    interfaces = infer_interfaces(services_data)
    print(f"  Detected {len(interfaces)} potential interfaces\n")

    # Build graph
    print("Building as-built graph...")
    graph = build_as_built_graph(system_root, services_data, interfaces)

    # Save graph
    print(f"Saving as-built graph to {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(graph, f, indent=2)

    print(f"\n=== Generation Complete ===")
    print(f"Services analyzed: {len(services_data)}")
    print(f"Interfaces detected: {len(interfaces)}")
    print(f"Output: {output_path}\n")

    # Compare to as-designed if requested
    if compare_to:
        compare_to_designed(output_path, compare_to, output_path.parent)

    return 0


def main():
    parser = argparse.ArgumentParser(description="Generate as-built architecture from implemented code")
    parser.add_argument('--system-root', required=True, help="Path to system root directory")
    parser.add_argument('--output', required=True, help="Path to output as-built graph JSON")
    parser.add_argument('--compare-to', help="Path to as-designed graph for comparison (optional)")

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

    return generate_as_built_architecture(system_root, output_path, compare_to)


if __name__ == "__main__":
    exit(main())
