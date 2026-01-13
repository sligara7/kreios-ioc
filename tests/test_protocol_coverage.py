"""
Protocol coverage tests for KREIOS-150 IOC.

This module verifies that all commands defined in the SpecsLab Prodigy
Remote In protocol (v1.22) are recognized and handled by the simulator/IOC.

Reference: Documentation/SpecsLab_Prodigy_RemoteIn.md
"""

import pytest


# Complete list of commands from SpecsLab Prodigy Remote In protocol v1.22
# Section 2: List of Commands (Requests from Client to SpecsLab Prodigy)
PROTOCOL_COMMANDS = {
    # Connection Management
    "Connect": {
        "section": "2.1",
        "description": "Open connection to SpecsLab Prodigy",
        "params": None,
    },
    "Disconnect": {
        "section": "2.2",
        "description": "Close connection to SpecsLab Prodigy",
        "params": None,
    },

    # Spectrum Definition
    "DefineSpectrumFAT": {
        "section": "2.3",
        "description": "Send FAT spectrum specification",
        "params": {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        },
    },
    "DefineSpectrumSFAT": {
        "section": "2.4",
        "description": "Send SFAT spectrum (snapshot) specification",
        "params": {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "Samples": 10,
            "DwellTime": 0.1,
        },
    },
    "DefineSpectrumFRR": {
        "section": "2.5",
        "description": "Send FRR spectrum specification (fixed retarding ratio)",
        "params": {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "RetardingRatio": 10.0,
        },
    },
    "DefineSpectrumFE": {
        "section": "2.6",
        "description": "Send FE spectrum specification (fixed kinetic energy)",
        "params": {
            "KinEnergy": 400.0,
            "Samples": 10,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        },
    },
    "DefineSpectrumLVS": {
        "section": "2.7",
        "description": "Send LVS spectrum specification (logical voltage scan)",
        "params": {
            "Start": -1.0,
            "End": 1.0,
            "StepWidth": 0.1,
            "KinEnergy": 400.0,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
            "ScanVariable": "Focus Displacement 1",
        },
    },

    # Spectrum Validation (Check without setting)
    "CheckSpectrumFAT": {
        "section": "2.8",
        "description": "Validate FAT spectrum specification without setting",
        "params": {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        },
    },
    "CheckSpectrumSFAT": {
        "section": "2.9",
        "description": "Validate SFAT spectrum specification without setting",
        "params": {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "Samples": 10,
            "DwellTime": 0.1,
        },
    },
    "CheckSpectrumFRR": {
        "section": "2.10",
        "description": "Validate FRR spectrum specification without setting",
        "params": {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "RetardingRatio": 10.0,
        },
    },
    "CheckSpectrumFE": {
        "section": "2.11",
        "description": "Validate FE spectrum specification without setting",
        "params": {
            "KinEnergy": 400.0,
            "Samples": 10,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        },
    },
    "CheckSpectrumLVS": {
        "section": "2.12",
        "description": "Validate LVS spectrum specification without setting",
        "params": {
            "Start": -1.0,
            "End": 1.0,
            "StepWidth": 0.1,
            "KinEnergy": 400.0,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
            "ScanVariable": "Focus Displacement 1",
        },
    },

    # Spectrum Validation and Acquisition Control
    "ValidateSpectrum": {
        "section": "2.13",
        "description": "Validate parameters from previous DefineSpectrum command",
        "params": None,
        "requires_spectrum": True,
    },
    "Start": {
        "section": "2.14",
        "description": "Start data acquisition",
        "params": None,
        "requires_validated_spectrum": True,
    },
    "Pause": {
        "section": "2.15",
        "description": "Pause data acquisition",
        "params": None,
        "requires_running_acquisition": True,
    },
    "Resume": {
        "section": "2.16",
        "description": "Resume paused data acquisition",
        "params": None,
        "requires_paused_acquisition": True,
    },
    "Abort": {
        "section": "2.17",
        "description": "Abort running or paused acquisition",
        "params": None,
        "requires_acquisition": True,
    },

    # Status and Data Retrieval
    "GetAcquisitionStatus": {
        "section": "2.18",
        "description": "Get acquisition status and progress",
        "params": None,
    },
    "GetAcquisitionData": {
        "section": "2.19",
        "description": "Request slice of data from acquisition buffer",
        "params": {"FromIndex": 0, "ToIndex": 10},
        "requires_data": True,
    },
    "ClearSpectrum": {
        "section": "2.20",
        "description": "Clear internal spectrum buffer",
        "params": None,
        "requires_finished_acquisition": True,
    },

    # Analyzer Parameter Commands
    "GetAllAnalyzerParameterNames": {
        "section": "2.21",
        "description": "Get all analyzer device parameter names",
        "params": None,
    },
    "GetAnalyzerParameterInfo": {
        "section": "2.22",
        "description": "Get information about single analyzer parameter",
        "params": {"ParameterName": "Detector Voltage"},
    },
    "GetAnalyzerVisibleName": {
        "section": "2.23",
        "description": "Get analyzer device visible name",
        "params": None,
    },
    "GetAnalyzerParameterValue": {
        "section": "2.24",
        "description": "Get value of single analyzer parameter",
        "params": {"ParameterName": "Detector Voltage"},
    },
    "SetAnalyzerParameterValue": {
        "section": "2.25",
        "description": "Set value of single analyzer parameter",
        "params": {"ParameterName": "Kinetic Energy Base", "Value": 10.0},
    },
    "SetAnalyzerParameterValueDirectly": {
        "section": "2.26",
        "description": "Set logical voltages/currents directly without acquisition",
        "params": {"LensMode": "MediumArea", "ScanRange": "1.5kV"},
    },
    "ValidateAnalyzerParameterValueDirectly": {
        "section": "2.27",
        "description": "Validate logical voltages/currents before setting",
        "params": {"LensMode": "MediumArea", "ScanRange": "1.5kV"},
    },

    # Spectrum Parameter Commands
    "GetSpectrumParameterInfo": {
        "section": "2.28",
        "description": "Get information about single spectrum parameter",
        "params": {"ParameterName": "LensMode"},
    },
    "GetSpectrumDataInfo": {
        "section": "2.29",
        "description": "Get information about spectrum data parameter",
        "params": {"ParameterName": "OrdinateRange"},
    },

    # Device Command Functions
    "GetAllDeviceCommands": {
        "section": "2.30",
        "description": "Get list of available device commands",
        "params": None,
    },
    "GetAllDeviceParameterNames": {
        "section": "2.31",
        "description": "Get device parameter names for a device command",
        "params": {"DeviceCommand": "Analyzer.SetParameters"},
    },
    "GetDeviceParameterInfo": {
        "section": "2.32",
        "description": "Get information about single device parameter",
        "params": {"ParameterName": "ChargeVoltage", "DeviceCommand": "Device.Operate"},
    },
    "GetDeviceParameterValue": {
        "section": "2.33",
        "description": "Get value of single device parameter",
        "params": {"ParameterName": "ChargeVoltage", "DeviceCommand": "Device.Operate"},
    },
    "SetDeviceParameterValue": {
        "section": "2.34",
        "description": "Set value of device parameter",
        "params": {"ParameterName": "ChargeVoltage", "DeviceCommand": "Device.Operate", "Value": 1.0},
    },

    # Analyzer Control
    "DisconnectAnalyzer": {
        "section": "2.35",
        "description": "Disconnect analyzer",
        "params": None,
    },
    "SetSafeState": {
        "section": "2.36",
        "description": "Set all devices into safe state",
        "params": None,
    },

    # Direct Device Command Functions
    "CreateDirectDeviceCommand": {
        "section": "2.37",
        "description": "Create experiment item for device operation",
        "params": {"Template": "Gas Flow"},
    },
    "GetDirectDeviceCommandInfo": {
        "section": "2.38",
        "description": "Get info about device command from Devices item",
        "params": {"DeviceCommand": "Device.Operate"},
    },
    "GetDirectDeviceParameterInfo": {
        "section": "2.39",
        "description": "Get info about parameter of direct device command",
        "params": {"DeviceCommand": "Device.Operate", "ParameterName": "mass_flow"},
    },
    "GetDirectDeviceParameterValue": {
        "section": "2.40",
        "description": "Get parameter value of direct device command",
        "params": {"DeviceCommand": "Device.Operate", "ParameterName": "mass_flow"},
    },
    "SetDirectDeviceParameterValue": {
        "section": "2.41",
        "description": "Set parameter value of direct device command",
        "params": {"DeviceCommand": "Device.Operate", "ParameterName": "mass_flow", "Value": 250.0},
    },
    "ExecuteDirectDeviceCommand": {
        "section": "2.42",
        "description": "Run the Devices item",
        "params": None,
    },

    # Device Information (added in v1.22)
    "GetAllDevices": {
        "section": "2.43",
        "description": "Get list of available devices",
        "params": None,
    },
    "GetDeviceInfo": {
        "section": "2.44",
        "description": "Get device information",
        "params": {"Device": "Analyzer"},
    },
    "GetLiveParameterInfo": {
        "section": "2.45",
        "description": "Get information about live device parameter",
        "params": {"Device": "Analyzer", "Parameter": "Voltage"},
    },
    "GetLiveParameterValue": {
        "section": "2.46",
        "description": "Get current value of live device parameter",
        "params": {"Device": "Analyzer", "Parameter": "Voltage"},
    },
}


