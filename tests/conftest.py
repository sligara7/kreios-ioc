"""
Pytest fixtures for KREIOS-150 IOC testing.

Provides shared fixtures for:
- Prodigy simulator server management
- TCP client connections
- Test data generators

Environment Variables:
- SIMULATOR_HOST: Hostname for simulator (default: localhost)
- SIMULATOR_PORT: Port for simulator (default: 7010)
- USE_EXTERNAL_SIMULATOR: If "1", don't start local simulator
- EPICS_IOC_PREFIX: PV prefix for EPICS IOC tests (default: KREIOS:cam1:)
"""

import asyncio
import os
import socket
import subprocess
import sys
import time
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

# Add project paths to import from
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "sim"))

# Configuration from environment variables (for Docker support)
SIMULATOR_HOST = os.environ.get("SIMULATOR_HOST", "localhost")
SIMULATOR_PORT = int(os.environ.get("SIMULATOR_PORT", "7010"))
USE_EXTERNAL_SIMULATOR = os.environ.get("USE_EXTERNAL_SIMULATOR", "0") == "1"
EPICS_IOC_PREFIX = os.environ.get("EPICS_IOC_PREFIX", "KREIOS:cam1:")


# ============================================================================
# Simulator Fixtures
# ============================================================================

class SimulatorProcess:
    """Manager for the Prodigy simulator subprocess."""

    def __init__(self, host=None, port=None):
        self.host = host or SIMULATOR_HOST
        self.port = port or SIMULATOR_PORT
        self.process = None
        self._original_dir = None
        self._external = USE_EXTERNAL_SIMULATOR

    def start(self, timeout=5.0):
        """Start the simulator subprocess (or verify external simulator is running)."""
        if self._external:
            # Using external simulator (e.g., in Docker)
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self._is_port_open():
                    return True
                time.sleep(0.1)
            raise RuntimeError(
                f"External simulator at {self.host}:{self.port} not responding"
            )

        # Start local simulator
        sim_path = PROJECT_ROOT / "sim"
        self._original_dir = os.getcwd()
        os.chdir(sim_path)

        self.process = subprocess.Popen(
            [sys.executable, "ProdigySimServer.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(sim_path),
        )

        # Wait for server to be ready
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._is_port_open():
                return True
            time.sleep(0.1)

        self.stop()
        raise RuntimeError(f"Simulator failed to start within {timeout}s")

    def stop(self):
        """Stop the simulator subprocess."""
        if self._external:
            # External simulator - nothing to stop
            return

        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

        if self._original_dir:
            os.chdir(self._original_dir)

    def _is_port_open(self):
        """Check if the simulator port is accepting connections."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except Exception:
            return False


@pytest.fixture(scope="function")
def simulator():
    """
    Fixture that starts the Prodigy simulator for each test.

    Yields the SimulatorProcess instance.
    Automatically stops simulator after test.
    """
    sim = SimulatorProcess()
    sim.start()
    yield sim
    sim.stop()


@pytest.fixture(scope="module")
def simulator_module():
    """
    Module-scoped simulator fixture for tests that need long-running simulator.
    """
    sim = SimulatorProcess()
    sim.start()
    yield sim
    sim.stop()


# ============================================================================
# TCP Client Fixtures
# ============================================================================

class ProdigyTestClient:
    """Synchronous TCP client for protocol testing."""

    def __init__(self, host=None, port=None):
        self.host = host or SIMULATOR_HOST
        self.port = port or SIMULATOR_PORT
        self.sock = None
        self.request_counter = 0

    def connect(self, timeout=5.0):
        """Connect to the simulator."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((self.host, self.port))

    def disconnect(self):
        """Disconnect from server."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def send_command(self, command, params=None, timeout=10.0):
        """
        Send a command and return the response.

        Args:
            command: Command name (e.g., "Connect")
            params: Dict of parameters
            timeout: Response timeout in seconds

        Returns:
            Response string
        """
        if not self.sock:
            raise RuntimeError("Not connected")

        # Build request
        self.request_counter = (self.request_counter + 1) % 10000
        req_id = f"{self.request_counter:04X}"

        request = f"?{req_id} {command}"
        if params:
            for key, value in params.items():
                if isinstance(value, str) and " " in value:
                    request += f' {key}:"{value}"'
                else:
                    request += f" {key}:{value}"
        request += "\n"

        # Send
        self.sock.sendall(request.encode("utf-8"))

        # Receive
        self.sock.settimeout(timeout)
        response = self.sock.recv(65536).decode("utf-8").strip()

        return response

    def send_raw(self, raw_message, timeout=10.0):
        """Send a raw message string (for protocol testing)."""
        if not self.sock:
            raise RuntimeError("Not connected")

        self.sock.sendall(raw_message.encode("utf-8"))
        self.sock.settimeout(timeout)

        try:
            response = self.sock.recv(65536).decode("utf-8").strip()
            return response
        except socket.timeout:
            return None


@pytest.fixture
def client(simulator):
    """
    Fixture that provides a connected test client.

    Depends on simulator fixture.
    Automatically connects and disconnects.
    """
    client = ProdigyTestClient()
    client.connect()
    yield client

    # Cleanup: Ensure proper state reset between tests
    try:
        # Abort any running acquisition
        client.send_command("Abort", timeout=1.0)
    except Exception:
        pass  # May fail if no acquisition running

    try:
        # Give acquisition thread time to fully terminate
        time.sleep(0.2)
    except Exception:
        pass

    try:
        # Disconnect cleanly
        client.send_command("Disconnect", timeout=1.0)
    except Exception:
        pass  # May fail if already disconnected

    client.disconnect()


@pytest.fixture
def unconnected_client(simulator):
    """
    Fixture that provides an unconnected client (for connection tests).
    """
    client = ProdigyTestClient()
    yield client
    client.disconnect()


# ============================================================================
# Async Client Fixtures (for IOC testing)
# ============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def spectrum_params_1d():
    """Standard 1D spectrum parameters."""
    return {
        "StartEnergy": 400.0,
        "EndEnergy": 410.0,
        "StepWidth": 0.5,
        "DwellTime": 0.1,
        "PassEnergy": 20.0,
        "LensMode": "HighMagnification",
        "ScanRange": "MediumArea",
        "ValuesPerSample": 1,
        "NumberOfSlices": 1,
    }


@pytest.fixture
def spectrum_params_2d():
    """Standard 2D spectrum parameters (energy x detector pixels)."""
    return {
        "StartEnergy": 400.0,
        "EndEnergy": 410.0,
        "StepWidth": 0.5,
        "DwellTime": 0.1,
        "PassEnergy": 20.0,
        "LensMode": "HighMagnification",
        "ScanRange": "MediumArea",
        "ValuesPerSample": 128,  # Detector pixels
        "NumberOfSlices": 1,
    }


@pytest.fixture
def spectrum_params_3d():
    """Standard 3D spectrum parameters (slices x energy x pixels)."""
    return {
        "StartEnergy": 400.0,
        "EndEnergy": 410.0,
        "StepWidth": 0.5,
        "DwellTime": 0.1,
        "PassEnergy": 20.0,
        "LensMode": "HighMagnification",
        "ScanRange": "MediumArea",
        "ValuesPerSample": 64,  # Detector pixels
        "NumberOfSlices": 5,  # Depth slices
    }


@pytest.fixture
def expected_num_samples():
    """Expected number of energy samples for default params (400-410, step 0.5)."""
    return 21  # (410 - 400) / 0.5 + 1


# ============================================================================
# Helper Functions
# ============================================================================

def parse_response(response):
    """
    Parse a Prodigy protocol response.

    Args:
        response: Response string like "!0001 OK: Param1:value1 Param2:value2"

    Returns:
        dict with 'id', 'status', 'params', 'error_code', 'error_message'
    """
    result = {
        "id": None,
        "status": None,
        "params": {},
        "error_code": None,
        "error_message": None,
    }

    if not response or not response.startswith("!"):
        return result

    # Extract ID
    result["id"] = response[1:5]

    # Check for error
    if " Error:" in response:
        result["status"] = "Error"
        error_part = response.split(" Error:")[1]
        parts = error_part.split(" ", 1)
        result["error_code"] = int(parts[0])
        if len(parts) > 1:
            result["error_message"] = parts[1]
        return result

    # Parse OK response
    if " OK" in response:
        result["status"] = "OK"

        # Check for parameters after OK:
        if " OK:" in response:
            param_part = response.split(" OK:")[1].strip()
            # Parse key:value pairs (simplified parsing)
            tokens = param_part.split()
            i = 0
            while i < len(tokens):
                token = tokens[i]
                if ":" in token:
                    key, value = token.split(":", 1)
                    # Handle quoted values
                    if value.startswith('"') and not value.endswith('"'):
                        while i + 1 < len(tokens) and not tokens[i].endswith('"'):
                            i += 1
                            value += " " + tokens[i]
                    result["params"][key] = value.strip('"')
                i += 1

    return result


def wait_for_acquisition_complete(client, timeout=30.0, poll_interval=0.5):
    """
    Wait for acquisition to complete.

    Args:
        client: ProdigyTestClient instance
        timeout: Maximum wait time
        poll_interval: Time between status polls

    Returns:
        Final status response
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = client.send_command("GetAcquisitionStatus")
        if "finished" in response.lower() or "aborted" in response.lower():
            return response
        time.sleep(poll_interval)
    raise TimeoutError(f"Acquisition did not complete within {timeout}s")


@pytest.fixture
def parse_response_func():
    """Fixture providing the parse_response helper function."""
    return parse_response


@pytest.fixture
def wait_for_complete_func():
    """Fixture providing the wait_for_acquisition_complete helper function."""
    return wait_for_acquisition_complete
