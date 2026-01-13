"""
Tests for Prodigy protocol client functionality.

Tests TCP client functionality:
- Connection management
- Command formatting and sending
- Response parsing
- Data array parsing

Note: These tests use the synchronous ProdigyTestClient from conftest.py
to test protocol interactions with the simulator.
"""

import pytest
import socket
from conftest import ProdigyTestClient, parse_response


class TestClientConnection:
    """Tests for client connection management."""

    def test_connect_to_simulator(self, simulator):
        """Test successful connection to simulator."""
        client = ProdigyTestClient()
        client.connect()

        assert client.sock is not None

        client.disconnect()

    def test_connect_to_invalid_host_fails(self):
        """Test connection to invalid host fails gracefully."""
        client = ProdigyTestClient(host="invalid.host.example.com", port=7010)
        try:
            client.connect(timeout=1.0)
            connected = True
        except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
            connected = False

        assert not connected

    def test_connect_to_closed_port_fails(self):
        """Test connection to closed port fails gracefully."""
        client = ProdigyTestClient(host="localhost", port=59999)
        try:
            client.connect(timeout=1.0)
            connected = True
        except (socket.timeout, ConnectionRefusedError, OSError):
            connected = False

        assert not connected

    def test_disconnect_clears_state(self, simulator):
        """Test disconnect clears connection state."""
        client = ProdigyTestClient()
        client.connect()
        assert client.sock is not None

        client.disconnect()
        assert client.sock is None

    def test_disconnect_when_not_connected(self):
        """Test disconnect when not connected doesn't error."""
        client = ProdigyTestClient()
        client.disconnect()  # Should not raise


class TestClientCommands:
    """Tests for client command sending."""

    def test_send_command_basic(self, client):
        """Test sending a basic command."""
        response = client.send_command("Connect")
        assert response is not None
        assert "OK" in response

    def test_send_command_get_analyzer_name(self, client):
        """Test getting analyzer visible name."""
        client.send_command("Connect")
        response = client.send_command("GetAnalyzerVisibleName")
        assert response is not None
        assert "OK" in response

    def test_send_command_with_params(self, client):
        """Test sending command with parameters."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        assert response is not None
        assert "OK" in response

    def test_send_command_increments_counter(self, client):
        """Test that request counter increments."""
        initial_counter = client.request_counter
        client.send_command("Connect")
        assert client.request_counter == initial_counter + 1

        client.send_command("GetAnalyzerVisibleName")
        assert client.request_counter == initial_counter + 2


class TestDataParsing:
    """Tests for response data parsing."""

    def test_parse_response_ok(self):
        """Test parsing OK response."""
        response = "!0001 OK"
        result = parse_response(response)

        assert result["status"] == "OK"
        assert result["id"] == "0001"

    def test_parse_response_with_params(self):
        """Test parsing response with parameters."""
        response = "!0001 OK: Name:KREIOS-150 Version:1.22"
        result = parse_response(response)

        assert result["status"] == "OK"
        assert "Name" in result["params"]
        assert result["params"]["Name"] == "KREIOS-150"

    def test_parse_response_error(self):
        """Test parsing error response."""
        response = "!0001 Error:100 Invalid command"
        result = parse_response(response)

        assert result["status"] == "Error"
        assert result["error_code"] == 100

    def test_parse_data_array(self):
        """Test parsing data array from response."""
        response = "!0001 OK: Data:[1.0,2.5,3.7,4.2,5.0]"

        # Extract data array
        if "Data:[" in response:
            data_str = response.split("Data:[")[1].split("]")[0]
            data = [float(x) for x in data_str.split(",")]
        else:
            data = []

        assert len(data) == 5
        assert data[0] == 1.0
        assert data[1] == 2.5
        assert data[4] == 5.0

    def test_parse_empty_data_array(self):
        """Test parsing empty data array."""
        response = "!0001 OK: Data:[]"

        if "Data:[" in response:
            data_str = response.split("Data:[")[1].split("]")[0]
            data = [float(x) for x in data_str.split(",") if x]
        else:
            data = []

        assert data == []

    def test_parse_large_data_array(self):
        """Test parsing large data array."""
        # Create response with 1000 values
        values = [f"{i * 1.5:.6f}" for i in range(1000)]
        response = f"!0001 OK: Data:[{','.join(values)}]"

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]

        assert len(data) == 1000
        assert data[0] == 0.0
        assert abs(data[999] - 999 * 1.5) < 1e-6


class TestAcquisitionWorkflows:
    """Integration tests using the synchronous client with simulator."""

    def test_full_1d_acquisition_workflow(self, client, wait_for_complete_func):
        """Test complete 1D acquisition workflow."""
        # Connect
        response = client.send_command("Connect")
        assert "OK" in response

        # Define spectrum
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        assert "OK" in response

        # Validate
        response = client.send_command("ValidateSpectrum")
        assert "OK" in response

        # Start
        response = client.send_command("Start")
        assert "OK" in response

        # Wait for completion
        wait_for_complete_func(client, timeout=30.0)

        # Get data (5 samples)
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 4,
        })
        assert "Data:[" in response

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]
        assert len(data) == 5

    def test_2d_acquisition(self, client, wait_for_complete_func):
        """Test 2D acquisition with ValuesPerSample > 1."""
        client.send_command("Connect")

        # Define 2D spectrum (5 energy steps x 10 pixels)
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
            "ValuesPerSample": 10,
        })
        assert "OK" in response

        response = client.send_command("ValidateSpectrum")
        assert "OK" in response

        response = client.send_command("Start")
        assert "OK" in response

        wait_for_complete_func(client, timeout=30.0)

        # Should have 5 samples x 10 pixels = 50 values
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 49,
        })
        assert "Data:[" in response

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]
        assert len(data) == 50

    def test_3d_acquisition(self, client, wait_for_complete_func):
        """Test 3D acquisition with NumberOfSlices > 1."""
        client.send_command("Connect")

        # Define 3D spectrum (3 slices x 5 energy steps x 10 pixels)
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
            "ValuesPerSample": 10,
            "NumberOfSlices": 3,
        })
        assert "OK" in response

        response = client.send_command("ValidateSpectrum")
        assert "OK" in response

        response = client.send_command("Start")
        assert "OK" in response

        wait_for_complete_func(client, timeout=60.0)

        # Should have 3 slices x 5 samples x 10 pixels = 150 values
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 149,
        })
        assert "Data:[" in response

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]
        assert len(data) == 150

    def test_pause_resume_workflow(self, client):
        """Test pause and resume during acquisition."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.5,  # Longer for pause test
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        # Pause
        response = client.send_command("Pause")
        assert "OK" in response

        # Check status
        response = client.send_command("GetAcquisitionStatus")
        assert "paused" in response.lower()

        # Resume
        response = client.send_command("Resume")
        assert "OK" in response

        # Abort (cleanup)
        client.send_command("Abort")

    def test_abort_workflow(self, client):
        """Test aborting an acquisition."""
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

        # Abort
        response = client.send_command("Abort")
        assert "OK" in response

        # Check status
        response = client.send_command("GetAcquisitionStatus")
        assert "aborted" in response.lower() or "idle" in response.lower()
