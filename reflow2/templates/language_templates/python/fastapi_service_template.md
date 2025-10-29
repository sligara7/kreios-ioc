# {{SERVICE_NAME}} - Python FastAPI Service

## Service Overview
- **Service ID**: {{SERVICE_ID}}
- **Language**: Python
- **Framework**: FastAPI
- **System**: {{SYSTEM_NAME}}

## Architecture Compliance
This service implements the black-box architecture principles:
- ✅ All external communication through declared interfaces
- ✅ Internal implementation completely encapsulated
- ✅ Interface contracts are language-agnostic
- ✅ Service boundaries clearly defined

## Interface Contracts
This service implements the following interfaces:
{{#INTERFACES}}
- **{{interface_name}}** ({{interface_type}})
  - Communication Pattern: {{communication_pattern}}
  - Dependency Type: {{dependency_type}}
  - Implementation Status: {{implementation_status}}
{{/INTERFACES}}

## Development Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment tool (venv or conda)

### Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### Project Structure
```
{{SERVICE_ID}}/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── models/              # Data models
│   │   ├── __init__.py
│   │   └── {{SERVICE_ID}}_models.py
│   ├── routers/             # API route handlers
│   │   ├── __init__.py
│   │   └── {{SERVICE_ID}}_router.py
│   ├── services/            # Business logic layer
│   │   ├── __init__.py
│   │   └── {{SERVICE_ID}}_service.py
│   ├── dependencies/        # Dependency injection
│   │   ├── __init__.py
│   │   └── {{SERVICE_ID}}_deps.py
│   └── config.py           # Configuration management
├── tests/
│   ├── __init__.py
│   ├── test_{{SERVICE_ID}}.py
│   ├── test_contracts.py    # Interface contract tests
│   └── test_integration.py  # Integration tests
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
├── Dockerfile              # Container configuration
├── docker-compose.yml      # Local development setup
├── .env.example            # Environment variables template
└── README.md               # This file
```

## Running the Service

### Development Mode
```bash
# Start the service
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Service will be available at:
# - API: http://localhost:8000
# - Interactive docs: http://localhost:8000/docs
# - OpenAPI spec: http://localhost:8000/openapi.json
```

### Production Mode
```bash
# Using Docker
docker build -t {{SERVICE_ID}}:latest .
docker run -p 8000:8000 {{SERVICE_ID}}:latest

# Using Docker Compose
docker-compose up -d
```

## Testing

### Unit Tests
```bash
# Run unit tests
pytest tests/test_{{SERVICE_ID}}.py -v

# Run with coverage
pytest --cov=app tests/ --cov-report=html
```

### Contract Tests
```bash
# Verify interface contract compliance
pytest tests/test_contracts.py -v
```

### Integration Tests
```bash
# Test with other services
pytest tests/test_integration.py -v
```

## Interface Implementation

### HTTP Endpoints
{{#HTTP_INTERFACES}}
**{{interface_name}}**
- **Method**: {{method}}
- **Path**: {{path}}
- **Auth Required**: {{auth_required}}
- **Description**: {{description}}

```python
@router.{{method_lower}}("{{path}}")
async def {{interface_name}}_endpoint(
    # Add parameters based on interface specification
):
    """{{description}}"""
    # Implementation follows interface contract exactly
    pass
```
{{/HTTP_INTERFACES}}

### Service Dependencies
{{#DEPENDENCIES}}
**{{dependency_name}}**
- **Type**: {{dependency_type}}
- **Interface**: {{interface_specification}}

```python
# Dependency injection for {{dependency_name}}
async def get_{{dependency_name}}_client():
    # Client configured based on interface contract
    return {{dependency_name}}_client
```
{{/DEPENDENCIES}}

## Configuration

### Environment Variables
```bash
# Copy example environment file
cp .env.example .env

# Edit configuration
nano .env
```

Required environment variables:
- `SERVICE_NAME={{SERVICE_NAME}}`
- `SERVICE_VERSION=1.0.0`
- `LOG_LEVEL=INFO`
- `HOST=0.0.0.0`
- `PORT=8000`

### Configuration Management
Configuration is handled through Pydantic settings:

```python
# app/config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    service_name: str = "{{SERVICE_NAME}}"
    service_version: str = "1.0.0"
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8000
    
    class Config:
        env_file = ".env"
```

## Monitoring and Observability

### Health Checks
```bash
# Health check endpoint
curl http://localhost:8000/health
```

### Metrics
- Service exposes metrics at `/metrics` endpoint
- Prometheus-compatible format
- Includes request duration, error rates, and custom business metrics

### Logging
- Structured JSON logging
- Correlation IDs for request tracing
- Consistent log levels and formats

## Development Guidelines

### Code Style
- **Formatter**: Black
- **Linter**: Flake8 + Pylint
- **Type Checking**: mypy
- **Import Sorting**: isort

```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/
pylint app/ tests/

# Type checking
mypy app/
```

### Contract Compliance
1. **Interface Implementation**: All declared interfaces must be implemented exactly as specified
2. **Data Models**: Use Pydantic models that match interface contracts
3. **Error Handling**: Return errors in format specified by interface contracts
4. **Authentication**: Implement authentication as specified in interface contracts

### Testing Strategy
1. **Unit Tests**: Test business logic in isolation
2. **Contract Tests**: Verify interface compliance
3. **Integration Tests**: Test with dependent services
4. **End-to-End Tests**: Test complete user workflows

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes
- Deployment manifests available in `k8s/` directory
- Includes service, deployment, and configmap configurations
- Health checks and resource limits configured

## Troubleshooting

### Common Issues
1. **Port conflicts**: Ensure port 8000 is available
2. **Dependency issues**: Verify all services in dependency chain are running
3. **Configuration errors**: Check environment variables and .env file

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug
```

### Performance Profiling
```bash
# Install profiling tools
pip install py-spy

# Profile running service
py-spy top --pid <service-pid>
```

## Contributing

1. Ensure all interface contracts are maintained
2. Add tests for new functionality
3. Follow code style guidelines
4. Update documentation for API changes
5. Verify contract tests pass before merging