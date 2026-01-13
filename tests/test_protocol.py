"""
Protocol conformance tests for SpecsLab Prodigy Remote In protocol v1.2.

Tests verify correct implementation of:
- Request/response message format
- Command parsing and routing
- Parameter encoding/decoding
- Error code handling
- Protocol state machine
"""

import pytest


class TestMessageFormat:
    """Tests for protocol message format compliance."""

    def test_request_format_valid(self, client):
        """Test that valid request format is accepted."""
        # Send Connect with proper format: ?<4-hex-id> Command
        response = client.send_raw("?0001 Connect\n")
        assert response.startswith("!0001")
        assert "OK" in response

    def test_request_format_invalid_no_question_mark(self, client):
        """Test that request without ? prefix is rejected."""
        response = client.send_raw("0001 Connect\n")
        assert response is None or "Error" in response

    def test_request_format_invalid_short_id(self, client):
        """Test that request with short ID is rejected."""
        response = client.send_raw("?01 Connect\n")
        assert "Error" in response

    def test_request_id_echoed_in_response(self, client):
        """Test that request ID is properly echoed in response."""
        # Use a distinctive ID
        response = client.send_raw("?ABCD Connect\n")
        assert response.startswith("!ABCD")

    def test_response_ok_format(self, client):
        """Test OK response format: !<id> OK[:params]"""
        response = client.send_command("Connect")
        assert response.startswith("!")
        assert " OK" in response

    def test_response_ok_with_params(self, client):
        """Test OK response includes parameters when expected."""
        response = client.send_command("Connect")
        assert "ServerName:" in response
        assert "ProtocolVersion:" in response

    def test_response_error_format(self, client):
        """Test Error response format: !<id> Error:<code> <message>"""
        # Send Connect, then try to connect again (should fail)
        client.send_command("Connect")
        response = client.send_command("Connect")
        assert " Error:" in response


class TestConnectionCommands:
    """Tests for Connect/Disconnect commands."""

    def test_connect_returns_server_info(self, client):
        """Test Connect returns ServerName and ProtocolVersion."""
        response = client.send_command("Connect")
        assert "OK" in response
        assert "ServerName:" in response
        assert "ProtocolVersion:1.2" in response

    def test_connect_twice_fails(self, client):
        """Test that connecting twice from same client fails."""
        response1 = client.send_command("Connect")
        assert "OK" in response1

        response2 = client.send_command("Connect")
        assert "Error:" in response2
        assert "2" in response2  # Error code 2 = Already connected

    def test_disconnect_success(self, client):
        """Test successful disconnect."""
        client.send_command("Connect")
        response = client.send_command("Disconnect")
        assert "OK" in response

    def test_disconnect_without_connect_fails(self, unconnected_client):
        """Test disconnect without prior connect fails."""
        unconnected_client.connect()
        response = unconnected_client.send_command("Disconnect")
        assert "Error:" in response


class TestSpectrumDefinitionCommands:
    """Tests for spectrum definition commands."""

    def test_define_spectrum_fat_success(self, client):
        """Test DefineSpectrumFAT with valid parameters."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        assert "OK" in response

    def test_define_spectrum_sfat_success(self, client):
        """Test DefineSpectrumSFAT with valid parameters."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumSFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "Samples": 21,
            "DwellTime": 0.1,
        })
        assert "OK" in response

    def test_define_spectrum_frr_success(self, client):
        """Test DefineSpectrumFRR with valid parameters."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFRR", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "RetardingRatio": 10.0,
        })
        assert "OK" in response

    def test_define_spectrum_fe_success(self, client):
        """Test DefineSpectrumFE with energy array."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFE", {
            "Energies": "[400.0,401.0,402.0,403.0,404.0]",
            "DwellTime": 0.1,
        })
        assert "OK" in response

    def test_define_spectrum_with_2d_params(self, client):
        """Test DefineSpectrumFAT with ValuesPerSample for 2D data."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
            "ValuesPerSample": 128,
        })
        assert "OK" in response

    def test_define_spectrum_with_3d_params(self, client):
        """Test DefineSpectrumFAT with NumberOfSlices for 3D data."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
            "ValuesPerSample": 64,
            "NumberOfSlices": 5,
        })
        assert "OK" in response


