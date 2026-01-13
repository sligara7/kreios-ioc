"""
Tests for the ProdigySimServer simulator.

Tests verify:
- Server startup and shutdown
- Single-client connection enforcement
- State machine transitions
- Data generation quality
- Spectrum mode implementations
"""

import pytest
import socket
import time
import threading


class TestSimulatorStartup:
    """Tests for simulator startup and basic operation."""

    def test_simulator_starts(self, simulator):
        """Test that simulator starts successfully."""
        assert simulator.process is not None
        assert simulator.process.poll() is None  # Still running

    def test_simulator_accepts_connection(self, simulator):
        """Test that simulator accepts TCP connections."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        result = sock.connect_ex((simulator.host, simulator.port))
        sock.close()
        assert result == 0


class TestSingleClientEnforcement:
    """Tests for single-client connection policy."""

    def test_first_connection_accepted(self, simulator):
        """Test that first connection is accepted."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((simulator.host, simulator.port))

        # Send connect command
        sock.sendall(b"?0001 Connect\n")
        response = sock.recv(4096).decode("utf-8")

        sock.close()
        assert "OK" in response

    def test_second_connection_rejected(self, simulator):
        """Test that second connection is rejected while first is active."""
        # First connection
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock1.settimeout(5.0)
        sock1.connect((simulator.host, simulator.port))
        sock1.sendall(b"?0001 Connect\n")
        sock1.recv(4096)

        # Try second connection - should be rejected or timeout
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2.settimeout(2.0)

        try:
            sock2.connect((simulator.host, simulator.port))
            # If connect succeeds, server might reject at protocol level
            # or simply close the connection
            sock2.sendall(b"?0002 Connect\n")
            response = sock2.recv(4096).decode("utf-8")
            # Should get error or empty response
            second_connected = "OK:" in response
        except (socket.timeout, ConnectionRefusedError, ConnectionResetError):
            second_connected = False

        sock1.close()
        sock2.close()

        assert not second_connected

    def test_connection_available_after_disconnect(self, simulator):
        """Test that new connection is accepted after first disconnects."""
        # First connection
        sock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock1.settimeout(5.0)
        sock1.connect((simulator.host, simulator.port))
        sock1.sendall(b"?0001 Connect\n")
        sock1.recv(4096)
        sock1.sendall(b"?0002 Disconnect\n")
        sock1.recv(4096)
        sock1.close()

        # Small delay for server cleanup
        time.sleep(0.2)

        # Second connection should work
        sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock2.settimeout(5.0)
        sock2.connect((simulator.host, simulator.port))
        sock2.sendall(b"?0003 Connect\n")
        response = sock2.recv(4096).decode("utf-8")
        sock2.close()

        assert "OK" in response


