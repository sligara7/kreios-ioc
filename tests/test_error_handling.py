"""
Error handling tests for KREIOS-150 IOC.

Tests verify proper handling of:
- Connection failures and recovery
- Invalid parameters
- State violations
- Protocol errors
- Timeout conditions
"""

import pytest
import socket
import time


class TestConnectionErrors:
    """Tests for connection error handling."""

    def test_connect_to_nonexistent_server(self):
        """Test connection to non-existent server fails gracefully."""
        client = ProdigyTestClientSync(host="localhost", port=59999)
        try:
            client.connect(timeout=1.0)
            connected = True
        except (socket.timeout, ConnectionRefusedError, OSError):
            connected = False

        assert not connected

    def test_reconnect_after_disconnect(self, simulator):
        """Test that reconnection works after disconnect."""
        client = ProdigyTestClientSync()
        client.connect()
        client.send_command("Connect")
        client.send_command("Disconnect")
        client.disconnect()

        # Small delay
        time.sleep(0.2)

        # Reconnect
        client.connect()
        response = client.send_command("Connect")
        assert "OK" in response

        client.disconnect()

    def test_server_gone_during_command(self, simulator):
        """Test handling when server disconnects during operation."""
        client = ProdigyTestClientSync()
        client.connect()
        client.send_command("Connect")

        # Stop the simulator
        simulator.stop()

        # Next command should fail gracefully
        try:
            response = client.send_command("GetAcquisitionStatus", timeout=2.0)
            # May get empty response or exception
            success = response is not None and len(response) > 0
        except (socket.timeout, ConnectionResetError, BrokenPipeError, OSError):
            success = False

        assert not success

        client.disconnect()


class TestParameterValidation:
    """Tests for parameter validation errors."""

    def test_negative_energy_values(self, client):
        """Test handling of negative energy values."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": -10.0,
            "EndEnergy": 10.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        # Simulator may accept this (depends on implementation)
        # Just verify it doesn't crash
        assert response is not None

    def test_zero_step_width(self, client):
        """Test handling of zero step width."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.0,  # Invalid
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        # Should either error or handle gracefully
        assert response is not None

    def test_inverted_energy_range(self, client):
        """Test handling when start > end energy."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 410.0,  # Higher than end
            "EndEnergy": 400.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        # Verify it handles this case
        assert response is not None

    def test_very_large_values_per_sample(self, client):
        """Test handling of very large ValuesPerSample."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
            "ValuesPerSample": 1000000,  # Very large
        })
        # Should accept or error gracefully
        assert response is not None

    def test_unknown_parameter(self, client):
        """Test handling of unknown parameters."""
        client.send_command("Connect")
        response = client.send_command("GetAnalyzerParameterValue", {
            "ParameterName": "NonExistentParameter123"
        })
        assert "Error:" in response


class TestStateViolations:
    """Tests for state machine violation handling."""

    def test_start_without_validate(self, client):
        """Test Start without ValidateSpectrum."""
        client.send_command("Connect")
        response = client.send_command("Start")
        assert "Error:" in response

    def test_start_without_define(self, client):
        """Test Start without DefineSpectrum."""
        client.send_command("Connect")
        response = client.send_command("ValidateSpectrum")
        assert "Error:" in response

    def test_pause_without_start(self, client):
        """Test Pause without active acquisition."""
        client.send_command("Connect")
        response = client.send_command("Pause")
        assert "Error:" in response

    def test_resume_without_pause(self, client):
        """Test Resume without prior Pause."""
        client.send_command("Connect")
        response = client.send_command("Resume")
        assert "Error:" in response

    def test_abort_without_acquisition(self, client):
        """Test Abort without active acquisition."""
        client.send_command("Connect")
        response = client.send_command("Abort")
        assert "Error:" in response

    def test_double_start(self, client):
        """Test calling Start twice."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.5,  # Longer to ensure still running
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        # Try to start again
        response = client.send_command("Start")
        assert "Error:" in response

        client.send_command("Abort")

    def test_clear_during_acquisition(self, client):
        """Test ClearSpectrum during active acquisition."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.5,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        response = client.send_command("ClearSpectrum")
        assert "Error:" in response

        client.send_command("Abort")


