"""
Tests for device command functions in the SpecsLab Prodigy simulator.

Covers protocol sections 2.26-2.27, 2.30-2.34, 2.37-2.42, 2.43-2.46:
- Analyzer direct voltage commands
- Device command functions
- Direct device command functions
- Device information queries
"""

import pytest
import time


class TestAnalyzerDirectVoltageCommands:
    """Tests for SetAnalyzerParameterValueDirectly / ValidateAnalyzerParameterValueDirectly."""

    def test_set_directly_with_params(self, client):
        """Test SetAnalyzerParameterValueDirectly accepts LensMode/ScanRange/Polarity."""
        client.send_command("Connect")
        response = client.send_command("SetAnalyzerParameterValueDirectly", {
            "LensMode": "MediumArea",
            "ScanRange": "1.5kV",
            "Polarity": "positive",
        })
        assert "OK" in response

    def test_validate_directly(self, client):
        """Test ValidateAnalyzerParameterValueDirectly returns OK without state change."""
        client.send_command("Connect")
        response = client.send_command("ValidateAnalyzerParameterValueDirectly", {
            "LensMode": "MediumArea",
            "ScanRange": "1.5kV",
        })
        assert "OK" in response

    def test_set_directly_during_acquisition_fails(self, client):
        """Test SetAnalyzerParameterValueDirectly rejects during acquisition."""
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

        response = client.send_command("SetAnalyzerParameterValueDirectly", {
            "LensMode": "MediumArea",
        })
        assert "Error:" in response
        assert "214" in response


class TestDeviceCommandFunctions:
    """Tests for device command functions (2.30-2.34)."""

    def test_get_all_device_commands(self, client):
        """Test GetAllDeviceCommands returns command list."""
        client.send_command("Connect")
        response = client.send_command("GetAllDeviceCommands")
        assert "OK" in response
        assert "DeviceCommands:[" in response
        assert "X-Ray Dummy.Operate" in response

    def test_get_all_device_parameter_names(self, client):
        """Test GetAllDeviceParameterNames returns params for known command."""
        client.send_command("Connect")
        response = client.send_command("GetAllDeviceParameterNames", {
            "DeviceCommand": "X-Ray Dummy.Operate",
        })
        assert "OK" in response
        assert "ParameterNames:[" in response
        assert "uanode" in response

    def test_get_all_device_parameter_names_unknown(self, client):
        """Test GetAllDeviceParameterNames with unknown command returns error."""
        client.send_command("Connect")
        response = client.send_command("GetAllDeviceParameterNames", {
            "DeviceCommand": "Unknown.Command",
        })
        assert "Error:" in response
        assert "218" in response

    def test_get_device_parameter_info(self, client):
        """Test GetDeviceParameterInfo returns Type/ValueType/Unit."""
        client.send_command("Connect")
        response = client.send_command("GetDeviceParameterInfo", {
            "DeviceCommand": "X-Ray Dummy.Operate",
            "ParameterName": "uanode",
        })
        assert "OK" in response
        assert "Type:" in response
        assert "ValueType:" in response
        assert "Unit:" in response

    def test_get_device_parameter_value(self, client):
        """Test GetDeviceParameterValue returns Name/Value."""
        client.send_command("Connect")
        response = client.send_command("GetDeviceParameterValue", {
            "DeviceCommand": "X-Ray Dummy.Operate",
            "ParameterName": "uanode",
        })
        assert "OK" in response
        assert "Name:" in response
        assert "Value:" in response

    def test_set_device_parameter_value(self, client):
        """Test SetDeviceParameterValue updates value (verify with Get)."""
        client.send_command("Connect")
        response = client.send_command("SetDeviceParameterValue", {
            "DeviceCommand": "X-Ray Dummy.Operate",
            "ParameterName": "uanode",
            "Value": 12.0,
        })
        assert "OK" in response

        # Verify the value changed
        response2 = client.send_command("GetDeviceParameterValue", {
            "DeviceCommand": "X-Ray Dummy.Operate",
            "ParameterName": "uanode",
        })
        assert "12" in response2

    def test_set_device_parameter_value_during_acquisition(self, client):
        """Test SetDeviceParameterValue rejects during acquisition."""
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

        response = client.send_command("SetDeviceParameterValue", {
            "DeviceCommand": "X-Ray Dummy.Operate",
            "ParameterName": "uanode",
            "Value": 10.0,
        })
        assert "Error:" in response
        assert "214" in response


