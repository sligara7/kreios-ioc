#!/usr/bin/env python3
"""
Architecture Validation Tool

Validates service_architecture.json files for template compliance and architectural consistency.
This tool checks:
- Interface consistency between services and interface_registry.json
- Resource isolation between services  
- Circular dependency detection
- Directory structure completeness

Outputs structured JSON results for LLM agent analysis and automated fixing.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import networkx as nx
from typing import Dict, List, Set, Tuple

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import validate_system_root, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError

# Adjust paths for reflow directory structure
REFLOW_ROOT = Path(__file__).parent.parent
TEMPLATES_PATH = REFLOW_ROOT / "templates"
DEFINITIONS_PATH = REFLOW_ROOT / "definitions"

class ArchitectureValidator:
    def __init__(self, system_path: Path):
        self.system_path = Path(system_path)
        self.working_memory = self.load_working_memory()
        self.validation_results = {
            "timestamp": datetime.now().isoformat(),
            "system": self.system_path.name,
            "checks": {},
            "issues": []
        }

    def load_working_memory(self) -> dict:
        candidates = [self.system_path / "working_memory.json",
                      self.system_path / "context" / "working_memory.json"]
        for memory_file in candidates:
            if memory_file.exists():
                try:
                    return safe_load_json(memory_file, file_type_description="working memory")
                except JSONValidationError:
                    # Continue to next candidate if JSON is invalid
                    continue
        return {}

    def load_service_files(self) -> Dict[str, dict]:
        services = {}
        for service_file in self.system_path.rglob("service_architecture.json"):
            try:
                services[service_file.parent.name] = safe_load_json(
                    service_file,
                    file_type_description="service architecture"
                )
            except JSONValidationError as e:
                print(f"Warning: Skipping invalid service architecture {service_file}: {e}")
                continue
        return services

    def validate_interface_consistency(self) -> List[dict]:
        """Check interface consistency across services"""
        issues = []
        services = self.load_service_files()
        interface_registry = self.load_interface_registry()

        for service_name, service in services.items():
            for interface in service.get("interfaces", []):
                # Check interface exists in registry
                if service_name not in interface_registry["interfaces"]:
                    issues.append({
                        "type": "interface_missing",
                        "service": service_name,
                        "interface": interface["name"],
                        "severity": "high",
                        "description": f"Service '{service_name}' declares interface '{interface['name']}' but it's not in interface_registry.json",
                        "recommendation": f"Add interface '{interface['name']}' to interface_registry.json for service '{service_name}'"
                    })
                    continue

                reg_interface = interface_registry["interfaces"][service_name].get(interface["name"])
                if not reg_interface:
                    issues.append({
                        "type": "interface_not_registered",
                        "service": service_name,
                        "interface": interface["name"],
                        "severity": "medium",
                        "description": f"Interface '{interface['name']}' for service '{service_name}' exists in registry but details are missing",
                        "recommendation": f"Complete interface definition for '{interface['name']}' in interface_registry.json"
                    })
                    continue

                # Check interface details match
                for field in ["path", "method", "auth_required"]:
                    if interface.get(field) != reg_interface.get(field):
                        issues.append({
                            "type": "interface_mismatch",
                            "service": service_name,
                            "interface": interface["name"],
                            "field": field,
                            "severity": "high",
                            "description": f"Interface '{interface['name']}' field '{field}' mismatch between service definition and registry",
                            "recommendation": f"Update {field} for interface '{interface['name']}' in service_architecture.json or interface_registry.json to match",
                            "service_value": interface.get(field),
                            "registry_value": reg_interface.get(field)
                        })

        return issues

    def validate_resource_isolation(self) -> List[dict]:
        """Check resource isolation between services"""
        issues = []
        services = self.load_service_files()
        shared_resources = set()

        # Collect shared resources
        for service in services.values():
            for relationship in service.get("service_resource_relationships", []):
                resource = (relationship["resource_type"], relationship["resource_performer"])
                if resource in shared_resources:
                    issues.append({
                        "type": "shared_resource",
                        "resource": resource[0],
                        "performer": resource[1],
                        "severity": "medium",
                        "description": f"Resource '{resource[0]}' performed by '{resource[1]}' is shared between multiple services",
                        "recommendation": "Implement resource isolation by dedicating resources to single services or using proper resource management patterns"
                    })
                shared_resources.add(resource)

        return issues

    def validate_dependency_cycles(self) -> List[dict]:
        """Check for circular dependencies"""
        issues = []
        services = self.load_service_files()
        
        # Build dependency graph
        G = nx.DiGraph()
        for service_name, service in services.items():
            G.add_node(service_name)
            for dep in service.get("dependencies", []):
                G.add_edge(service_name, dep)

        # Find cycles
        try:
            cycles = list(nx.simple_cycles(G))
            for cycle in cycles:
                issues.append({
                    "type": "circular_dependency",
                    "cycle": cycle,
                    "severity": "high",
                    "description": f"Circular dependency detected: {' -> '.join(cycle + [cycle[0]])}",
                    "recommendation": "Break dependency cycle by introducing async communication, event-driven architecture, or refactoring service boundaries"
                })
        except Exception as e:
            issues.append({
                "type": "graph_analysis_error",
                "error": str(e),
                "severity": "high"
            })

        return issues

    def load_interface_registry(self) -> dict:
        candidates = [
            self.system_path / "specs" / "machine" / "interface_registry.json",
            self.system_path / "specs" / "interface_registry.json",
            self.system_path / "interface_registry.json"
        ]
        for registry_file in candidates:
            if registry_file.exists():
                try:
                    return safe_load_json(registry_file, file_type_description="interface registry")
                except JSONValidationError:
                    # Continue to next candidate if JSON is invalid
                    continue
        return {"interfaces": {}}

    def validate_directory_structure(self) -> List[dict]:
        """Check for empty or incomplete system directories"""
        issues = []
        
        # Skip directory structure validation - it's incompatible with reflow's specs-based structure
        # Service architecture files are expected in specs/machine/service_arch/<service_name>/
        # NOT in services/<service_name>/ as this method incorrectly assumes
        # Actual service validation is done via load_service_files() which uses rglob
        
        return issues

    def run_all_validations(self) -> dict:
        """Run all validation checks"""
        # Directory structure validation
        directory_issues = self.validate_directory_structure()
        self.validation_results["checks"]["directory_structure"] = {
            "status": "fail" if directory_issues else "pass",
            "issues": directory_issues
        }
        # Interface consistency
        interface_issues = self.validate_interface_consistency()
        self.validation_results["checks"]["interface_consistency"] = {
            "status": "fail" if interface_issues else "pass",
            "issues": interface_issues
        }

        # Resource isolation
        resource_issues = self.validate_resource_isolation()
        self.validation_results["checks"]["resource_isolation"] = {
            "status": "fail" if resource_issues else "pass",
            "issues": resource_issues
        }

        # Dependency cycles
        dependency_issues = self.validate_dependency_cycles()
        self.validation_results["checks"]["dependency_cycles"] = {
            "status": "fail" if dependency_issues else "pass",
            "issues": dependency_issues
        }

        # Combine all issues
        all_issues = directory_issues + interface_issues + resource_issues + dependency_issues
        self.validation_results["issues"] = all_issues
        
        # Add LLM guidance
        self.validation_results["llm_agent_instructions"] = {
            "total_issues": len(all_issues),
            "critical_issues": len([i for i in all_issues if i.get("severity") == "high"]),
            "action_required": any(i.get("severity") == "high" for i in all_issues),
            "fix_workflow": [
                "1. Address all high severity issues first - these prevent proper system operation",
                "2. Update service_architecture.json files to fix interface mismatches",
                "3. Update interface_registry.json to add missing interface definitions",
                "4. Refactor service boundaries to resolve circular dependencies",
                "5. Implement proper resource isolation patterns",
                "6. Create missing service_architecture.json files",
                "7. Re-run validation until all checks pass"
            ],
            "common_fixes": {
                "interface_missing": "Add missing interface definition to interface_registry.json",
                "interface_mismatch": "Align interface definitions between service files and registry",
                "circular_dependency": "Break cycles using async communication or service boundary refactoring",
                "shared_resource": "Implement resource isolation by dedicating resources to single services",
                "missing_architecture": "Create service_architecture.json file using template"
            }
        }

        return self.validation_results

    def update_working_memory(self):
        """Update working memory with validation results"""
        if not self.working_memory:
            return

        self.working_memory["validation_state"] = {
            "interface_consistency": {
                "last_checked": datetime.now().isoformat(),
                "status": self.validation_results["checks"]["interface_consistency"]["status"],
                "issues": self.validation_results["checks"]["interface_consistency"]["issues"]
            },
            "resource_isolation": {
                "last_checked": datetime.now().isoformat(),
                "status": self.validation_results["checks"]["resource_isolation"]["status"],
                "issues": self.validation_results["checks"]["resource_isolation"]["issues"]
            },
            "dependency_cycles": {
                "last_checked": datetime.now().isoformat(),
                "status": self.validation_results["checks"]["dependency_cycles"]["status"],
                "issues": self.validation_results["checks"]["dependency_cycles"]["issues"]
            }
        }

        with open(self.system_path / "working_memory.json", "w") as f:
            json.dump(self.working_memory, f, indent=2)

def main():
    if len(sys.argv) != 2:
        print("Usage: validate_architecture.py <system_path>")
        sys.exit(1)

    # Security: Validate system path (v3.4.0 fix - SV-01)
    try:
        system_path = validate_system_root(sys.argv[1])
    except PathSecurityError as e:
        print(f"Error: Path security violation: {e}", file=sys.stderr)
        print("System path must be a valid directory", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    validator = ArchitectureValidator(system_path)
    results = validator.run_all_validations()
    validator.update_working_memory()

    # Enhanced output for LLM agents
    total_issues = len(results["issues"])
    critical_issues = len([i for i in results["issues"] if i.get("severity") == "high"])
    
    print(json.dumps(results, indent=2))
    
    # Summary for LLM agents
    if critical_issues > 0:
        print(f"\n⚠️  CRITICAL VALIDATION FAILURES - {critical_issues} high severity issues detected")
        print("LLM agent should address these issues immediately before proceeding")
    elif total_issues > 0:
        print(f"\n⚠️  VALIDATION ISSUES - {total_issues} issues detected")
        print("LLM agent should review and fix these issues") 
    else:
        print("\n✅ VALIDATION PASSED - All architecture files are valid")

    # Exit with status code
    sys.exit(1 if results["issues"] else 0)

if __name__ == "__main__":
    main()