class TestSpectrumValidation:
    """Tests for spectrum validation commands."""

    def test_validate_spectrum_success(self, client):
        """Test ValidateSpectrum returns spectrum parameters."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        response = client.send_command("ValidateSpectrum")
        assert "OK" in response
        assert "Samples:" in response
        assert "StartEnergy:" in response
        assert "EndEnergy:" in response

    def test_validate_without_define_fails(self, client):
        """Test ValidateSpectrum without prior DefineSpectrum fails."""
        client.send_command("Connect")
        response = client.send_command("ValidateSpectrum")
        assert "Error:" in response

    def test_check_spectrum_fat_no_side_effects(self, client):
        """Test CheckSpectrumFAT validates without setting spectrum."""
        client.send_command("Connect")
        response = client.send_command("CheckSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        assert "OK" in response
        assert "Samples:" in response

        # ValidateSpectrum should fail since no spectrum is defined
        response2 = client.send_command("ValidateSpectrum")
        assert "Error:" in response2

    def test_clear_spectrum(self, client):
        """Test ClearSpectrum resets spectrum state."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")

        response = client.send_command("ClearSpectrum")
        assert "OK" in response

        # Validate should now fail
        response2 = client.send_command("ValidateSpectrum")
        assert "Error:" in response2


class TestParameterCommands:
    """Tests for device parameter commands."""

    def test_get_all_parameter_names(self, client):
        """Test GetAllAnalyzerParameterNames returns parameter list."""
        client.send_command("Connect")
        response = client.send_command("GetAllAnalyzerParameterNames")
        assert "OK" in response
        assert "ParameterNames:" in response
        assert "[" in response

    def test_get_analyzer_visible_name(self, client):
        """Test GetAnalyzerVisibleName returns device name."""
        client.send_command("Connect")
        response = client.send_command("GetAnalyzerVisibleName")
        assert "OK" in response
        assert "AnalyzerVisibleName:" in response

    def test_get_parameter_value(self, client):
        """Test GetAnalyzerParameterValue returns value."""
        client.send_command("Connect")
        response = client.send_command("GetAnalyzerParameterValue", {
            "ParameterName": "Detector Voltage"
        })
        assert "OK" in response
        assert "Value:" in response

    def test_get_unknown_parameter_fails(self, client):
        """Test GetAnalyzerParameterValue with unknown parameter fails."""
        client.send_command("Connect")
        response = client.send_command("GetAnalyzerParameterValue", {
            "ParameterName": "NonExistentParameter"
        })
        assert "Error:" in response

    def test_set_parameter_value(self, client):
        """Test SetAnalyzerParameterValue updates value."""
        client.send_command("Connect")

        # Set value
        response = client.send_command("SetAnalyzerParameterValue", {
            "ParameterName": "Detector Voltage",
            "Value": 1500.0,
        })
        assert "OK" in response

        # Verify value changed
        response2 = client.send_command("GetAnalyzerParameterValue", {
            "ParameterName": "Detector Voltage"
        })
        assert "1500" in response2


class TestAcquisitionCommands:
    """Tests for acquisition control commands."""

    def test_start_acquisition(self, client):
        """Test Start command begins acquisition."""
        client.send_command("Connect")
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

    def test_start_without_validate_fails(self, client):
        """Test Start without ValidateSpectrum fails."""
        client.send_command("Connect")
        response = client.send_command("Start")
        assert "Error:" in response

    def test_pause_resume(self, client):
        """Test Pause and Resume commands."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        # Pause
        response = client.send_command("Pause")
        assert "OK" in response

        # Check status shows paused
        status = client.send_command("GetAcquisitionStatus")
        assert "paused" in status.lower()

        # Resume
        response = client.send_command("Resume")
        assert "OK" in response

    def test_abort_acquisition(self, client):
        """Test Abort command stops acquisition."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        response = client.send_command("Abort")
        assert "OK" in response

        status = client.send_command("GetAcquisitionStatus")
        assert "aborted" in status.lower()

    def test_get_acquisition_status(self, client):
        """Test GetAcquisitionStatus returns state and progress."""
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

        response = client.send_command("GetAcquisitionStatus")
        assert "OK" in response
        assert "ControllerState:" in response

    def test_get_acquisition_data(self, client, wait_for_complete_func):
        """Test GetAcquisitionData returns data array."""
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

        # Wait for some data
        wait_for_complete_func(client, timeout=10.0)

        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 2,
        })
        assert "OK" in response
        assert "Data:[" in response

    def test_get_acquisition_data_invalid_range(self, client):
        """Test GetAcquisitionData with invalid range fails."""
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

        # Try to get data beyond what's acquired
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 1000000,
            "ToIndex": 1000010,
        })
        assert "Error:" in response


class TestUnknownCommands:
    """Tests for unknown/invalid command handling."""

    def test_unknown_command_error(self, client):
        """Test unknown command returns error."""
        client.send_command("Connect")
        response = client.send_command("UnknownCommand123")
        assert "Error:" in response
        assert "101" in response  # Unknown command error code

    def test_empty_command_error(self, client):
        """Test empty command line handling."""
        client.send_command("Connect")
        response = client.send_raw("?0001 \n")
        assert "Error:" in response
