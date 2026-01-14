# KREIOS-150 IOC Testing Guide

Comprehensive guide for running and developing tests for the KREIOS-150 areaDetector IOC.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Environments](#test-environments)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
- [Docker Testing](#docker-testing)
- [Writing New Tests](#writing-new-tests)
- [CI/CD Integration](#cicd-integration)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Run All Tests Locally

```bash
# 1. Start the simulator
./scripts/start_simulator.sh

# 2. Run tests
pytest tests/ -v
```

### Run Tests in Docker

```bash
# Run against simulator only (fast)
./scripts/run_tests.sh --docker-sim

# Run full test suite including EPICS IOC tests
./scripts/run_tests.sh --docker-full
```

## Test Environments

### 1. Local Testing

**Requirements:**
- Python 3.8+
- pytest and dependencies (see `tests/requirements-test.txt`)
- Optional: pyepics for EPICS tests

**Setup:**
```bash
# Install dependencies
pip install -r tests/requirements-test.txt

# Start simulator
./scripts/start_simulator.sh

# Run tests
pytest tests/ -v
```

**Pros:**
- Fast iteration
- Easy debugging
- Direct access to logs

**Cons:**
- Requires local environment setup
- Manual simulator management

### 2. Docker Testing (Simulator Only)

**Use Case:** Testing protocol and simulator functionality without EPICS

**Command:**
```bash
./scripts/run_tests.sh --docker-sim
```

**What's Tested:**
- Protocol conformance
- Simulator state machine
- Client communication
- Data generation

**Pros:**
- No local Python setup needed
- Isolated environment
- Fast (simulator only)

**Cons:**
- No EPICS IOC testing
- Docker overhead

### 3. Docker Testing (Full Stack)

**Use Case:** Complete integration testing with EPICS IOC

**Command:**
```bash
./scripts/run_tests.sh --docker-full
```

**What's Tested:**
- Everything from simulator-only mode
- EPICS PV access via Channel Access
- IOC driver functionality
- End-to-end acquisition workflows

**Pros:**
- Complete integration testing
- Production-like environment
- All tests enabled

**Cons:**
- Slower (IOC startup ~5-10s)
- Requires more resources
- Longer build time (~15-20 min first time)

## Test Organization

### Test Files

| File | Purpose | Dependencies |
|------|---------|--------------|
| `test_protocol.py` | Protocol message format and parsing | Simulator |
| `test_simulator.py` | Simulator state machine and behavior | Simulator |
| `test_prodigy_client.py` | TCP client communication | Simulator |
| `test_acquisition.py` | Acquisition workflows (1D, 2D, 3D) | Simulator |
| `test_data_integrity.py` | Data reshaping and validation | None |
| `test_error_handling.py` | Error conditions and recovery | Simulator |
| `test_protocol_coverage.py` | Protocol v1.22 command coverage | Simulator |
| `test_ioc.py` | IOC logic and EPICS PV access | EPICS IOC |

### Test Categories

**Unit Tests** (no external dependencies):
- `test_data_integrity.py` - Data calculations
- `test_ioc.py` - Non-EPICS sections

**Integration Tests** (require simulator):
- `test_protocol.py`
- `test_simulator.py`
- `test_prodigy_client.py`
- `test_acquisition.py`
- `test_error_handling.py`
- `test_protocol_coverage.py`

**System Tests** (require EPICS IOC):
- `test_ioc.py` - EPICS-dependent sections

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_protocol.py -v

# Run specific test class
pytest tests/test_acquisition.py::TestAcquisitionWorkflow1D -v

# Run specific test function
pytest tests/test_protocol.py::test_connect_command -v

# Run with coverage
pytest tests/ --cov=sim --cov-report=html
```

### Using the Test Runner Script

The `scripts/run_tests.sh` script provides convenient test execution:

```bash
# Local testing
./scripts/run_tests.sh --local

# Docker simulator only
./scripts/run_tests.sh --docker-sim

# Docker full stack
./scripts/run_tests.sh --docker-full

# With coverage
./scripts/run_tests.sh --docker-full --coverage

# Rebuild images first
./scripts/run_tests.sh --docker-full --build

# Clean and rebuild
./scripts/run_tests.sh --docker-full --clean --build

# Pass pytest arguments
./scripts/run_tests.sh --docker-sim tests/test_protocol.py -v -k "test_connect"
```

### Filtering Tests

```bash
# Run tests matching pattern
pytest tests/ -k "1d" -v

# Run tests by marker (if configured)
pytest tests/ -m "slow" -v

# Skip slow tests
pytest tests/ -m "not slow" -v
```

## Docker Testing

### Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Simulator   │────▶│   IOC        │────▶│  Test Runner │
│  (Python)    │     │  (C++/EPICS) │     │  (pytest)    │
│  Port 7010   │     │  PVs: 5064/5 │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
       │                     │                     │
       └─────────────────────┴─────────────────────┘
                  Docker Network: kreios-net
```

### Environment Variables

Tests automatically detect and use these environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `SIMULATOR_HOST` | localhost | Simulator hostname |
| `SIMULATOR_PORT` | 7010 | Simulator port |
| `USE_EXTERNAL_SIMULATOR` | 0 | Set to 1 to use running simulator |
| `EPICS_CA_ADDR_LIST` | localhost | EPICS CA server address |
| `EPICS_IOC_PREFIX` | KREIOS:cam1: | PV prefix |
| `EPICS_IOC_AVAILABLE` | 0 | Set to 1 to enable IOC tests |

### Manual Docker Testing

```bash
cd docker

# Start simulator
docker compose up simulator -d

# Check simulator is running
docker compose logs simulator

# Run specific tests
docker compose --profile test run --rm test pytest tests/test_protocol.py -v

# Stop services
docker compose down
```

### Docker Compose Profiles

- **Default** - Simulator only
- **`--profile full`** - Simulator + IOC
- **`--profile test`** - Test runner

## Writing New Tests

### Test Template

```python
"""
Test module for [feature description].

Tests:
- [Test case 1]
- [Test case 2]
"""

import pytest

def test_feature_basic(client):
    """Test basic [feature] functionality."""
    # Arrange
    params = {"StartEnergy": 400.0, "EndEnergy": 410.0}

    # Act
    response = client.send_command("CommandName", params)

    # Assert
    assert "OK" in response
    assert some_condition

def test_feature_error_handling(client):
    """Test [feature] error handling."""
    # Test error conditions
    response = client.send_command("CommandName", invalid_params)
    assert "Error" in response
```

### Available Fixtures

#### `simulator` (function scope)
Starts and stops the simulator for each test.

```python
def test_example(simulator):
    # Simulator is running
    assert simulator.process is not None
```

#### `client` (function scope)
Provides a connected TCP client.

```python
def test_example(client):
    response = client.send_command("Connect")
    assert "OK" in response
```

#### `unconnected_client`
Provides an unconnected client for connection tests.

```python
def test_connection(unconnected_client):
    unconnected_client.connect()
    # Test connection behavior
```

#### `spectrum_params_1d`, `spectrum_params_2d`, `spectrum_params_3d`
Standard test parameters for different dimensionalities.

```python
def test_1d_acquisition(client, spectrum_params_1d):
    client.send_command("DefineSpectrumFAT", spectrum_params_1d)
    # Continue with acquisition
```

#### `wait_for_complete_func`
Helper function to wait for acquisition completion.

```python
def test_acquisition(client, wait_for_complete_func):
    client.send_command("Start")
    response = wait_for_complete_func(client, timeout=30.0)
    assert "finished" in response.lower()
```

### Testing Best Practices

1. **Use descriptive test names**
   ```python
   # Good
   def test_1d_spectrum_integration_over_detector_pixels():

   # Bad
   def test_integration():
   ```

2. **Follow AAA pattern** (Arrange, Act, Assert)
   ```python
   def test_example():
       # Arrange - Set up test data
       params = {"StartEnergy": 400.0}

       # Act - Execute the test
       response = client.send_command("Command", params)

       # Assert - Verify results
       assert "OK" in response
   ```

3. **Test one thing per test**
   - Keep tests focused
   - Make failures easy to diagnose

4. **Use parametrize for multiple cases**
   ```python
   @pytest.mark.parametrize("energy,expected", [
       (400.0, 21),
       (500.0, 101),
   ])
   def test_energy_samples(energy, expected):
       # Test implementation
       pass
   ```

5. **Clean up resources**
   - Use fixtures for setup/teardown
   - Disconnect clients after use

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test-simulator:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build simulator image
        run: |
          cd docker
          docker compose build simulator test

      - name: Run tests
        run: |
          ./scripts/run_tests.sh --docker-sim -v --tb=short

  test-full:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build all images
        run: |
          cd docker
          docker compose --profile full build

      - name: Run full test suite
        run: |
          ./scripts/run_tests.sh --docker-full -v --tb=short
```

### Local Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running tests before commit..."
./scripts/run_tests.sh --docker-sim -v --tb=short

if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi
```

## Troubleshooting

### Simulator Won't Start

**Symptom:** Tests fail with "Simulator not accessible"

**Solutions:**
1. Check if port 7010 is already in use:
   ```bash
   lsof -i :7010
   # or
   netstat -an | grep 7010
   ```

2. Ensure `sim/parameters.dat` exists:
   ```bash
   ls -la sim/parameters.dat
   ```

3. Check simulator logs:
   ```bash
   docker compose logs simulator
   ```

### EPICS IOC Tests Skipped

**Symptom:** IOC tests show "SKIPPED: KREIOS IOC not running"

**Solutions:**
1. Ensure IOC is running:
   ```bash
   docker compose --profile full ps
   ```

2. Set environment variable:
   ```bash
   export EPICS_IOC_AVAILABLE=1
   ```

3. Check IOC logs for errors:
   ```bash
   docker compose logs ioc
   ```

### Tests Timeout

**Symptom:** Tests hang or timeout

**Solutions:**
1. Increase timeout in test:
   ```python
   wait_for_complete_func(client, timeout=60.0)  # Increase from 30
   ```

2. Check network connectivity:
   ```bash
   docker network inspect kreios-ioc_kreios-net
   ```

3. Verify services are healthy:
   ```bash
   docker compose ps
   docker compose logs
   ```

### Import Errors

**Symptom:** `ModuleNotFoundError` when running tests

**Solutions:**
1. Install test dependencies:
   ```bash
   pip install -r tests/requirements-test.txt
   ```

2. Run from project root:
   ```bash
   cd /path/to/kreios_ioc
   pytest tests/
   ```

3. Check PYTHONPATH:
   ```bash
   export PYTHONPATH=/path/to/kreios_ioc:$PYTHONPATH
   ```

### Docker Build Failures

**Symptom:** Docker build fails or takes too long

**Solutions:**
1. Increase Docker memory:
   - Docker Desktop → Settings → Resources → Memory → 4GB+

2. Use BuildKit:
   ```bash
   DOCKER_BUILDKIT=1 docker compose build
   ```

3. Check disk space:
   ```bash
   df -h
   docker system df
   ```

4. Clean up old images:
   ```bash
   docker system prune -a
   ```

## Additional Resources

- [Test Suite README](README.md) - Test organization and fixtures
- [Docker README](../docker/README.md) - Docker setup and configuration
- [VERSION_NOTES](../docker/VERSION_NOTES.md) - areaDetector version information
- [Protocol Specification](../Documentation/SpecsLab_Prodigy_RemoteIn.md) - Protocol details

## Getting Help

1. Check test output carefully - pytest provides detailed failure information
2. Use `-vv` for very verbose output: `pytest tests/ -vv`
3. Use `--tb=long` for full tracebacks: `pytest tests/ --tb=long`
4. Check simulator/IOC logs when tests fail
5. Run single tests in isolation to diagnose issues