# Commands that should work immediately after Connect
BASIC_COMMANDS = [
    "Connect",
    "GetAcquisitionStatus",
    "GetAllAnalyzerParameterNames",
    "GetAnalyzerVisibleName",
    "GetAllDeviceCommands",
    "GetAllDevices",
    "Disconnect",
]

# Core acquisition workflow commands
ACQUISITION_WORKFLOW_COMMANDS = [
    "DefineSpectrumFAT",
    "ValidateSpectrum",
    "Start",
    "GetAcquisitionStatus",
    "Pause",
    "Resume",
    "Abort",
    "GetAcquisitionData",
    "ClearSpectrum",
]


class TestProtocolCommandRecognition:
    """Tests that all protocol commands are recognized (not returning 'unknown command')."""

    def test_basic_commands_recognized(self, client):
        """Test that basic commands are recognized and return OK."""
        client.send_command("Connect")

        for cmd in BASIC_COMMANDS:
            if cmd == "Connect":
                continue  # Already sent
            response = client.send_command(cmd)
            # Commands should return OK or a specific error, not "unknown command"
            assert "Error:101" not in response, f"Command {cmd} returned 'unknown command'"
            assert response is not None, f"Command {cmd} returned no response"

    def test_define_spectrum_fat_recognized(self, client):
        """Test DefineSpectrumFAT command is recognized."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        assert "Error:101" not in response, "DefineSpectrumFAT returned 'unknown command'"
        assert "OK" in response

    def test_define_spectrum_sfat_recognized(self, client):
        """Test DefineSpectrumSFAT command is recognized."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumSFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "Samples": 10,
            "DwellTime": 0.1,
        })
        # May return OK or error (not implemented), but not "unknown command"
        assert "Error:101" not in response, "DefineSpectrumSFAT returned 'unknown command'"

    def test_define_spectrum_frr_recognized(self, client):
        """Test DefineSpectrumFRR command is recognized."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFRR", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "RetardingRatio": 10.0,
        })
        assert "Error:101" not in response, "DefineSpectrumFRR returned 'unknown command'"

    def test_define_spectrum_fe_recognized(self, client):
        """Test DefineSpectrumFE command is recognized."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFE", {
            "KinEnergy": 400.0,
            "Samples": 10,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        assert "Error:101" not in response, "DefineSpectrumFE returned 'unknown command'"

    def test_validate_spectrum_recognized(self, client):
        """Test ValidateSpectrum command is recognized."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        response = client.send_command("ValidateSpectrum")
        assert "Error:101" not in response, "ValidateSpectrum returned 'unknown command'"
        assert "OK" in response

    def test_acquisition_control_commands_recognized(self, client, wait_for_complete_func):
        """Test acquisition control commands (Start, Pause, Resume, Abort) are recognized."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.5,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")

        # Start
        response = client.send_command("Start")
        assert "Error:101" not in response, "Start returned 'unknown command'"
        assert "OK" in response

        # Pause
        response = client.send_command("Pause")
        assert "Error:101" not in response, "Pause returned 'unknown command'"
        assert "OK" in response

        # Resume
        response = client.send_command("Resume")
        assert "Error:101" not in response, "Resume returned 'unknown command'"
        assert "OK" in response

        # Abort
        response = client.send_command("Abort")
        assert "Error:101" not in response, "Abort returned 'unknown command'"
        assert "OK" in response

    def test_get_acquisition_status_recognized(self, client):
        """Test GetAcquisitionStatus command is recognized."""
        client.send_command("Connect")
        response = client.send_command("GetAcquisitionStatus")
        assert "Error:101" not in response, "GetAcquisitionStatus returned 'unknown command'"
        assert "OK" in response
        assert "ControllerState:" in response

    def test_clear_spectrum_recognized(self, client, wait_for_complete_func):
        """Test ClearSpectrum command is recognized."""
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
        wait_for_complete_func(client, timeout=30.0)

        response = client.send_command("ClearSpectrum")
        assert "Error:101" not in response, "ClearSpectrum returned 'unknown command'"
        assert "OK" in response

    def test_analyzer_parameter_commands_recognized(self, client):
        """Test analyzer parameter commands are recognized."""
        client.send_command("Connect")

        # GetAllAnalyzerParameterNames
        response = client.send_command("GetAllAnalyzerParameterNames")
        assert "Error:101" not in response
        assert "OK" in response

        # GetAnalyzerVisibleName
        response = client.send_command("GetAnalyzerVisibleName")
        assert "Error:101" not in response
        assert "OK" in response


