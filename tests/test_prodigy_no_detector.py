"""
Protocol tests against real SpecsLab Prodigy with no detector attached.

These tests validate protocol conformance against the actual Prodigy software
running on the Windows machine (10.67.228.10), without requiring the KREIOS
detector or analyzer electronics (EC 10) to be connected.

Usage:
    USE_EXTERNAL_SIMULATOR=1 SIMULATOR_HOST=10.67.228.10 \
        pytest tests/test_prodigy_no_detector.py -v

Tests are organized by what's testable without a connected analyzer:
- Connection management
- Protocol message format
- Device information and live parameter queries
- Device command parameter queries
- Spectrum definition (no validate/acquire)
- Acquisition status in idle state
- Control commands (SetSafeState, DisconnectAnalyzer)
- All 46 commands recognized (smoke test)

Skipped areas (require analyzer EC 10 online):
- ValidateSpectrum, CheckSpectrum* (need analyzer communication)
- Start/Pause/Resume/Abort (need validated spectrum)
- GetAnalyzerParameter* (need analyzer EC 10)
- GetSpectrumParameterInfo/GetSpectrumDataInfo (need analyzer EC 10)
"""

import os
import pytest

# Skip entire module if not running against external simulator
pytestmark = pytest.mark.skipif(
    os.environ.get("USE_EXTERNAL_SIMULATOR", "0") != "1",
    reason="Requires USE_EXTERNAL_SIMULATOR=1 (real Prodigy connection)"
)

# ============================================================================
# Real hardware configuration discovered from Prodigy 4.120.0-r122222
# ============================================================================

# Devices reported by GetAllDevices
REAL_DEVICES = {
    "Analyzer ND": {
        "type": "PhoibosND",
        "visible_name": "KREIOS MM",
        "live_params": [
            "Kinetic Energy (Target)",
            "Pass Energy (Target)",
            "Detector Voltage (Target)",
            "Count Rate",
        ],
    },
    "Aperture MCS2": {
        "type": "Aperture MCS2",
        "visible_name": "KREIOS Aperture",
        "live_params": ["Pos_k_x", "Pos_k_y", "Pos_real_x", "Pos_real_y"],
    },
    "Beamline": {
        "type": "Beamline",
        "visible_name": "Monochromator",
        "live_params": ["Excitation Energy"],
    },
    "ILC 10": {
        "type": "ILC10-Net",
        "visible_name": "ILC 10",
        "live_params": [],
    },
    "MCPS 36 Manipulator (Nanotec)": {
        "type": None,  # not yet probed
        "visible_name": None,
        "live_params": None,
    },
}

# Device commands reported by GetAllDeviceCommands
REAL_DEVICE_COMMANDS = {
    "Analyzer ND.Configure 2D/XPS": {
        "params": [],  # No parameters
    },
    "X-Ray Dummy.Operate": {
        "params": ["uanode", "iemission"],
    },
}


# ============================================================================
# Connection and Protocol Format
# ============================================================================

class TestProdigyConnection:
    """Test connection to real Prodigy."""

    def test_connect_returns_server_info(self, client):
        """Connect returns real Prodigy server name and protocol version."""
        response = client.send_command("Connect")
        assert "OK" in response
        assert "ServerName:" in response
        assert "ProtocolVersion:1.22" in response
        assert "SpecsLab Prodigy" in response

    def test_connect_twice_fails(self, client):
        """Double connect returns error 2."""
        client.send_command("Connect")
        response = client.send_command("Connect")
        assert "Error:" in response
        assert "2" in response

    def test_disconnect_success(self, client):
        """Disconnect after connect returns OK."""
        client.send_command("Connect")
        response = client.send_command("Disconnect")
        assert "OK" in response

    def test_disconnect_without_connect_fails(self, unconnected_client):
        """Disconnect without prior connect returns error 3."""
        unconnected_client.connect()
        response = unconnected_client.send_command("Disconnect")
        assert "Error:" in response
        assert "3" in response

    def test_request_id_echoed(self, client):
        """Request ID is echoed in response."""
        response = client.send_raw("?A1B2 Connect\n")
        assert response.startswith("!A1B2")

    def test_unknown_command_returns_101(self, client):
        """Unknown command returns error 101."""
        client.send_command("Connect")
        response = client.send_command("TotallyFakeCommand123")
        assert "Error:" in response
        assert "101" in response