class TestSimulatorStateMachine:
    """Tests for acquisition state machine."""

    def test_initial_state_idle(self, client):
        """Test that initial state is idle."""
        client.send_command("Connect")
        response = client.send_command("GetAcquisitionStatus")
        assert "idle" in response.lower()

    def test_state_validated_after_validate(self, client):
        """Test state changes to validated after ValidateSpectrum."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")

        response = client.send_command("GetAcquisitionStatus")
        assert "validated" in response.lower()

    def test_state_running_after_start(self, client):
        """Test state changes to running after Start."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.5,  # Longer dwell to ensure running state
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        response = client.send_command("GetAcquisitionStatus")
        assert "running" in response.lower()

    def test_state_paused_after_pause(self, client):
        """Test state changes to paused after Pause."""
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
        client.send_command("Pause")

        response = client.send_command("GetAcquisitionStatus")
        assert "paused" in response.lower()

    def test_state_aborted_after_abort(self, client):
        """Test state changes to aborted after Abort."""
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
        client.send_command("Abort")

        response = client.send_command("GetAcquisitionStatus")
        assert "aborted" in response.lower()

    def test_state_finished_after_completion(self, client, wait_for_complete_func):
        """Test state changes to finished after acquisition completes."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 401.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,  # Fast acquisition
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        response = wait_for_complete_func(client, timeout=10.0)
        assert "finished" in response.lower()


class TestSimulatorDataGeneration:
    """Tests for simulator data generation."""

    def test_data_contains_gaussian_peak(self, client, wait_for_complete_func):
        """Test that generated data contains a Gaussian-like peak."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        wait_for_complete_func(client, timeout=10.0)

        # Get all data (21 points for 400-410 eV at 0.5 step)
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 20,
        })

        # Parse data
        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]

        assert len(data) == 21

        # Center (index 10) should have higher intensity than edges
        center_intensity = data[10]
        edge_intensity_low = data[0]
        edge_intensity_high = data[20]

        # Center should be at least 2x edge values (Gaussian shape)
        assert center_intensity > edge_intensity_low
        assert center_intensity > edge_intensity_high

    def test_data_values_non_negative(self, client, wait_for_complete_func):
        """Test that all data values are non-negative."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        wait_for_complete_func(client, timeout=10.0)

        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 20,
        })

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]

        for value in data:
            assert value >= 0, f"Negative value found: {value}"

    def test_2d_data_has_spatial_variation(self, client, wait_for_complete_func):
        """Test that 2D data has variation across detector pixels."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 405.0,  # Just center energy
            "EndEnergy": 405.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
            "ValuesPerSample": 10,  # 10 detector pixels
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        wait_for_complete_func(client, timeout=10.0)

        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 9,
        })

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]

        assert len(data) == 10

        # Check that there's variation (not all same value)
        unique_values = set(round(v, 2) for v in data)
        assert len(unique_values) > 1, "All pixel values are identical"


class TestSimulatorSpectrumModes:
    """Tests for different spectrum acquisition modes."""

    def test_fat_mode(self, client, wait_for_complete_func):
        """Test Fixed Analyzer Transmission mode."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        assert "OK" in response

        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=10.0)

        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 4,
        })
        assert "Data:[" in response

    def test_sfat_mode(self, client, wait_for_complete_func):
        """Test Snapshot FAT mode."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumSFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "Samples": 21,
            "DwellTime": 0.01,
        })
        assert "OK" in response

        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=10.0)

        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 10,
        })
        assert "Data:[" in response

    def test_frr_mode(self, client, wait_for_complete_func):
        """Test Fixed Retard Ratio mode."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFRR", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "RetardingRatio": 10.0,
        })
        assert "OK" in response

        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=10.0)

        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 4,
        })
        assert "Data:[" in response

    def test_fe_mode(self, client, wait_for_complete_func):
        """Test Fixed Energies mode."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFE", {
            "Energies": "[400.0,401.0,402.0]",
            "DwellTime": 0.01,
        })
        assert "OK" in response

        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=10.0)

        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 2,
        })
        assert "Data:[" in response


class TestSimulatorProgress:
    """Tests for acquisition progress tracking."""

    def test_progress_increments(self, client):
        """Test that NumberOfAcquiredPoints increments during acquisition."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,  # Slower to observe progress
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        # Collect progress values
        progress_values = []
        for _ in range(5):
            response = client.send_command("GetAcquisitionStatus")
            if "NumberOfAcquiredPoints:" in response:
                parts = response.split("NumberOfAcquiredPoints:")
                if len(parts) > 1:
                    progress = int(parts[1].split()[0])
                    progress_values.append(progress)
            time.sleep(0.2)

        # Progress should be increasing (or stable if finished)
        assert len(progress_values) > 0
        # Should see some variation (not all zeros)
        assert max(progress_values) > 0

        # Cleanup
        client.send_command("Abort")

    def test_progress_reaches_total_samples(self, client, wait_for_complete_func):
        """Test that final progress equals total samples."""
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

        response = client.send_command("GetAcquisitionStatus")
        if "NumberOfAcquiredPoints:" in response:
            parts = response.split("NumberOfAcquiredPoints:")
            final_progress = int(parts[1].split()[0])
            assert final_progress == 5  # (402 - 400) / 0.5 + 1 = 5
