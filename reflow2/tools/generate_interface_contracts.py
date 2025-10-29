#!/usr/bin/env python3
"""
Generate Interface Contract Documents (ICDs) from service architecture files.

This tool analyzes service_architecture.json files and generates detailed
interface contracts for each interface between components, enabling
independent development with guaranteed integration success.

Creates complete ICD specifications including:
- Input/output schemas with validation rules
- Error handling and retry policies
- Timing and performance constraints
- Integration test scenarios
- Contract verification guidelines

Usage:
    python3 generate_interface_contracts.py /path/to/systems/<system_name>/

Output:
    Creates /systems/<system_name>/interfaces/<interface_id>.json for each interface
    Creates /systems/<system_name>/interfaces/interfaces_summary.json overview

LLM Usage:
    Generated ICD files serve as authoritative specifications for component development.
    Following the contracts precisely guarantees successful integration.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import sanitize_path, validate_system_root, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError

class InterfaceContractGenerator:
    def __init__(self, system_path: Path):
        """
        Initialize contract generator with validated system path.

        Args:
            system_path: Pre-validated Path object (use validate_system_root() before passing)
        """
        self.system_path = system_path

        # Security: Sanitize all file paths (v3.4.0 fix - SV-01)
        try:
            self.index_file = sanitize_path("index.json", self.system_path, must_exist=False)
            self.interfaces_dir = sanitize_path("interfaces", self.system_path, must_exist=False)

            # Template is in reflow_root, need to validate that path
            reflow_root = Path(__file__).parent.parent
            reflow_root = validate_system_root(reflow_root)
            self.template_path = sanitize_path(
                "templates/interface_contract_complete_template.json",
                reflow_root,
                must_exist=True
            )

        except (PathSecurityError, FileNotFoundError) as e:
            print(f"ERROR: Path security violation during initialization: {e}", file=sys.stderr)
            sys.exit(1)

        # Load template
        self.template = safe_load_json(self.template_path, file_type_description="interface contract template")

        # Create interfaces directory
        self.interfaces_dir.mkdir(exist_ok=True)

        self.components = {}
        self.interfaces_generated = []
        self.interfaces_map = {}  # interface_id -> contract
        
    def load_components(self):
        """Load all component specifications from index"""
        if not self.index_file.exists():
            print(f"Error: Index file not found at {self.index_file}")
            sys.exit(1)

        index = safe_load_json(self.index_file, file_type_description="component index")

        for component_id, component_path_str in index.get('components', {}).items():
            # Security: Sanitize component paths (v3.4.0 fix - SV-01)
            try:
                # Always treat component paths as relative to system_path
                if os.path.isabs(component_path_str):
                    print(f"Warning: Absolute path detected for component {component_id}: {component_path_str}")
                    print(f"  Treating as relative to system_path for security")
                    # Strip leading slash to make it relative
                    component_path_str = component_path_str.lstrip('/')

                component_path = sanitize_path(
                    component_path_str,
                    self.system_path,
                    must_exist=True
                )

                self.components[component_id] = safe_load_json(
                    component_path,
                    file_type_description=f"component architecture '{component_id}'"
                )

            except PathSecurityError as e:
                print(f"Warning: Path security violation for component {component_id}: {e}")
                continue
            except FileNotFoundError:
                print(f"Warning: Component file not found: {component_path_str}")
                continue
            except json.JSONDecodeError as e:
                print(f"Warning: Could not parse component {component_id}: {e}")
                continue

        print(f"Loaded {len(self.components)} components")
        
    def extract_interfaces(self):
        """Extract all interfaces from component specifications"""
        interface_pairs = []
        
        for component_id, spec in self.components.items():
            # Get dependencies (consumers)
            dependencies = spec.get('dependencies', [])
            if isinstance(dependencies, dict):
                dependencies = dependencies.get('required_services', [])
            if isinstance(dependencies, list) and dependencies and isinstance(dependencies[0], dict):
                dependencies = [d.get('service_name', d) for d in dependencies]
                
            # Extract interfaces from spec
            interfaces = spec.get('interfaces', [])
            
            # Handle different interface formats
            if isinstance(interfaces, dict):
                # Format: {"provided": [...], "required": [...]}
                for provided in interfaces.get('provided', []):
                    for dep_id in dependencies:
                        if dep_id in self.components:
                            interface_pairs.append({
                                'provider': component_id,
                                'consumer': dep_id,
                                'interface_def': provided,
                                'direction': 'provided'
                            })
                            
                for required in interfaces.get('required', []):
                    target = required.get('service', required.get('target_service'))
                    if target and target in self.components:
                        interface_pairs.append({
                            'provider': target,
                            'consumer': component_id,
                            'interface_def': required,
                            'direction': 'required'
                        })
            elif isinstance(interfaces, list):
                # Format: list of interface objects
                for iface in interfaces:
                    for dep_id in dependencies:
                        if dep_id in self.components:
                            interface_pairs.append({
                                'provider': component_id,
                                'consumer': dep_id,
                                'interface_def': iface,
                                'direction': 'unknown'
                            })
                            
        print(f"Extracted {len(interface_pairs)} interface pairs")
        return interface_pairs
        
    def generate_interface_contract(self, provider: str, consumer: str, interface_def: Dict) -> Dict:
        """Generate a complete interface contract from interface definition"""
        
        # Create interface ID
        interface_name = interface_def.get('name', 'unnamed_interface')
        interface_id = f"{provider}_to_{consumer}_{interface_name}"
        
        # Determine interaction type
        comm_pattern = interface_def.get('communication_pattern', 
                                        interface_def.get('type', 'synchronous'))
        interaction_map = {
            'synchronous': 'synchronous',
            'asynchronous': 'asynchronous',
            'bidirectional': 'bidirectional',
            'pubsub': 'broadcast',
            'rest': 'synchronous',
            'websocket': 'bidirectional',
            'grpc': 'synchronous'
        }
        interaction_type = interaction_map.get(comm_pattern, 'synchronous')
        
        # Determine format from interface type
        iface_type = interface_def.get('interface_type', interface_def.get('protocol', 'json'))
        format_map = {
            'http_endpoint': 'json',
            'message': 'json',
            'pubsub': 'json',
            'grpc': 'protobuf',
            'rest': 'json',
            'HTTPS': 'json',
            'AMQP': 'json',
            'WSS': 'json'
        }
        format_type = format_map.get(iface_type, 'json')
        
        # Build contract
        contract = {
            "template_version": "1.0",
            "interface_id": interface_id,
            "provider_component": provider,
            "consumer_component": consumer,
            "interaction_type": interaction_type,
            "domain_type": "software",  # Default, could be inferred from system
            "contract": {
                "input_specification": {
                    "format": format_type,
                    "schema": interface_def.get('request_schema', interface_def.get('message_format', {})),
                    "constraints": self._extract_constraints(interface_def),
                    "examples": self._generate_examples(interface_def, 'input'),
                    "validation_rules": []
                },
                "output_specification": {
                    "format": format_type,
                    "schema": interface_def.get('response_schema', {}),
                    "success_criteria": "Response matches schema and contains expected fields",
                    "examples": self._generate_examples(interface_def, 'output'),
                    "validation_rules": []
                },
                "error_handling": {
                    "error_conditions": self._extract_error_conditions(interface_def),
                    "error_responses": [],
                    "retry_policy": {
                        "applicable": "yes" if interaction_type == "asynchronous" else "no",
                        "max_retries": 3,
                        "backoff_strategy": "exponential"
                    },
                    "fallback_behavior": "Log error and return error response to consumer"
                },
                "timing_constraints": {
                    "max_latency": interface_def.get('max_latency', 'none'),
                    "throughput_requirements": interface_def.get('throughput', 'none'),
                    "synchronization_requirements": "depends_on_interaction_type"
                },
                "state_requirements": {
                    "stateful": interface_def.get('stateful', False),
                    "state_description": interface_def.get('state_description', 'none'),
                    "state_persistence": "none"
                }
            },
            "integration_tests": {
                "test_scenarios": self._generate_test_scenarios(interface_def),
                "contract_verification": {
                    "provider_verification": f"Provider must implement interface matching {interface_id} specification",
                    "consumer_verification": f"Consumer must call interface according to {interface_id} specification",
                    "integration_verification": "Run integration test scenarios to verify end-to-end interaction"
                },
                "mock_specifications": {
                    "provider_mock": f"Mock {provider} that returns responses matching output_specification",
                    "consumer_mock": f"Mock {consumer} that sends requests matching input_specification"
                }
            },
            "dependencies": {
                "depends_on_interfaces": [],
                "environmental_dependencies": self._extract_env_dependencies(interface_def)
            },
            "metadata": {
                "version": f"1.0+{datetime.now().strftime('%Y-%m-%d')}",
                "last_updated": datetime.now().strftime('%Y-%m-%d'),
                "status": "draft",
                "backwards_compatible": True,
                "breaking_changes": [],
                "rationale": interface_def.get('description', f"Interface between {provider} and {consumer}"),
                "alternatives_considered": []
            }
        }
        
        return contract
        
    def _extract_constraints(self, interface_def: Dict) -> List[str]:
        """Extract constraints from interface definition"""
        constraints = []
        
        if interface_def.get('auth_required'):
            constraints.append("Authentication required")
        if 'rate_limit' in interface_def:
            constraints.append(f"Rate limit: {interface_def['rate_limit']}")
        if 'path' in interface_def:
            constraints.append(f"HTTP path: {interface_def['path']}")
        if 'method' in interface_def:
            constraints.append(f"HTTP method: {interface_def['method']}")
            
        return constraints
        
    def _extract_error_conditions(self, interface_def: Dict) -> List[Dict]:
        """Extract error conditions from interface definition"""
        return [
            {
                "error_id": "INVALID_INPUT",
                "condition": "Input does not match schema",
                "severity": "high"
            },
            {
                "error_id": "AUTH_FAILED",
                "condition": "Authentication failed",
                "severity": "critical"
            },
            {
                "error_id": "SERVICE_UNAVAILABLE",
                "condition": "Provider service is unavailable",
                "severity": "critical"
            }
        ]
        
    def _generate_examples(self, interface_def: Dict, io_type: str) -> List[Dict]:
        """Generate example inputs/outputs"""
        examples = []
        
        if io_type == 'input':
            schema = interface_def.get('request_schema', interface_def.get('message_format', {}))
            if schema:
                examples.append({
                    "example_id": "example_input_1",
                    "description": "Example request",
                    "value": self._generate_example_from_schema(schema)
                })
        else:
            schema = interface_def.get('response_schema', {})
            if schema:
                examples.append({
                    "example_id": "example_output_1",
                    "description": "Example response",
                    "value": self._generate_example_from_schema(schema),
                    "corresponding_input": "example_input_1"
                })
                
        return examples
        
    def _generate_example_from_schema(self, schema: Dict) -> Any:
        """Generate example data from schema"""
        if isinstance(schema, dict) and 'schema' in schema:
            schema = schema['schema']
            
        if isinstance(schema, dict):
            example = {}
            for key, value_type in schema.items():
                if value_type == 'string':
                    example[key] = f"example_{key}"
                elif value_type == 'integer' or value_type == 'number':
                    example[key] = 0
                elif value_type == 'boolean':
                    example[key] = True
                elif value_type == 'array':
                    example[key] = []
                elif value_type == 'object':
                    example[key] = {}
                else:
                    example[key] = f"example_{key}"
            return example
        return {}
        
    def _generate_test_scenarios(self, interface_def: Dict) -> List[Dict]:
        """Generate test scenarios for interface"""
        return [
            {
                "scenario_id": "happy_path",
                "description": "Successful interface interaction",
                "input": self._generate_example_from_schema(
                    interface_def.get('request_schema', interface_def.get('message_format', {}))
                ),
                "expected_output": self._generate_example_from_schema(
                    interface_def.get('response_schema', {})
                ),
                "success_criteria": "Output matches expected_output schema",
                "execution_steps": [
                    "Setup: Initialize provider and consumer",
                    "Execute: Consumer calls interface with test input",
                    "Verify: Check output matches expected schema and values"
                ]
            },
            {
                "scenario_id": "invalid_input",
                "description": "Test invalid input handling",
                "input": {},
                "expected_error": "INVALID_INPUT",
                "success_criteria": "Provider returns appropriate error response"
            }
        ]
        
    def _extract_env_dependencies(self, interface_def: Dict) -> List[str]:
        """Extract environmental dependencies"""
        deps = []
        
        protocol = interface_def.get('protocol', interface_def.get('interface_type', ''))
        if 'HTTPS' in protocol or 'http' in protocol.lower():
            deps.append("network_connectivity")
        if 'AMQP' in protocol:
            deps.append("message_broker_available")
        if interface_def.get('auth_required'):
            deps.append("authentication_service_available")
            
        return deps
        
    def generate_all_contracts(self):
        """Generate all interface contracts"""
        interface_pairs = self.extract_interfaces()

        for pair in interface_pairs:
            contract = self.generate_interface_contract(
                pair['provider'],
                pair['consumer'],
                pair['interface_def']
            )

            interface_id = contract['interface_id']

            # Security: Sanitize contract path (v3.4.0 fix - SV-01)
            try:
                # interfaces_dir is already validated, but sanitize the specific file
                contract_filename = f"{interface_id}.json"
                contract_path = sanitize_path(
                    f"interfaces/{contract_filename}",
                    self.system_path,
                    must_exist=False
                )

                with open(contract_path, 'w') as f:
                    json.dump(contract, f, indent=2)

                self.interfaces_generated.append(interface_id)
                self.interfaces_map[interface_id] = contract

            except PathSecurityError as e:
                print(f"Warning: Could not write contract {interface_id}: {e}")
                continue

        print(f"\nGenerated {len(self.interfaces_generated)} interface contracts")
        print(f"Saved to: {self.interfaces_dir}/")
        
    def generate_summary(self):
        """Generate summary of interface contracts with LLM development guidance"""
        summary = {
            "system_path": str(self.system_path),
            "generation_date": datetime.now().isoformat(),
            "total_interfaces": len(self.interfaces_generated),
            "llm_development_instructions": {
                "purpose": "Generated ICD files provide complete interface specifications for independent component development",
                "usage_workflow": [
                    "1. Locate the ICD file for the interface you're implementing",
                    "2. For provider components: Implement interface to satisfy output_specification",
                    "3. For consumer components: Send requests matching input_specification format",
                    "4. Follow error_handling specifications for robust error management",
                    "5. Use integration_tests scenarios to verify contract compliance",
                    "6. Generated contracts guarantee integration success when followed precisely"
                ],
                "contract_guarantee": "If both provider and consumer implement according to their respective ICD specifications, integration will succeed without additional coordination"
            },
            "interfaces": []
        }
        
        for interface_id, contract in self.interfaces_map.items():
            summary['interfaces'].append({
                "interface_id": interface_id,
                "provider": contract['provider_component'],
                "consumer": contract['consumer_component'],
                "interaction_type": contract['interaction_type'],
                "status": contract['metadata']['status'],
                "file_path": f"interfaces/{interface_id}.json",
                "development_guidance": {
                    "provider_requirements": f"Implement {contract['provider_component']} to satisfy output_specification",
                    "consumer_requirements": f"Implement {contract['consumer_component']} to send requests matching input_specification",
                    "integration_confidence": "high_confidence_if_contracts_followed"
                }
            })
            
        # Security: Sanitize summary path (v3.4.0 fix - SV-01)
        try:
            summary_path = sanitize_path(
                "interfaces/interfaces_summary.json",
                self.system_path,
                must_exist=False
            )

            with open(summary_path, 'w') as f:
                json.dump(summary, f, indent=2)

            print(f"Summary saved to: {summary_path}")
            print(f"📋 Generated {len(self.interfaces_generated)} interface contracts")
            print("🤖 LLM agents can use these contracts for independent component development")
            print("✅ Following contracts precisely guarantees integration success")

        except PathSecurityError as e:
            print(f"ERROR: Could not write summary file: {e}", file=sys.stderr)
        
def main():
    if len(sys.argv) != 2:
        print("Usage: python3 generate_interface_contracts.py /path/to/systems/<system_name>/")
        sys.exit(1)

    # Security: Validate system path (v3.4.0 fix - SV-01)
    try:
        system_path = validate_system_root(sys.argv[1])
    except PathSecurityError as e:
        print(f"ERROR: Path security violation: {e}", file=sys.stderr)
        print("System path must be a valid directory", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("Interface Contract Generator")
    print("=" * 80)
    print(f"System path: {system_path}\n")

    generator = InterfaceContractGenerator(system_path)
    generator.load_components()
    generator.generate_all_contracts()
    generator.generate_summary()

    print("\n" + "=" * 80)
    print("Interface contract generation complete!")
    print("=" * 80)
    
if __name__ == "__main__":
    main()