# ============================================================================
# Analyzer Visible Name (works without EC 10)
# ============================================================================

class TestProdigyAnalyzerName:
    """Test analyzer name query."""

    def test_get_analyzer_visible_name(self, client):
        """GetAnalyzerVisibleName returns KREIOS MM."""
        client.send_command("Connect")
        response = client.send_command("GetAnalyzerVisibleName")
        assert "OK" in response
        assert "AnalyzerVisibleName:" in response
        assert "KREIOS" in response


# ============================================================================
# Device Information (2.43-2.46)
# ============================================================================

class TestProdigyDeviceInformation:
    """Test device information queries against real Prodigy."""

    def test_get_all_devices(self, client):
        """GetAllDevices returns the real device list."""
        client.send_command("Connect")
        response = client.send_command("GetAllDevices")
        assert "OK" in response
        assert "Devices:[" in response
        for device in ["Analyzer ND", "Aperture MCS2", "Beamline", "ILC 10"]:
            assert device in response, f"Missing device: {device}"

    @pytest.mark.parametrize("device,expected_type,expected_name", [
        ("Analyzer ND", "PhoibosND", "KREIOS MM"),
        ("Aperture MCS2", "Aperture MCS2", "KREIOS Aperture"),
        ("Beamline", "Beamline", "Monochromator"),
        ("ILC 10", "ILC10-Net", "ILC 10"),
    ])
    def test_get_device_info(self, client, device, expected_type, expected_name):
        """GetDeviceInfo returns correct Type and VisibleName for each device."""
        client.send_command("Connect")
        response = client.send_command("GetDeviceInfo", {"Device": device})
        assert "OK" in response
        assert f'Type:"{expected_type}"' in response
        assert f'VisibleName:"{expected_name}"' in response
        assert "LiveParameterNames:[" in response

    def test_get_device_info_unknown_device(self, client):
        """GetDeviceInfo with unknown device returns error 220."""
        client.send_command("Connect")
        response = client.send_command("GetDeviceInfo", {"Device": "Nonexistent"})
        assert "Error:" in response
        assert "220" in response

    @pytest.mark.parametrize("device,param", [
        ("Analyzer ND", "Kinetic Energy (Target)"),
        ("Analyzer ND", "Count Rate"),
        ("Aperture MCS2", "Pos_k_x"),
        ("Beamline", "Excitation Energy"),
    ])
    def test_get_live_parameter_info(self, client, device, param):
        """GetLiveParameterInfo returns ValueType and Unit."""
        client.send_command("Connect")
        response = client.send_command("GetLiveParameterInfo", {
            "Device": device,
            "Parameter": param,
        })
        assert "OK" in response
        assert "ValueType:" in response
        assert "Unit:" in response

    @pytest.mark.parametrize("device,param", [
        ("Analyzer ND", "Kinetic Energy (Target)"),
        ("Analyzer ND", "Detector Voltage (Target)"),
        ("Analyzer ND", "Count Rate"),
        ("Aperture MCS2", "Pos_k_x"),
        ("Aperture MCS2", "Pos_k_y"),
        ("Beamline", "Excitation Energy"),
    ])
    def test_get_live_parameter_value(self, client, device, param):
        """GetLiveParameterValue returns Connectivity and Value."""
        client.send_command("Connect")
        response = client.send_command("GetLiveParameterValue", {
            "Device": device,
            "Parameter": param,
        })
        assert "OK" in response
        assert "Connectivity:" in response
        assert "Value:" in response

    def test_live_params_offline_without_detector(self, client):
        """All live params report Connectivity:Offline when EC 10 is disconnected."""
        client.send_command("Connect")
        response = client.send_command("GetLiveParameterValue", {
            "Device": "Analyzer ND",
            "Parameter": "Kinetic Energy (Target)",
        })
        assert "Connectivity:Offline" in response


# ============================================================================
# Device Commands (2.30-2.34)
# ============================================================================

