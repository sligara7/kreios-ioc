#!/usr/bin/env python3
"""
Development Language Selection Tool

Interactive tool to help users select programming languages for their services.
Supports both homogeneous (single language) and heterogeneous (multiple languages) systems.

This tool respects the black-box architecture principles by:
1. Allowing different services to use different languages based on suitability
2. Maintaining interface contract integrity regardless of implementation language
3. Providing language-specific development guidance while preserving architectural boundaries

Usage:
    python3 select_development_languages.py <system_path> [--interactive] [--config <config_file>]
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any
import argparse

# Import secure path handling (v3.4.0 security fix - SV-01)
from path_utils import sanitize_path, validate_system_root, PathSecurityError

# Import JSON validation (v3.4.0 security fix - SV-02)
from json_utils import safe_load_json, JSONValidationError

class LanguageSelector:
    def __init__(self, system_path: Path):
        """
        Initialize language selector with validated system path.

        Args:
            system_path: Pre-validated Path object (use validate_system_root() before passing)
        """
        self.system_path = system_path
        self.system_name = self.system_path.name
        
        # Language configurations with framework options
        self.supported_languages = {
            "python": {
                "frameworks": ["fastapi", "flask", "django", "starlette"],
                "default_framework": "fastapi",
                "strengths": ["AI/ML", "data processing", "rapid prototyping", "scientific computing"],
                "considerations": ["Performance for CPU-intensive tasks", "Global Interpreter Lock"],
                "best_for": ["ML services", "data processing", "APIs", "scripting", "web backends"]
            },
            "java": {
                "frameworks": ["spring-boot", "micronaut", "quarkus", "dropwizard"],
                "default_framework": "spring-boot", 
                "strengths": ["Enterprise applications", "high performance", "mature ecosystem", "strong typing"],
                "considerations": ["Memory usage", "startup time", "verbosity"],
                "best_for": ["Enterprise services", "high-throughput APIs", "complex business logic"]
            },
            "javascript": {
                "frameworks": ["express", "koa", "hapi", "fastify"],
                "default_framework": "express",
                "strengths": ["Full-stack development", "large ecosystem", "JSON handling"],
                "considerations": ["Single-threaded", "dynamic typing challenges"],
                "best_for": ["Web APIs", "real-time applications", "frontend integration"]
            },
            "typescript": {
                "frameworks": ["express", "nestjs", "koa", "fastify"],
                "default_framework": "nestjs",
                "strengths": ["Type safety", "JavaScript ecosystem", "modern tooling"],
                "considerations": ["Compilation step", "learning curve"],
                "best_for": ["Large-scale APIs", "enterprise applications", "full-stack development"]
            },
            "go": {
                "frameworks": ["gin", "echo", "fiber", "chi"],
                "default_framework": "gin",
                "strengths": ["High performance", "concurrency", "small binaries", "fast compilation"],
                "considerations": ["Smaller ecosystem", "verbose error handling"],
                "best_for": ["High-performance services", "concurrent processing", "system services"]
            },
            "rust": {
                "frameworks": ["axum", "warp", "actix-web", "rocket"],
                "default_framework": "axum",
                "strengths": ["Memory safety", "zero-cost abstractions", "high performance"],
                "considerations": ["Steep learning curve", "longer development time"],
                "best_for": ["Performance-critical services", "system programming", "safe concurrent processing"]
            },
            "ruby": {
                "frameworks": ["rails", "sinatra", "hanami", "roda"],
                "default_framework": "sinatra",
                "strengths": ["Developer productivity", "readable code", "mature web ecosystem"],
                "considerations": ["Performance", "concurrency limitations"],
                "best_for": ["Rapid prototyping", "web applications", "APIs with complex business logic"]
            },
            "csharp": {
                "frameworks": ["asp.net-core", "minimal-api", "nancy"],
                "default_framework": "asp.net-core",
                "strengths": ["Strong typing", "comprehensive framework", "performance", "tooling"],
                "considerations": ["Microsoft ecosystem dependency", "licensing"],
                "best_for": ["Enterprise applications", "Windows environments", "high-performance web APIs"]
            }
        }
        
        self.language_configuration = {
            "system_name": self.system_name,
            "configuration_type": None,  # "homogeneous" or "heterogeneous"
            "default_language": None,
            "default_framework": None,
            "service_languages": {},
            "rationale": {},
            "development_setup": {}
        }

    def load_system_services(self) -> List[Dict[str, Any]]:
        """Load services from build_ready_index.json."""
        # Security: Sanitize build_ready_index path (v3.4.0 fix - SV-01)
        try:
            build_ready_path = sanitize_path(
                "build_ready_index.json",
                self.system_path,
                must_exist=True
            )
        except (PathSecurityError, FileNotFoundError) as e:
            print(f"❌ Error: build_ready_index.json not found or path security violation: {e}")
            sys.exit(1)

        build_ready = safe_load_json(build_ready_path, file_type_description="build-ready configuration")

        services = []
        components = build_ready.get("components", {})

        for service_id, component_info in components.items():
            # Security: Sanitize service architecture path (v3.4.0 fix - SV-01)
            try:
                service_arch_path_str = component_info.get("service_architecture_path", "")
                if not service_arch_path_str:
                    continue

                # Make path relative to system_path
                service_arch_path = sanitize_path(
                    service_arch_path_str,
                    self.system_path,
                    must_exist=True
                )

                service_arch = safe_load_json(service_arch_path, file_type_description="service architecture")

                services.append({
                    "service_id": service_id,
                    "service_name": service_arch.get("service_name", service_id),
                    "purpose": service_arch.get("purpose", ""),
                    "component_classification": service_arch.get("component_classification", "service"),
                    "interfaces": service_arch.get("interfaces", []),
                    "performance": service_arch.get("performance", {}),
                    "architecture_path": str(service_arch_path)
                })

            except (PathSecurityError, FileNotFoundError) as e:
                print(f"Warning: Could not load service {service_id}: {e}")
                continue

        return services

    def analyze_service_requirements(self, service: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze service requirements to suggest appropriate languages."""
        analysis = {
            "service_id": service["service_id"],
            "requirements": [],
            "suggested_languages": [],
            "rationale": []
        }
        
        # Performance analysis
        performance = service.get("performance", {})
        expected_load = performance.get("expected_load", "medium")
        
        if expected_load == "high":
            analysis["requirements"].append("high_performance")
            analysis["suggested_languages"].extend(["go", "rust", "java"])
            analysis["rationale"].append("High performance requirements suggest Go, Rust, or Java")
        
        # Interface analysis
        interfaces = service.get("interfaces", [])
        has_external_http = any(
            iface.get("interface_type") == "http_endpoint" and iface.get("dependency_type") == "external"
            for iface in interfaces
        )
        
        if has_external_http:
            analysis["requirements"].append("web_api")
            analysis["suggested_languages"].extend(["python", "typescript", "java", "go"])
            analysis["rationale"].append("HTTP endpoints suggest web framework support")
        
        # Purpose analysis
        purpose = service.get("purpose", "").lower()
        if any(keyword in purpose for keyword in ["ml", "machine learning", "ai", "data", "analytics"]):
            analysis["requirements"].append("data_processing")
            analysis["suggested_languages"].extend(["python", "julia", "r"])
            analysis["rationale"].append("Data/ML workloads suggest Python ecosystem")
        
        if any(keyword in purpose for keyword in ["auth", "security", "crypto"]):
            analysis["requirements"].append("security")
            analysis["suggested_languages"].extend(["rust", "go", "java"])
            analysis["rationale"].append("Security-critical services benefit from memory-safe or strongly-typed languages")
        
        # Remove duplicates and rank by suitability
        analysis["suggested_languages"] = list(dict.fromkeys(analysis["suggested_languages"]))
        
        return analysis

    def interactive_homogeneous_selection(self) -> str:
        """Interactive selection for homogeneous systems."""
        print("\n🔧 Homogeneous System Configuration")
        print("All services will be developed in the same programming language.\n")
        
        # Show available languages
        print("Available programming languages:")
        for i, (lang, config) in enumerate(self.supported_languages.items(), 1):
            print(f"{i:2d}. {lang.capitalize()}")
            print(f"    Frameworks: {', '.join(config['frameworks'])}")
            print(f"    Best for: {', '.join(config['best_for'])}")
            print()
        
        while True:
            try:
                choice = input("Select language number (1-{0}): ".format(len(self.supported_languages)))
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(self.supported_languages):
                    selected_language = list(self.supported_languages.keys())[choice_idx]
                    break
                else:
                    print("Invalid selection. Please choose a number from the list.")
            except (ValueError, KeyboardInterrupt):
                print("Invalid input. Please enter a number.")
        
        # Framework selection
        lang_config = self.supported_languages[selected_language]
        print(f"\n🔧 Framework Selection for {selected_language.capitalize()}")
        print(f"Available frameworks: {', '.join(lang_config['frameworks'])}")
        
        default_framework = lang_config['default_framework']
        framework_choice = input(f"Select framework (default: {default_framework}): ").strip()
        selected_framework = framework_choice if framework_choice else default_framework
        
        if selected_framework not in lang_config['frameworks']:
            print(f"Warning: {selected_framework} not in recommended frameworks. Using {default_framework}")
            selected_framework = default_framework
        
        return selected_language, selected_framework

    def interactive_heterogeneous_selection(self, services: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """Interactive selection for heterogeneous systems."""
        print("\n🔧 Heterogeneous System Configuration")
        print("Different services can use different programming languages based on their requirements.\n")
        
        service_selections = {}
        
        for service in services:
            print(f"\n--- Service: {service['service_name']} ---")
            print(f"Purpose: {service['purpose']}")
            print(f"Classification: {service['component_classification']}")
            
            # Show analysis
            analysis = self.analyze_service_requirements(service)
            if analysis['suggested_languages']:
                print(f"Suggested languages: {', '.join(analysis['suggested_languages'])}")
                print("Rationale:")
                for rationale in analysis['rationale']:
                    print(f"  • {rationale}")
            
            print("\nAvailable languages:")
            for i, (lang, config) in enumerate(self.supported_languages.items(), 1):
                marker = "⭐" if lang in analysis['suggested_languages'] else "  "
                print(f"{marker} {i:2d}. {lang.capitalize()} - {', '.join(config['best_for'][:2])}")
            
            while True:
                try:
                    choice = input(f"Select language for {service['service_name']} (1-{len(self.supported_languages)}): ")
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(self.supported_languages):
                        selected_language = list(self.supported_languages.keys())[choice_idx]
                        break
                    else:
                        print("Invalid selection. Please choose a number from the list.")
                except (ValueError, KeyboardInterrupt):
                    print("Invalid input. Please enter a number.")
            
            # Framework selection
            lang_config = self.supported_languages[selected_language]
            default_framework = lang_config['default_framework']
            framework_choice = input(f"Framework for {selected_language} (default: {default_framework}): ").strip()
            selected_framework = framework_choice if framework_choice else default_framework
            
            service_selections[service['service_id']] = {
                "language": selected_language,
                "framework": selected_framework,
                "rationale": f"Selected based on: {', '.join(analysis['requirements'])}"
            }
        
        return service_selections

    def generate_configuration(self, configuration_type: str, services: List[Dict[str, Any]], **kwargs):
        """Generate the language configuration."""
        self.language_configuration["configuration_type"] = configuration_type
        
        if configuration_type == "homogeneous":
            language, framework = kwargs.get("language"), kwargs.get("framework")
            self.language_configuration["default_language"] = language
            self.language_configuration["default_framework"] = framework
            
            # Apply to all services
            for service in services:
                self.language_configuration["service_languages"][service["service_id"]] = {
                    "language": language,
                    "framework": framework,
                    "rationale": "Homogeneous system configuration"
                }
        
        elif configuration_type == "heterogeneous":
            service_selections = kwargs.get("service_selections", {})
            self.language_configuration["service_languages"] = service_selections
            
            # Determine most common language as default
            language_counts = {}
            for selection in service_selections.values():
                lang = selection["language"]
                language_counts[lang] = language_counts.get(lang, 0) + 1
            
            if language_counts:
                most_common_lang = max(language_counts.items(), key=lambda x: x[1])[0]
                self.language_configuration["default_language"] = most_common_lang
                self.language_configuration["default_framework"] = self.supported_languages[most_common_lang]["default_framework"]
        
        # Add development setup information
        self.generate_development_setup()

    def generate_development_setup(self):
        """Generate development environment setup information."""
        languages_used = set()
        for service_config in self.language_configuration["service_languages"].values():
            languages_used.add(service_config["language"])
        
        setup_info = {}
        for language in languages_used:
            lang_config = self.supported_languages[language]
            setup_info[language] = {
                "runtime_requirements": self.get_runtime_requirements(language),
                "framework_setup": self.get_framework_setup(language),
                "development_tools": self.get_development_tools(language),
                "testing_frameworks": self.get_testing_frameworks(language)
            }
        
        self.language_configuration["development_setup"] = setup_info

    def get_runtime_requirements(self, language: str) -> List[str]:
        """Get runtime requirements for a language."""
        requirements = {
            "python": ["Python 3.8+", "pip", "virtualenv or conda"],
            "java": ["Java 11+ JDK", "Maven or Gradle"],
            "javascript": ["Node.js 16+", "npm or yarn"],
            "typescript": ["Node.js 16+", "TypeScript compiler", "npm or yarn"],
            "go": ["Go 1.18+"],
            "rust": ["Rust 1.60+", "Cargo"],
            "ruby": ["Ruby 3.0+", "Bundler"],
            "csharp": [".NET 6+", "NuGet"]
        }
        return requirements.get(language, [f"{language} runtime"])

    def get_framework_setup(self, language: str) -> Dict[str, str]:
        """Get framework setup commands."""
        setups = {
            "python": {
                "fastapi": "pip install fastapi uvicorn",
                "flask": "pip install flask",
                "django": "pip install django"
            },
            "java": {
                "spring-boot": "Spring Initializr or Maven/Gradle",
                "micronaut": "Micronaut CLI",
                "quarkus": "Quarkus CLI"
            },
            "typescript": {
                "nestjs": "npm install -g @nestjs/cli",
                "express": "npm install express @types/express"
            }
        }
        return setups.get(language, {})

    def get_development_tools(self, language: str) -> List[str]:
        """Get recommended development tools."""
        tools = {
            "python": ["Black (formatter)", "Pylint/Flake8 (linting)", "pytest (testing)"],
            "java": ["IntelliJ IDEA/Eclipse", "Checkstyle", "JUnit"],
            "javascript": ["ESLint", "Prettier", "Jest"],
            "typescript": ["TSLint/ESLint", "Prettier", "Jest"],
            "go": ["gofmt", "golint", "go test"],
            "rust": ["rustfmt", "clippy", "cargo test"],
            "ruby": ["RuboCop", "RSpec", "Bundler"],
            "csharp": ["Visual Studio/Rider", "StyleCop", "xUnit"]
        }
        return tools.get(language, [])

    def get_testing_frameworks(self, language: str) -> List[str]:
        """Get testing frameworks for the language."""
        frameworks = {
            "python": ["pytest", "unittest", "testcontainers-python"],
            "java": ["JUnit 5", "Mockito", "Testcontainers"],
            "javascript": ["Jest", "Mocha", "Cypress"],
            "typescript": ["Jest", "Mocha", "Supertest"],
            "go": ["go test", "Testify", "GoMock"],
            "rust": ["cargo test", "mockall"],
            "ruby": ["RSpec", "Minitest"],
            "csharp": ["xUnit", "NUnit", "Moq"]
        }
        return frameworks.get(language, [])

    def save_configuration(self):
        """Save the language configuration to file."""
        # Security: Sanitize output path (v3.4.0 fix - SV-01)
        try:
            output_path = sanitize_path(
                "development_language_configuration.json",
                self.system_path,
                must_exist=False
            )

            with open(output_path, 'w') as f:
                json.dump(self.language_configuration, f, indent=2)

            print(f"\n✅ Configuration saved to: {output_path}")
            return output_path

        except PathSecurityError as e:
            print(f"ERROR: Could not save configuration: Path security violation: {e}")
            sys.exit(1)

    def print_summary(self):
        """Print a summary of the configuration."""
        print("\n" + "="*60)
        print("DEVELOPMENT LANGUAGE CONFIGURATION SUMMARY")
        print("="*60)
        
        print(f"System: {self.language_configuration['system_name']}")
        print(f"Configuration Type: {self.language_configuration['configuration_type'].capitalize()}")
        
        if self.language_configuration['configuration_type'] == 'homogeneous':
            print(f"Language: {self.language_configuration['default_language'].capitalize()}")
            print(f"Framework: {self.language_configuration['default_framework']}")
        
        print("\nService Language Assignments:")
        for service_id, config in self.language_configuration['service_languages'].items():
            print(f"  • {service_id}: {config['language'].capitalize()} ({config['framework']})")
            if config.get('rationale'):
                print(f"    Rationale: {config['rationale']}")
        
        print("\nDevelopment Environment Requirements:")
        for language, setup in self.language_configuration['development_setup'].items():
            print(f"\n{language.capitalize()}:")
            print(f"  Runtime: {', '.join(setup['runtime_requirements'])}")
            if setup['development_tools']:
                print(f"  Tools: {', '.join(setup['development_tools'])}")


def main():
    parser = argparse.ArgumentParser(description="Select development languages for system services")
    parser.add_argument("system_path", help="Path to the system directory")
    parser.add_argument("--interactive", action="store_true", default=True,
                       help="Interactive mode (default)")
    parser.add_argument("--config", help="Load configuration from JSON file")
    parser.add_argument("--homogeneous", action="store_true",
                       help="Force homogeneous configuration")
    parser.add_argument("--heterogeneous", action="store_true",
                       help="Force heterogeneous configuration")

    args = parser.parse_args()

    # Security: Validate system path (v3.4.0 fix - SV-01)
    try:
        system_path = validate_system_root(args.system_path)
    except PathSecurityError as e:
        print(f"❌ Path security violation: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ System path does not exist: {args.system_path}")
        sys.exit(1)

    selector = LanguageSelector(system_path)
    services = selector.load_system_services()

    if not services:
        print("❌ No services found in system. Please complete architecture workflow first.")
        sys.exit(1)

    print(f"🚀 Development Language Selection for: {selector.system_name}")
    print(f"Found {len(services)} services to configure")

    if args.config:
        # Security: Validate config file path (v3.4.0 fix - SV-01)
        try:
            config_path = sanitize_path(
                args.config,
                system_path,
                must_exist=True
            )
            config = safe_load_json(config_path, file_type_description="language configuration")
            selector.language_configuration = config
        except (PathSecurityError, FileNotFoundError) as e:
            print(f"❌ Could not load config file: {e}")
            sys.exit(1)
    else:
        # Interactive configuration
        print("\nConfiguration Options:")
        print("1. Homogeneous - All services in same language")
        print("2. Heterogeneous - Different languages per service based on requirements")
        
        if args.homogeneous:
            config_choice = "1"
        elif args.heterogeneous:
            config_choice = "2"
        else:
            config_choice = input("\nSelect configuration type (1 or 2): ").strip()
        
        if config_choice == "1":
            language, framework = selector.interactive_homogeneous_selection()
            selector.generate_configuration("homogeneous", services, 
                                           language=language, framework=framework)
        elif config_choice == "2":
            service_selections = selector.interactive_heterogeneous_selection(services)
            selector.generate_configuration("heterogeneous", services, 
                                           service_selections=service_selections)
        else:
            print("Invalid choice. Exiting.")
            sys.exit(1)
    
    # Save and display results
    selector.save_configuration()
    selector.print_summary()
    
    print("\n🎯 Next Steps:")
    print("1. Review the generated configuration")
    print("2. Set up development environments for selected languages")
    print("3. Proceed with development workflow (Dev-01-InitBootstrap.json)")


if __name__ == "__main__":
    main()