class TestDirectDeviceCommands:
    """Tests for direct device command functions (2.37-2.42)."""

    def test_create_direct_device_command(self, client):
        """Test CreateDirectDeviceCommand returns DeviceCommands list."""
        client.send_command("Connect")
        response = client.send_command("CreateDirectDeviceCommand", {
            "Template": "Gas Flow",
        })
        assert "OK" in response
        assert "DeviceCommands:[" in response
        assert "BrooksGF040.Operate" in response

    def test_create_unknown_template_fails(self, client):
        """Test CreateDirectDeviceCommand with unknown template returns error."""
        client.send_command("Connect")
        response = client.send_command("CreateDirectDeviceCommand", {
            "Template": "NonExistent",
        })
        assert "Error:" in response
        assert "219" in response

    def test_create_replaces_previous(self, client):
        """Test CreateDirectDeviceCommand replaces previous direct command."""
        client.send_command("Connect")
        client.send_command("CreateDirectDeviceCommand", {
            "Template": "Gas Flow",
        })
        response = client.send_command("CreateDirectDeviceCommand", {
            "Template": "Ion Source",
        })
        assert "OK" in response
        assert "SPECS_IQE12_38.Operate" in response
        # Old command should be gone
        assert "BrooksGF040" not in response

    def test_get_direct_device_command_info(self, client):
        """Test GetDirectDeviceCommandInfo returns Type/Name/ParameterNames."""
        client.send_command("Connect")
        client.send_command("CreateDirectDeviceCommand", {
            "Template": "Gas Flow",
        })
        response = client.send_command("GetDirectDeviceCommandInfo", {
            "DeviceCommand": "BrooksGF040.Operate",
        })
        assert "OK" in response
        assert "Type:" in response
        assert "Name:" in response
        assert "ParameterNames:[" in response

    def test_get_direct_device_command_info_without_create(self, client):
        """Test GetDirectDeviceCommandInfo without Create returns error."""
        client.send_command("Connect")
        response = client.send_command("GetDirectDeviceCommandInfo", {
            "DeviceCommand": "BrooksGF040.Operate",
        })
        assert "Error:" in response
        assert "218" in response

    def test_get_direct_device_parameter_info(self, client):
        """Test GetDirectDeviceParameterInfo returns Type/ValueType/Unit."""
        client.send_command("Connect")
        client.send_command("CreateDirectDeviceCommand", {
            "Template": "Gas Flow",
        })
        response = client.send_command("GetDirectDeviceParameterInfo", {
            "DeviceCommand": "BrooksGF040.Operate",
            "ParameterName": "mass_flow",
        })
        assert "OK" in response
        assert "Type:" in response
        assert "ValueType:" in response
        assert "Unit:" in response

    def test_get_direct_device_parameter_value(self, client):
        """Test GetDirectDeviceParameterValue returns Name/Value."""
        client.send_command("Connect")
        client.send_command("CreateDirectDeviceCommand", {
            "Template": "Gas Flow",
        })
        response = client.send_command("GetDirectDeviceParameterValue", {
            "DeviceCommand": "BrooksGF040.Operate",
            "ParameterName": "mass_flow",
        })
        assert "OK" in response
        assert "Name:" in response
        assert "Value:" in response

    def test_set_direct_device_parameter_value(self, client):
        """Test SetDirectDeviceParameterValue updates value (verify with Get)."""
        client.send_command("Connect")
        client.send_command("CreateDirectDeviceCommand", {
            "Template": "Gas Flow",
        })
        response = client.send_command("SetDirectDeviceParameterValue", {
            "DeviceCommand": "BrooksGF040.Operate",
            "ParameterName": "mass_flow",
            "Value": 250.0,
        })
        assert "OK" in response

        # Verify the value changed
        response2 = client.send_command("GetDirectDeviceParameterValue", {
            "DeviceCommand": "BrooksGF040.Operate",
            "ParameterName": "mass_flow",
        })
        assert "250" in response2

    def test_execute_direct_device_command(self, client):
        """Test ExecuteDirectDeviceCommand returns OK."""
        client.send_command("Connect")
        client.send_command("CreateDirectDeviceCommand", {
            "Template": "Gas Flow",
        })
        response = client.send_command("ExecuteDirectDeviceCommand")
        assert "OK" in response

    def test_execute_without_create_fails(self, client):
        """Test ExecuteDirectDeviceCommand without Create returns error."""
        client.send_command("Connect")
        response = client.send_command("ExecuteDirectDeviceCommand")
        assert "Error:" in response
        assert "219" in response

    def test_execute_with_safe_state_after(self, client):
        """Test ExecuteDirectDeviceCommand with SetSafeStateAfter returns OK."""
        client.send_command("Connect")
        client.send_command("CreateDirectDeviceCommand", {
            "Template": "Ion Source",
        })
        response = client.send_command("ExecuteDirectDeviceCommand", {
            "SetSafeStateAfter": "true",
        })
        assert "OK" in response