class TestProdigyDeviceCommands:
    """Test device command queries against real Prodigy."""

    def test_get_all_device_commands(self, client):
        """GetAllDeviceCommands returns real command list."""
        client.send_command("Connect")
        response = client.send_command("GetAllDeviceCommands")
        assert "OK" in response
        assert "DeviceCommands:[" in response
        assert "X-Ray Dummy.Operate" in response

    def test_get_device_parameter_names_xray(self, client):
        """GetAllDeviceParameterNames returns params for X-Ray Dummy."""
        client.send_command("Connect")
        response = client.send_command("GetAllDeviceParameterNames", {
            "DeviceCommand": "X-Ray Dummy.Operate",
        })
        assert "OK" in response
        assert "ParameterNames:[" in response
        assert "uanode" in response
        assert "iemission" in response

    def test_get_device_parameter_names_unknown(self, client):
        """GetAllDeviceParameterNames with unknown command returns error 218."""
        client.send_command("Connect")
        response = client.send_command("GetAllDeviceParameterNames", {
            "DeviceCommand": "Nonexistent.Command",
        })
        assert "Error:" in response
        assert "218" in response

    @pytest.mark.parametrize("param", ["uanode", "iemission"])
    def test_get_device_parameter_info(self, client, param):
        """GetDeviceParameterInfo returns Type/ValueType/Unit for X-Ray Dummy params."""
        client.send_command("Connect")
        response = client.send_command("GetDeviceParameterInfo", {
            "DeviceCommand": "X-Ray Dummy.Operate",
            "ParameterName": param,
        })
        assert "OK" in response
        assert "Type:" in response
        assert "ValueType:" in response

    @pytest.mark.parametrize("param", ["uanode", "iemission"])
    def test_get_device_parameter_value(self, client, param):
        """GetDeviceParameterValue returns Name/Value for X-Ray Dummy params."""
        client.send_command("Connect")
        response = client.send_command("GetDeviceParameterValue", {
            "DeviceCommand": "X-Ray Dummy.Operate",
            "ParameterName": param,
        })
        assert "OK" in response
        assert "Name:" in response
        assert "Value:" in response


# ============================================================================
# Spectrum Definition (works without analyzer, just stores params)
# ============================================================================

class TestProdigySpectrumDefinition:
    """Test spectrum definition commands (no validate/acquire needed)."""

    def test_define_spectrum_fat(self, client):
        """DefineSpectrumFAT with required LensMode/ScanRange succeeds."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
            "LensMode": "LowAngularDispersion",
            "ScanRange": "LargeArea",
        })
        assert "OK" in response

    def test_define_spectrum_fat_missing_lens_mode(self, client):
        """DefineSpectrumFAT without LensMode returns error 104."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        assert "Error:" in response
        assert "104" in response

    def test_define_spectrum_sfat_requires_analyzer(self, client):
        """DefineSpectrumSFAT needs analyzer (SFAT requires hardware negotiation)."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumSFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "Samples": 10,
            "DwellTime": 0.1,
            "LensMode": "LowAngularDispersion",
            "ScanRange": "LargeArea",
        })
        # SFAT (snapshot) mode requires analyzer communication to negotiate
        # pass energy and step width, so it fails without EC 10
        assert "Error:" in response

    def test_define_spectrum_frr(self, client):
        """DefineSpectrumFRR with required params succeeds."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFRR", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "RetardingRatio": 10.0,
            "LensMode": "LowAngularDispersion",
            "ScanRange": "LargeArea",
        })
        assert "OK" in response

    def test_define_spectrum_fe(self, client):
        """DefineSpectrumFE with required params succeeds."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFE", {
            "KinEnergy": 400.0,
            "Samples": 10,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
            "LensMode": "LowAngularDispersion",
            "ScanRange": "LargeArea",
        })
        assert "OK" in response

    def test_define_spectrum_lvs(self, client):
        """DefineSpectrumLVS with required params succeeds."""
        client.send_command("Connect")
        response = client.send_command("DefineSpectrumLVS", {
            "Start": -1.0,
            "End": 1.0,
            "StepWidth": 0.1,
            "KinEnergy": 400.0,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
            "LensMode": "LowAngularDispersion",
            "ScanRange": "LargeArea",
            "ScanVariable": "Focus Displacement 1 [nu]",
        })
        assert "OK" in response

    def test_validate_fails_without_detector(self, client):
        """ValidateSpectrum fails with error 202 when EC 10 is offline."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
            "LensMode": "LowAngularDispersion",
            "ScanRange": "LargeArea",
        })
        response = client.send_command("ValidateSpectrum")
        assert "Error:" in response
        # Error 202: Unable to connect to analyzer
        assert "202" in response