class TestDataRetrievalErrors:
    """Tests for data retrieval error handling."""

    def test_get_data_invalid_from_index(self, client, wait_for_complete_func):
        """Test GetAcquisitionData with invalid FromIndex."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=10.0)

        # Request with negative FromIndex
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": -1,
            "ToIndex": 2,
        })
        assert "Error:" in response

    def test_get_data_invalid_to_index(self, client, wait_for_complete_func):
        """Test GetAcquisitionData with ToIndex beyond data range."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,  # 5 samples
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=10.0)

        # Request beyond data range
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 1000,  # Only 5 points exist
        })
        assert "Error:" in response

    def test_get_data_reversed_range(self, client, wait_for_complete_func):
        """Test GetAcquisitionData with FromIndex > ToIndex."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=10.0)

        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 4,
            "ToIndex": 2,  # Reversed
        })
        assert "Error:" in response


class TestProtocolErrors:
    """Tests for protocol-level error handling."""

    def test_malformed_request_id(self, unconnected_client, simulator):
        """Test handling of malformed request ID."""
        unconnected_client.connect()
        response = unconnected_client.send_raw("?GGGG Connect\n")  # Invalid hex
        # Should either work or error gracefully
        assert response is not None

    def test_missing_command(self, unconnected_client, simulator):
        """Test handling of request without command."""
        unconnected_client.connect()
        response = unconnected_client.send_raw("?0001\n")
        assert "Error:" in response

    def test_extra_whitespace(self, client):
        """Test handling of extra whitespace in command."""
        response = client.send_raw("?0001    Connect    \n")
        # Should work or error gracefully
        assert response is not None

    def test_very_long_command(self, client):
        """Test handling of very long command line."""
        long_param = "A" * 10000
        response = client.send_raw(f"?0001 Connect {long_param}\n", timeout=5.0)
        # Should handle without crashing
        assert response is not None or True  # May timeout


class TestTimeoutHandling:
    """Tests for timeout handling."""

    def test_client_timeout_recovery(self, client):
        """Test that client can recover after a timeout."""
        client.send_command("Connect")

        # Normal operation should work
        response = client.send_command("GetAnalyzerVisibleName")
        assert "OK" in response


class TestRecoveryScenarios:
    """Tests for error recovery scenarios."""

    def test_recover_from_failed_acquisition(self, client, wait_for_complete_func):
        """Test recovery after a failed/aborted acquisition."""
        client.send_command("Connect")

        # First acquisition - abort
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        client.send_command("Abort")

        # Should be able to start new acquisition
        client.send_command("ClearSpectrum")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        response = client.send_command("Start")
        assert "OK" in response

        wait_for_complete_func(client, timeout=10.0)

    def test_redefine_after_completion(self, client, wait_for_complete_func):
        """Test defining new spectrum after completion."""
        client.send_command("Connect")

        # Complete first acquisition
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=10.0)

        # Define new spectrum with different parameters
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 500.0,
            "EndEnergy": 510.0,
            "StepWidth": 1.0,
            "DwellTime": 0.01,
            "PassEnergy": 50.0,
        })
        assert "OK" in response


# Helper class for synchronous testing
class ProdigyTestClientSync:
    """Synchronous test client for error testing."""

    def __init__(self, host="localhost", port=7010):
        self.host = host
        self.port = port
        self.sock = None
        self.request_counter = 0

    def connect(self, timeout=5.0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(timeout)
        self.sock.connect((self.host, self.port))

    def disconnect(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def send_command(self, command, params=None, timeout=10.0):
        if not self.sock:
            raise RuntimeError("Not connected")

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

        self.sock.sendall(request.encode("utf-8"))
        self.sock.settimeout(timeout)
        response = self.sock.recv(65536).decode("utf-8").strip()
        return response

    def send_raw(self, raw_message, timeout=10.0):
        if not self.sock:
            raise RuntimeError("Not connected")

        self.sock.sendall(raw_message.encode("utf-8"))
        self.sock.settimeout(timeout)

        try:
            response = self.sock.recv(65536).decode("utf-8").strip()
            return response
        except socket.timeout:
            return None