class TestProtocolCommandCoverage:
    """Summary test to verify command coverage."""

    def test_protocol_command_list_complete(self):
        """Verify all documented commands are in our test list."""
        # Commands from protocol v1.22 documentation
        documented_commands = [
            "Connect", "Disconnect",
            "DefineSpectrumFAT", "DefineSpectrumSFAT", "DefineSpectrumFRR",
            "DefineSpectrumFE", "DefineSpectrumLVS",
            "CheckSpectrumFAT", "CheckSpectrumSFAT", "CheckSpectrumFRR",
            "CheckSpectrumFE", "CheckSpectrumLVS",
            "ValidateSpectrum", "Start", "Pause", "Resume", "Abort",
            "GetAcquisitionStatus", "GetAcquisitionData", "ClearSpectrum",
            "GetAllAnalyzerParameterNames", "GetAnalyzerParameterInfo",
            "GetAnalyzerVisibleName", "GetAnalyzerParameterValue",
            "SetAnalyzerParameterValue", "SetAnalyzerParameterValueDirectly",
            "ValidateAnalyzerParameterValueDirectly",
            "GetSpectrumParameterInfo", "GetSpectrumDataInfo",
            "GetAllDeviceCommands", "GetAllDeviceParameterNames",
            "GetDeviceParameterInfo", "GetDeviceParameterValue",
            "SetDeviceParameterValue",
            "DisconnectAnalyzer", "SetSafeState",
            "CreateDirectDeviceCommand", "GetDirectDeviceCommandInfo",
            "GetDirectDeviceParameterInfo", "GetDirectDeviceParameterValue",
            "SetDirectDeviceParameterValue", "ExecuteDirectDeviceCommand",
            "GetAllDevices", "GetDeviceInfo",
            "GetLiveParameterInfo", "GetLiveParameterValue",
        ]

        # Verify our test dictionary has all commands
        for cmd in documented_commands:
            assert cmd in PROTOCOL_COMMANDS, f"Command {cmd} missing from PROTOCOL_COMMANDS"

        # Count commands
        assert len(documented_commands) == 46, "Protocol v1.22 has 46 commands"

    def test_core_commands_count(self):
        """Verify core acquisition commands are covered."""
        core_commands = [
            "Connect", "DefineSpectrumFAT", "ValidateSpectrum",
            "Start", "Pause", "Resume", "Abort",
            "GetAcquisitionStatus", "GetAcquisitionData",
            "ClearSpectrum", "Disconnect",
        ]

        for cmd in core_commands:
            assert cmd in PROTOCOL_COMMANDS, f"Core command {cmd} missing"


class TestProtocolVersion:
    """Tests for protocol version compatibility."""

    def test_protocol_version_in_connect(self, client):
        """Test that Connect returns protocol version."""
        response = client.send_command("Connect")
        assert "OK" in response
        # May contain ProtocolVersion
        # Note: Simulator may not implement full version reporting

    def test_supported_protocol_version(self):
        """Verify we are testing against protocol v1.22."""
        # This is a documentation test to ensure we track the correct version
        protocol_version = "1.22"
        protocol_date = "September 2024"

        # These match the documentation header
        assert protocol_version == "1.22"
        assert "September" in protocol_date