# ============================================================================
# Acquisition Status (idle state)
# ============================================================================

class TestProdigyAcquisitionStatus:
    """Test acquisition status in idle state."""

    def test_idle_status(self, client):
        """GetAcquisitionStatus returns idle state."""
        client.send_command("Connect")
        response = client.send_command("GetAcquisitionStatus")
        assert "OK" in response
        assert "ControllerState:idle" in response

    def test_start_without_validate_fails(self, client):
        """Start without ValidateSpectrum fails."""
        client.send_command("Connect")
        response = client.send_command("Start")
        assert "Error:" in response


# ============================================================================
# Control Commands
# ============================================================================

class TestProdigyControlCommands:
    """Test control commands that work without detector."""

    def test_set_safe_state(self, client):
        """SetSafeState returns OK."""
        client.send_command("Connect")
        response = client.send_command("SetSafeState")
        assert "OK" in response

    def test_disconnect_analyzer(self, client):
        """DisconnectAnalyzer returns OK."""
        client.send_command("Connect")
        response = client.send_command("DisconnectAnalyzer")
        assert "OK" in response

    def test_set_analyzer_parameter_value_directly(self, client):
        """SetAnalyzerParameterValueDirectly accepted (may fail at hardware level)."""
        client.send_command("Connect")
        response = client.send_command("SetAnalyzerParameterValueDirectly", {
            "LensMode": "LowAngularDispersion",
            "ScanRange": "LargeArea",
        })
        # Command is recognized - may return OK or hardware-level error
        assert "Error: 101" not in response

    def test_validate_analyzer_parameter_value_directly(self, client):
        """ValidateAnalyzerParameterValueDirectly accepted."""
        client.send_command("Connect")
        response = client.send_command("ValidateAnalyzerParameterValueDirectly", {
            "LensMode": "LowAngularDispersion",
            "ScanRange": "LargeArea",
        })
        assert "Error: 101" not in response


# ============================================================================
# All 46 Commands Recognized (smoke test)
# ============================================================================

