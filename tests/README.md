# KREIOS-150 IOC Test Suite

Comprehensive test suite for the KREIOS-150 areaDetector IOC and SpecsLab Prodigy Remote In protocol simulator.

## Quick Start

```bash
# Install test dependencies
pip install -r tests/requirements-test.txt

# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_protocol.py -v

# Run with coverage report
pytest tests/ --cov=sim --cov-report=html
```

## Test Organization

| File | Description |
|------|-------------|
| `conftest.py` | Shared fixtures for simulator, clients, and test data |
| `test_protocol.py` | Protocol conformance tests (message format, commands) |
| `test_prodigy_client.py` | Tests for TCP client functionality with simulator |
| `test_simulator.py` | Tests for ProdigySimServer (state machine, data generation) |
| `test_acquisition.py` | Acquisition workflow tests (1D, 2D, 3D) |
| `test_data_integrity.py` | Data reshaping and integrity tests |
| `test_error_handling.py` | Error condition and recovery tests |
| `test_ioc.py` | Logic tests (calculations, constants, data reshaping) |
| `test_protocol_coverage.py` | Protocol command coverage tests (v1.22) |

## Test Categories

### Protocol Tests (`test_protocol.py`)
- Request/response message format validation
- Command parsing and routing
- Parameter encoding/decoding
- Error code handling

### Client Tests (`test_prodigy_client.py`)
- Connection management
- Command formatting and sending
- Response parsing
- Data array parsing
- 1D, 2D, 3D acquisition workflows

### Simulator Tests (`test_simulator.py`)
- Server startup and shutdown
- Single-client enforcement
- State machine transitions
- Data generation quality

### Acquisition Tests (`test_acquisition.py`)
- 1D spectrum workflow (standard XPS/UPS)
- 2D image workflow (angle-resolved / imaging)
- 3D volume workflow (depth profiling)
- Real-time polling patterns
- Pause/resume/abort handling

### Data Integrity Tests (`test_data_integrity.py`)
- Flat-to-N-D reshaping correctness
- Index calculation verification
- Energy axis calculation
- Chunked data retrieval consistency

### Error Handling Tests (`test_error_handling.py`)
- Connection failures and recovery
- Invalid parameter handling
- State violation handling
- Timeout recovery

### IOC Logic Tests (`test_ioc.py`)
- Data array size calculations
- Energy axis generation
- Data reshaping logic (1D/2D/3D integration)
- Simulated data generation formulas
- Parameter validation ranges
- Protocol enumeration strings

### Protocol Coverage Tests (`test_protocol_coverage.py`)
- Verifies all 46 commands from Prodigy Remote In v1.22 are recognized
- Tests core acquisition workflow commands
- Validates protocol version compatibility

## Running Specific Test Classes

```bash
# Run only acquisition workflow tests
pytest tests/test_acquisition.py::TestAcquisitionWorkflow1D -v

# Run only 2D tests
pytest tests/test_acquisition.py::TestAcquisitionWorkflow2D -v

# Run only 3D tests
pytest tests/test_acquisition.py::TestAcquisitionWorkflow3D -v

# Run error handling tests
pytest tests/test_error_handling.py -v

# Run protocol coverage tests
pytest tests/test_protocol_coverage.py -v
```

## Fixtures

The test suite provides several reusable fixtures:

### `simulator`
Starts and manages the Prodigy simulator subprocess. Automatically starts before each test and stops after.

```python
def test_example(simulator):
    # Simulator is running on localhost:7010
    assert simulator.process is not None
```

### `client`
Provides a connected TCP test client.

```python
def test_example(client):
    response = client.send_command("Connect")
    assert "OK" in response
```

### `spectrum_params_1d`, `spectrum_params_2d`, `spectrum_params_3d`
Provide standard test parameters for different data dimensionalities.

```python
def test_example(client, spectrum_params_2d):
    client.send_command("DefineSpectrumFAT", spectrum_params_2d)
```

### `wait_for_complete_func`
Helper function to wait for acquisition completion.

```python
def test_example(client, wait_for_complete_func):
    client.send_command("Start")
    response = wait_for_complete_func(client, timeout=30.0)
    assert "finished" in response.lower()
```

## Data Dimensionality Testing

The test suite thoroughly covers all three data dimensionalities:

### 1D Spectrum
- Shape: `(n_samples,)`
- Parameters: `ValuesPerSample=1, NumberOfSlices=1`
- Use case: Standard XPS/UPS spectroscopy

### 2D Image
- Shape: `(n_samples, n_pixels)`
- Parameters: `ValuesPerSample=N, NumberOfSlices=1`
- Use case: Angle-resolved spectroscopy, imaging detector

### 3D Volume
- Shape: `(n_slices, n_samples, n_pixels)`
- Parameters: `ValuesPerSample=N, NumberOfSlices=M`
- Use case: Depth profiling, multi-region scanning

## Index Calculation Reference

For flat data arrays, the index formula is:
```
index = slice * (S * V) + sample * V + pixel

Where:
  S = number of samples (energy points)
  V = values per sample (detector pixels)
```

## Protocol Reference

The tests are based on SpecsLab Prodigy Remote In protocol v1.22 (September 2024).
See `Documentation/SpecsLab_Prodigy_RemoteIn.md` for full protocol specification.

### Core Commands Tested
- Connection: `Connect`, `Disconnect`
- Spectrum Definition: `DefineSpectrumFAT`, `DefineSpectrumSFAT`, `DefineSpectrumFRR`, `DefineSpectrumFE`, `DefineSpectrumLVS`
- Acquisition: `ValidateSpectrum`, `Start`, `Pause`, `Resume`, `Abort`
- Status/Data: `GetAcquisitionStatus`, `GetAcquisitionData`, `ClearSpectrum`
- Parameters: `GetAllAnalyzerParameterNames`, `GetAnalyzerVisibleName`, etc.

## Troubleshooting

### Simulator won't start
- Check if port 7010 is already in use: `lsof -i :7010`
- Ensure `sim/parameters.dat` exists

### Tests timing out
- Increase timeout in `wait_for_complete_func` calls
- Check simulator logs for errors
- Verify network connectivity to localhost

### Import errors
- Install dependencies: `pip install -r tests/requirements-test.txt`
- Ensure you're running from the project root

## Coverage

To generate a coverage report:

```bash
pytest tests/ --cov=sim --cov-report=html
open htmlcov/index.html
```

## Continuous Integration

These tests are designed to run in CI environments:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r tests/requirements-test.txt
    pytest tests/ -v --tb=short
```