class TestDeviceInformation:
    """Tests for device information queries (2.43-2.46)."""

    def test_get_all_devices(self, client):
        """Test GetAllDevices returns device list."""
        client.send_command("Connect")
        response = client.send_command("GetAllDevices")
        assert "OK" in response
        assert "Devices:[" in response
        assert "Analyzer ND" in response
        assert "Beamline" in response

    def test_get_device_info(self, client):
        """Test GetDeviceInfo returns Type/VisibleName/LiveParameterNames."""
        client.send_command("Connect")
        response = client.send_command("GetDeviceInfo", {
            "Device": "Analyzer ND",
        })
        assert "OK" in response
        assert "Type:" in response
        assert "VisibleName:" in response
        assert "LiveParameterNames:[" in response

    def test_get_device_info_unknown(self, client):
        """Test GetDeviceInfo with unknown device returns error."""
        client.send_command("Connect")
        response = client.send_command("GetDeviceInfo", {
            "Device": "Unknown Device",
        })
        assert "Error:" in response
        assert "220" in response

    def test_get_live_parameter_info(self, client):
        """Test GetLiveParameterInfo returns ValueType/Unit."""
        client.send_command("Connect")
        response = client.send_command("GetLiveParameterInfo", {
            "Device": "Analyzer ND",
            "Parameter": "Kinetic Energy",
        })
        assert "OK" in response
        assert "ValueType:" in response
        assert "Unit:" in response

    def test_get_live_parameter_info_unknown_param(self, client):
        """Test GetLiveParameterInfo with unknown parameter returns error."""
        client.send_command("Connect")
        response = client.send_command("GetLiveParameterInfo", {
            "Device": "Analyzer ND",
            "Parameter": "NoSuchParam",
        })
        assert "Error:" in response
        assert "206" in response

    def test_get_live_parameter_value(self, client):
        """Test GetLiveParameterValue returns Connectivity/Value."""
        client.send_command("Connect")
        response = client.send_command("GetLiveParameterValue", {
            "Device": "Analyzer ND",
            "Parameter": "Kinetic Energy",
        })
        assert "OK" in response
        assert "Connectivity:" in response
        assert "Value:" in response

    def test_get_live_parameter_value_unknown_device(self, client):
        """Test GetLiveParameterValue with unknown device returns error."""
        client.send_command("Connect")
        response = client.send_command("GetLiveParameterValue", {
            "Device": "Nonexistent",
            "Parameter": "Voltage",
        })
        assert "Error:" in response
        assert "220" in response

    def test_get_live_parameter_value_connectivity_online(self, client):
        """Test GetLiveParameterValue reports Connectivity:Online."""
        client.send_command("Connect")
        response = client.send_command("GetLiveParameterValue", {
            "Device": "Analyzer ND",
            "Parameter": "Detector Voltage",
        })
        assert "OK" in response
        assert "Connectivity:Online" in response