ALL_COMMANDS = [
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

assert len(ALL_COMMANDS) == 46


class TestProdigyAllCommandsRecognized:
    """Verify all 46 protocol commands are recognized by real Prodigy."""

    @pytest.mark.parametrize("command", ALL_COMMANDS)
    def test_command_not_error_101(self, client, command):
        """Command is recognized (does not return 'unknown command' error 101)."""
        client.send_command("Connect")

        if command in ("Connect", "Disconnect"):
            return  # Skip - Connect already sent, Disconnect would break client

        # Send with minimal params to avoid parse errors
        params = {
            "DefineSpectrumFAT": {"StartEnergy": 400, "EndEnergy": 410, "StepWidth": 0.5,
                                  "DwellTime": 0.1, "PassEnergy": 20,
                                  "LensMode": "LowAngularDispersion", "ScanRange": "LargeArea"},
            "DefineSpectrumSFAT": {"StartEnergy": 400, "EndEnergy": 410, "Samples": 10,
                                   "DwellTime": 0.1, "LensMode": "LowAngularDispersion",
                                   "ScanRange": "LargeArea"},
            "DefineSpectrumFRR": {"StartEnergy": 400, "EndEnergy": 410, "StepWidth": 0.5,
                                  "DwellTime": 0.1, "RetardingRatio": 10,
                                  "LensMode": "LowAngularDispersion", "ScanRange": "LargeArea"},
            "DefineSpectrumFE": {"KinEnergy": 400, "Samples": 10, "DwellTime": 0.1,
                                 "PassEnergy": 20, "LensMode": "LowAngularDispersion",
                                 "ScanRange": "LargeArea"},
            "DefineSpectrumLVS": {"Start": -1, "End": 1, "StepWidth": 0.1, "KinEnergy": 400,
                                  "DwellTime": 0.1, "PassEnergy": 20,
                                  "LensMode": "LowAngularDispersion", "ScanRange": "LargeArea",
                                  "ScanVariable": "Focus Displacement 1 [nu]"},
            "CheckSpectrumFAT": {"StartEnergy": 400, "EndEnergy": 410, "StepWidth": 0.5,
                                 "DwellTime": 0.1, "PassEnergy": 20,
                                 "LensMode": "LowAngularDispersion", "ScanRange": "LargeArea"},
            "CheckSpectrumSFAT": {"StartEnergy": 400, "EndEnergy": 410, "Samples": 10,
                                  "DwellTime": 0.1, "LensMode": "LowAngularDispersion",
                                  "ScanRange": "LargeArea"},
            "CheckSpectrumFRR": {"StartEnergy": 400, "EndEnergy": 410, "StepWidth": 0.5,
                                 "DwellTime": 0.1, "RetardingRatio": 10,
                                 "LensMode": "LowAngularDispersion", "ScanRange": "LargeArea"},
            "CheckSpectrumFE": {"KinEnergy": 400, "Samples": 10, "DwellTime": 0.1,
                                "PassEnergy": 20, "LensMode": "LowAngularDispersion",
                                "ScanRange": "LargeArea"},
            "CheckSpectrumLVS": {"Start": -1, "End": 1, "StepWidth": 0.1, "KinEnergy": 400,
                                 "DwellTime": 0.1, "PassEnergy": 20,
                                 "LensMode": "LowAngularDispersion", "ScanRange": "LargeArea",
                                 "ScanVariable": "Focus Displacement 1 [nu]"},
            "GetAnalyzerParameterInfo": {"ParameterName": "Detector Voltage"},
            "GetAnalyzerParameterValue": {"ParameterName": "Detector Voltage"},
            "SetAnalyzerParameterValue": {"ParameterName": "Detector Voltage", "Value": 0},
            "SetAnalyzerParameterValueDirectly": {"LensMode": "LowAngularDispersion",
                                                   "ScanRange": "LargeArea"},
            "ValidateAnalyzerParameterValueDirectly": {"LensMode": "LowAngularDispersion",
                                                        "ScanRange": "LargeArea"},
            "GetSpectrumParameterInfo": {"ParameterName": "LensMode"},
            "GetSpectrumDataInfo": {"ParameterName": "OrdinateRange"},
            "GetAllDeviceParameterNames": {"DeviceCommand": "X-Ray Dummy.Operate"},
            "GetDeviceParameterInfo": {"DeviceCommand": "X-Ray Dummy.Operate",
                                       "ParameterName": "uanode"},
            "GetDeviceParameterValue": {"DeviceCommand": "X-Ray Dummy.Operate",
                                        "ParameterName": "uanode"},
            "SetDeviceParameterValue": {"DeviceCommand": "X-Ray Dummy.Operate",
                                        "ParameterName": "uanode", "Value": 14000},
            "GetAcquisitionData": {"FromIndex": 0, "ToIndex": 0},
            "CreateDirectDeviceCommand": {"Template": "Dummy"},
            "GetDirectDeviceCommandInfo": {"DeviceCommand": "Dummy.Operate"},
            "GetDirectDeviceParameterInfo": {"DeviceCommand": "Dummy.Operate",
                                              "ParameterName": "x"},
            "GetDirectDeviceParameterValue": {"DeviceCommand": "Dummy.Operate",
                                               "ParameterName": "x"},
            "SetDirectDeviceParameterValue": {"DeviceCommand": "Dummy.Operate",
                                               "ParameterName": "x", "Value": 0},
            "GetDeviceInfo": {"Device": "Analyzer ND"},
            "GetLiveParameterInfo": {"Device": "Analyzer ND",
                                     "Parameter": "Count Rate"},
            "GetLiveParameterValue": {"Device": "Analyzer ND",
                                      "Parameter": "Count Rate"},
        }.get(command)

        response = client.send_command(command, params)
        assert "Error: 101" not in response, (
            f"{command} returned 'unknown command' (Error 101)"
        )
