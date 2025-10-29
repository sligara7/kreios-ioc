# Language-Specific Development Templates

This directory contains templates for different programming languages and frameworks to support heterogeneous development while maintaining black-box architecture principles.

## Template Organization

### By Language
- `python/` - Python-specific templates (FastAPI, Flask, Django)
- `java/` - Java-specific templates (Spring Boot, Micronaut, Quarkus)
- `typescript/` - TypeScript templates (NestJS, Express)
- `go/` - Go templates (Gin, Echo, Fiber)
- `rust/` - Rust templates (Axum, Warp, Actix-web)
- `javascript/` - JavaScript templates (Express, Koa)
- `ruby/` - Ruby templates (Sinatra, Rails)
- `csharp/` - C# templates (ASP.NET Core)

### Template Types
Each language directory contains:
- `service_template/` - Basic service structure
- `api_template/` - HTTP API service template
- `worker_template/` - Background worker service template
- `test_template/` - Testing framework setup
- `deployment_template/` - Deployment configuration (Docker, etc.)

## Black-Box Architecture Principles

All templates maintain these principles:
1. **Interface Contract Compliance**: Services implement declared interfaces exactly
2. **Internal Encapsulation**: Service internals are completely hidden
3. **Language-Agnostic Communication**: Services communicate through standard protocols (HTTP, gRPC, message queues)
4. **Contract-First Development**: Interface specifications drive implementation

## Usage

Templates are used by the development workflow based on the language configuration:
1. Language selection tool creates `development_language_configuration.json`
2. Development workflow (Dev-01) uses this configuration to select appropriate templates
3. Templates are instantiated with service-specific information
4. Language-specific tooling and frameworks are configured

## Template Variables

Common variables across all templates:
- `{{SERVICE_NAME}}` - Service name
- `{{SERVICE_ID}}` - Service identifier
- `{{LANGUAGE}}` - Programming language
- `{{FRAMEWORK}}` - Framework name
- `{{INTERFACES}}` - Service interfaces from architecture
- `{{DEPENDENCIES}}` - Service dependencies
- `{{SYSTEM_NAME}}` - Parent system name

## Adding New Languages

To add support for a new language:
1. Create language directory under `language_templates/`
2. Add basic templates for service, API, worker, test patterns
3. Update `select_development_languages.py` with language configuration
4. Add language setup information to decision_flow.json tool reference

## Contract Testing

All language templates include contract testing setup to ensure:
- Provider services satisfy interface contracts
- Consumer services properly use interface contracts
- Cross-language service communication works correctly