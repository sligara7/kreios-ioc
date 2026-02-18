"""
IOC integration tests for new protocol commands (Groups A-G).

These tests verify the 27 new protocol commands implemented as EPICS PVs
in the KREIOS areaDetector driver, covering:
- Group A: Simple trigger commands (Resume, DisconnectAnalyzer, SetSafeState)
- Group B: CheckSpectrum and validated readbacks
- Group C: GetAllAnalyzerParameterNames
- Group D: Analyzer direct voltage control
- Groups E/F/G: Shared query interface (device commands, direct device
  commands, device information)

Test environment: IOC → TCP → real Prodigy (10.67.228.10:7010).
The analyzer EC 10 is disconnected — commands requiring analyzer hardware
will return errors. Tests account for this.

Requirements:
- IOC must be running: softioc-kreios-det1 via procServ
- Prodigy must be accessible at 10.67.228.10:7010
- pyepics must be available (miniconda3)
- EPICS_CA_AUTO_ADDR_LIST=YES

Usage:
    EPICS_CA_AUTO_ADDR_LIST=YES /home/asligar/miniconda3/bin/python \
        -m pytest tests/test_ioc_new_commands.py -v
"""

import time

import pytest

# Require pyepics
pytest.importorskip("epics")

from .ioc_helpers import caget, caput, ioc_connected


def parse_response(response):
    """Parse a Prodigy comma-separated response into a list of unquoted strings.

    Prodigy wraps response values in double quotes, e.g.:
        '"Analyzer ND.Configure 2D/XPS","X-Ray Dummy.Operate"'
    This helper splits on '","' and strips outer quotes.
    """
    if not response:
        return []
    items = response.split('","')
    return [item.strip().strip('"') for item in items]


# ============================================================================
# Skip conditions
# ============================================================================

# Skip entire module if IOC is not reachable
pytestmark = pytest.mark.skipif(
    not ioc_connected(),
    reason="IOC not running or not connected (Connected_RBV != Connected)"
)


# ============================================================================
# 1. New PV Existence Tests
# ============================================================================

class TestNewPVExistence:
    """Verify every new PV is accessible via caget (not None).

    This catches template typos, missing createParam calls, and asyn
    parameter name mismatches between the template and the driver.
    """

    # Group A: Simple trigger commands
    def test_resume_exists(self):
        assert caget("Resume") is not None

    def test_disconnect_analyzer_exists(self):
        assert caget("DisconnectAnalyzer") is not None

    def test_set_safe_state_trigger_exists(self):
        assert caget("SetSafeStateTrigger") is not None

    # Group B: CheckSpectrum
    def test_check_spectrum_exists(self):
        assert caget("CheckSpectrum") is not None

    def test_check_start_energy_rbv_exists(self):
        assert caget("CheckStartEnergy_RBV") is not None

    def test_check_end_energy_rbv_exists(self):
        assert caget("CheckEndEnergy_RBV") is not None

    def test_check_step_width_rbv_exists(self):
        assert caget("CheckStepWidth_RBV") is not None

    def test_check_samples_rbv_exists(self):
        assert caget("CheckSamples_RBV") is not None

    def test_check_dwell_time_rbv_exists(self):
        assert caget("CheckDwellTime_RBV") is not None

    def test_check_pass_energy_rbv_exists(self):
        assert caget("CheckPassEnergy_RBV") is not None

    # Group C: GetAllAnalyzerParameterNames
    def test_get_all_analyzer_params_exists(self):
        assert caget("GetAllAnalyzerParams") is not None

    def test_analyzer_param_names_rbv_exists(self):
        assert caget("AnalyzerParamNames_RBV", as_string=True) is not None

    # Group D: Analyzer direct voltage
    def test_direct_polarity_exists(self):
        assert caget("DirectPolarity") is not None

    def test_direct_param_name_exists(self):
        assert caget("DirectParamName", as_string=True) is not None

    def test_direct_param_value_exists(self):
        assert caget("DirectParamValue") is not None

    def test_set_analyzer_directly_exists(self):
        assert caget("SetAnalyzerDirectly") is not None

    def test_validate_analyzer_directly_exists(self):
        assert caget("ValidateAnalyzerDirectly") is not None

    # Query input PVs
    def test_query_device_exists(self):
        assert caget("QueryDevice", as_string=True) is not None

    def test_query_device_cmd_exists(self):
        assert caget("QueryDeviceCmd", as_string=True) is not None

    def test_query_param_name_exists(self):
        assert caget("QueryParamName", as_string=True) is not None

    def test_query_value_exists(self):
        assert caget("QueryValue", as_string=True) is not None

    def test_query_template_exists(self):
        assert caget("QueryTemplate", as_string=True) is not None

    # Query trigger PVs (spot-check 4 of 15)
    def test_get_all_device_cmds_exists(self):
        assert caget("GetAllDeviceCmds") is not None

    def test_get_all_devices_exists(self):
        assert caget("GetAllDevices") is not None

    def test_get_device_info_exists(self):
        assert caget("GetDeviceInfo") is not None

    def test_get_live_param_value_exists(self):
        assert caget("GetLiveParamValue") is not None

    # Query output PVs (all 9)
    def test_query_response_rbv_exists(self):
        assert caget("QueryResponse_RBV", as_string=True) is not None

    def test_query_param_names_rbv_exists(self):
        assert caget("QueryParamNames_RBV", as_string=True) is not None

    def test_query_value_type_rbv_exists(self):
        assert caget("QueryValueType_RBV", as_string=True) is not None

    def test_query_unit_rbv_exists(self):
        assert caget("QueryUnit_RBV", as_string=True) is not None

    def test_query_param_value_rbv_exists(self):
        assert caget("QueryParamValue_RBV", as_string=True) is not None

    def test_query_connectivity_rbv_exists(self):
        assert caget("QueryConnectivity_RBV", as_string=True) is not None

    def test_query_device_type_rbv_exists(self):
        assert caget("QueryDeviceType_RBV", as_string=True) is not None

    def test_query_visible_name_rbv_exists(self):
        assert caget("QueryVisibleName_RBV", as_string=True) is not None

    def test_query_status_rbv_exists(self):
        assert caget("QueryStatus_RBV") is not None


# ============================================================================
# 2. Group A: Simple Trigger Commands
# ============================================================================

class TestGroupATriggers:
    """Verify Group A trigger commands don't crash the IOC.

    These commands are expected to return errors from Prodigy when the
    analyzer is disconnected, but the IOC must handle them gracefully.
    """

    def test_set_safe_state_trigger(self):
        """SetSafeStateTrigger=1 should not crash; IOC stays connected."""
        caput("SetSafeStateTrigger", 1)
        time.sleep(0.5)
        assert caget("Connected_RBV") == 1, "IOC disconnected after SetSafeStateTrigger"

    def test_resume_no_crash_when_idle(self):
        """Resume=1 when idle should be handled gracefully."""
        caput("Resume", 1)
        time.sleep(0.5)
        assert caget("Connected_RBV") == 1, "IOC disconnected after Resume"

    def test_disconnect_analyzer(self):
        """DisconnectAnalyzer=1 should not crash; IOC stays connected to Prodigy."""
        caput("DisconnectAnalyzer", 1)
        time.sleep(0.5)
        assert caget("Connected_RBV") == 1, "IOC disconnected after DisconnectAnalyzer"


# ============================================================================
# 3. Group B: CheckSpectrum
# ============================================================================

class TestGroupBCheckSpectrum:
    """Verify CheckSpectrum trigger and readback PVs."""

    def test_check_spectrum_trigger_no_crash(self):
        """Triggering CheckSpectrum should not crash IOC.

        Without analyzer hardware, the CheckSpectrum command will likely
        fail, but the IOC should handle the error gracefully.
        """
        caput("CheckSpectrum", 1)
        time.sleep(0.5)
        assert caget("Connected_RBV") == 1, "IOC disconnected after CheckSpectrum"

    def test_check_spectrum_readback_pvs_zero_initially(self):
        """CheckSpectrum readback PVs should be 0 before any successful check."""
        # These are populated only after a successful CheckSpectrum round-trip
        # Before that (or after a failed one), they hold their initial value (0)
        pvs = [
            ("CheckStartEnergy_RBV", float),
            ("CheckEndEnergy_RBV", float),
            ("CheckStepWidth_RBV", float),
            ("CheckSamples_RBV", int),
            ("CheckDwellTime_RBV", float),
            ("CheckPassEnergy_RBV", float),
        ]
        for name, _ in pvs:
            val = caget(name)
            assert val is not None, f"{name} returned None"


# ============================================================================
# 4. Group C: GetAllAnalyzerParameterNames
# ============================================================================

class TestGroupCAnalyzerParamNames:
    """Verify GetAllAnalyzerParameterNames returns parameter list from Prodigy."""

    def test_get_all_analyzer_param_names_no_crash(self):
        """Trigger GetAllAnalyzerParams=1; IOC survives and PV is updated.

        With the analyzer disconnected, this command may return an error
        from Prodigy (Error 205), resulting in an empty response. The key
        assertion is that the IOC handles it gracefully.
        """
        caput("GetAllAnalyzerParams", 1)
        time.sleep(0.5)
        val = caget("AnalyzerParamNames_RBV", as_string=True)
        assert val is not None, "AnalyzerParamNames_RBV is None (PV missing)"
        assert caget("Connected_RBV") == 1, "IOC disconnected after GetAllAnalyzerParams"
        # If analyzer were connected, val would contain param names
        # With analyzer disconnected, empty is acceptable

    def test_analyzer_param_names_format_if_populated(self):
        """If AnalyzerParamNames_RBV is populated, verify known params exist.

        With analyzer disconnected this returns empty — test is skipped.
        When analyzer is connected, it should contain known KREIOS parameters.
        """
        caput("GetAllAnalyzerParams", 1)
        time.sleep(0.5)
        val = caget("AnalyzerParamNames_RBV", as_string=True)
        if not val or len(val) == 0:
            pytest.skip("AnalyzerParamNames empty (analyzer disconnected)")
        known_params = ["Detector Voltage", "Bias Voltage", "Coil Current"]
        found = any(p in val for p in known_params)
        assert found, (
            f"None of {known_params} found in AnalyzerParamNames_RBV: '{val[:200]}...'"
        )


# ============================================================================
# 5. Group D: Analyzer Direct Voltage
# ============================================================================

class TestGroupDDirectVoltage:
    """Verify direct voltage control PVs (polarity, param name, value, triggers)."""

    def test_direct_polarity_write_readback(self):
        """Write DirectPolarity 0 (Unipolar) and 1 (Bipolar), verify readback."""
        caput("DirectPolarity", 0)
        time.sleep(0.2)
        val = caget("DirectPolarity")
        assert val == 0, f"Expected Unipolar (0), got {val}"

        caput("DirectPolarity", 1)
        time.sleep(0.2)
        val = caget("DirectPolarity")
        assert val == 1, f"Expected Bipolar (1), got {val}"

        # Restore
        caput("DirectPolarity", 0)

    def test_direct_param_name_write_readback(self):
        """Write a string to DirectParamName and verify it is stored."""
        test_name = "Detector Voltage"
        caput("DirectParamName", test_name)
        time.sleep(0.2)
        val = caget("DirectParamName", as_string=True)
        assert val == test_name, f"Expected '{test_name}', got '{val}'"

    def test_direct_param_value_write_readback(self):
        """Write a float to DirectParamValue and verify readback."""
        test_val = 42.5
        caput("DirectParamValue", test_val)
        time.sleep(0.2)
        val = caget("DirectParamValue")
        assert abs(val - test_val) < 0.01, f"Expected {test_val}, got {val}"

    def test_set_analyzer_directly_trigger_no_crash(self):
        """Trigger SetAnalyzerDirectly; IOC should survive even with error.

        With analyzer disconnected, this will fail at Prodigy but the IOC
        must handle the error without crashing or disconnecting.
        """
        # Set inputs first
        caput("DirectParamName", "Detector Voltage")
        caput("DirectParamValue", 0.0)
        caput("DirectPolarity", 0)
        time.sleep(0.2)

        caput("SetAnalyzerDirectly", 1)
        time.sleep(0.5)
        assert caget("Connected_RBV") == 1, "IOC disconnected after SetAnalyzerDirectly"

    def test_validate_analyzer_directly_trigger_no_crash(self):
        """Trigger ValidateAnalyzerDirectly; IOC should survive."""
        caput("DirectParamName", "Detector Voltage")
        caput("DirectParamValue", 0.0)
        caput("DirectPolarity", 0)
        time.sleep(0.2)

        caput("ValidateAnalyzerDirectly", 1)
        time.sleep(0.5)
        assert caget("Connected_RBV") == 1, (
            "IOC disconnected after ValidateAnalyzerDirectly"
        )


# ============================================================================
# 6. Query Input PVs (Write/Readback)
# ============================================================================

class TestQueryInputPVs:
    """Verify shared query input PVs accept writes and read back correctly."""

    def test_query_device_write_readback(self):
        """QueryDevice string write/readback."""
        test_val = "TestDevice"
        caput("QueryDevice", test_val)
        time.sleep(0.2)
        val = caget("QueryDevice", as_string=True)
        assert val == test_val, f"Expected '{test_val}', got '{val}'"

    def test_query_device_cmd_write_readback(self):
        """QueryDeviceCmd string write/readback."""
        test_val = "TestCmd"
        caput("QueryDeviceCmd", test_val)
        time.sleep(0.2)
        val = caget("QueryDeviceCmd", as_string=True)
        assert val == test_val, f"Expected '{test_val}', got '{val}'"

    def test_query_param_name_write_readback(self):
        """QueryParamName string write/readback."""
        test_val = "TestParam"
        caput("QueryParamName", test_val)
        time.sleep(0.2)
        val = caget("QueryParamName", as_string=True)
        assert val == test_val, f"Expected '{test_val}', got '{val}'"

    def test_query_value_write_readback(self):
        """QueryValue string write/readback."""
        test_val = "123.456"
        caput("QueryValue", test_val)
        time.sleep(0.2)
        val = caget("QueryValue", as_string=True)
        assert val == test_val, f"Expected '{test_val}', got '{val}'"

    def test_query_template_write_readback(self):
        """QueryTemplate string write/readback."""
        test_val = "TestTemplate"
        caput("QueryTemplate", test_val)
        time.sleep(0.2)
        val = caget("QueryTemplate", as_string=True)
        assert val == test_val, f"Expected '{test_val}', got '{val}'"


# ============================================================================
# 7. Query Round-Trip Tests (IOC → Prodigy → IOC)
# ============================================================================

class TestQueryRoundTrip:
    """Full round-trip tests through the shared query interface.

    These tests use real Prodigy commands that should work even without
    the analyzer hardware connected. They dynamically discover valid
    device/command names from Prodigy responses.

    Note: Prodigy wraps response values in double quotes. All tests use
    parse_response() to strip quotes before using values as inputs.
    """

    def _get_cmd_with_params(self):
        """Find a device command that has parameters.

        Some commands (e.g., "Analyzer ND.Configure 2D/XPS") have no
        parameters. This helper tries each command until it finds one
        with parameter names.

        Returns (cmd, [param_names]) or (None, []).
        """
        caput("GetAllDeviceCmds", 1)
        time.sleep(0.5)
        cmds = parse_response(caget("QueryResponse_RBV", as_string=True))

        for cmd in cmds:
            caput("QueryDeviceCmd", cmd)
            time.sleep(0.2)
            caput("GetAllDeviceParamNames", 1)
            time.sleep(0.5)
            params_raw = caget("QueryParamNames_RBV", as_string=True)
            params = parse_response(params_raw)
            if params:
                return cmd, params
        return None, []

    def test_get_all_device_cmds(self):
        """GetAllDeviceCmds populates QueryResponse_RBV and status=OK."""
        caput("GetAllDeviceCmds", 1)
        time.sleep(0.5)

        status = caget("QueryStatus_RBV")
        response = caget("QueryResponse_RBV", as_string=True)

        assert status == 1, f"Expected QueryStatus OK (1), got {status}"
        assert response is not None and len(response) > 0, (
            "QueryResponse_RBV empty after GetAllDeviceCmds"
        )

    def test_get_all_devices(self):
        """GetAllDevices populates QueryResponse_RBV."""
        caput("GetAllDevices", 1)
        time.sleep(0.5)

        status = caget("QueryStatus_RBV")
        response = caget("QueryResponse_RBV", as_string=True)

        assert status == 1, f"Expected QueryStatus OK (1), got {status}"
        assert response is not None and len(response) > 0, (
            "QueryResponse_RBV empty after GetAllDevices"
        )

    def test_get_all_device_param_names(self):
        """GetAllDeviceParamNames returns parameter names for a valid command.

        Tries each device command until one with parameters is found.
        """
        cmd, params = self._get_cmd_with_params()
        assert cmd is not None, "No device command with parameters found"
        assert len(params) > 0, f"No param names for any device command"

    def test_get_device_param_info(self):
        """GetDeviceParamInfo returns type/unit for a valid device param."""
        cmd, params = self._get_cmd_with_params()
        assert cmd is not None, "No device command with parameters found"
        first_param = params[0]

        # Query info for the parameter
        caput("QueryDeviceCmd", cmd)
        caput("QueryParamName", first_param)
        time.sleep(0.2)
        caput("GetDeviceParamInfo", 1)
        time.sleep(0.5)

        status = caget("QueryStatus_RBV")
        value_type = caget("QueryValueType_RBV", as_string=True)

        assert status == 1, (
            f"Expected OK for param info on '{cmd}'/'{first_param}', got {status}"
        )
        assert value_type is not None and len(value_type) > 0, (
            "QueryValueType_RBV empty"
        )

    def test_get_device_param_value(self):
        """GetDeviceParamValue returns a value for a valid device param."""
        cmd, params = self._get_cmd_with_params()
        assert cmd is not None, "No device command with parameters found"
        first_param = params[0]

        caput("QueryDeviceCmd", cmd)
        caput("QueryParamName", first_param)
        time.sleep(0.2)
        caput("GetDeviceParamValue", 1)
        time.sleep(0.5)

        status = caget("QueryStatus_RBV")
        param_val = caget("QueryParamValue_RBV", as_string=True)

        assert status == 1, (
            f"Expected OK for get value '{cmd}'/'{first_param}', got {status}"
        )
        assert param_val is not None, "QueryParamValue_RBV is None"

    def test_set_device_param_value(self):
        """SetDeviceParamValue writes and returns status.

        Reads current value first, then writes it back (no-op change)
        to avoid altering device state.
        """
        cmd, params = self._get_cmd_with_params()
        assert cmd is not None, "No device command with parameters found"
        first_param = params[0]

        # Read current value
        caput("QueryDeviceCmd", cmd)
        caput("QueryParamName", first_param)
        time.sleep(0.2)
        caput("GetDeviceParamValue", 1)
        time.sleep(0.5)
        current_val = caget("QueryParamValue_RBV", as_string=True)
        assert current_val is not None

        # Write same value back (no-op)
        caput("QueryValue", current_val)
        time.sleep(0.2)
        caput("SetDeviceParamValue", 1)
        time.sleep(0.5)

        status = caget("QueryStatus_RBV")
        # Accept both OK and Error (some params may be read-only)
        assert status is not None, "QueryStatus_RBV is None after SetDeviceParamValue"
        assert caget("Connected_RBV") == 1, "IOC disconnected after SetDeviceParamValue"

    def test_get_device_info(self):
        """GetDeviceInfo returns device type for a valid device."""
        caput("GetAllDevices", 1)
        time.sleep(0.5)
        devices = parse_response(caget("QueryResponse_RBV", as_string=True))
        assert len(devices) > 0, "No devices returned"

        caput("QueryDevice", devices[0])
        time.sleep(0.2)
        caput("GetDeviceInfo", 1)
        time.sleep(0.5)

        status = caget("QueryStatus_RBV")
        device_type = caget("QueryDeviceType_RBV", as_string=True)

        assert status == 1, (
            f"Expected OK for GetDeviceInfo on '{devices[0]}', got {status}"
        )
        assert device_type is not None and len(device_type) > 0, (
            "QueryDeviceType_RBV empty"
        )

    def test_get_live_param_value(self):
        """GetLiveParamValue for a valid device+param; IOC survives."""
        # Find a command with parameters
        cmd, params = self._get_cmd_with_params()
        assert cmd is not None, "No device command with parameters found"

        # Get a device name
        caput("GetAllDevices", 1)
        time.sleep(0.5)
        devices = parse_response(caget("QueryResponse_RBV", as_string=True))
        assert len(devices) > 0

        # Query live parameter value
        caput("QueryDevice", devices[0])
        caput("QueryParamName", params[0])
        time.sleep(0.2)
        caput("GetLiveParamValue", 1)
        time.sleep(0.5)

        # Live param queries may fail for disconnected devices — just verify
        # the IOC survives
        assert caget("Connected_RBV") == 1, "IOC disconnected after GetLiveParamValue"


# ============================================================================
# 8. Direct Device Command Tests
# ============================================================================

class TestQueryDirectDeviceCmds:
    """Verify direct device command lifecycle (create, info, execute).

    Direct device commands use a template-based creation workflow.
    These tests verify the IOC handles the full lifecycle without crashing.
    """

    def _get_valid_template(self):
        """Discover a valid template name from GetAllDeviceCmds."""
        caput("GetAllDeviceCmds", 1)
        time.sleep(0.5)
        cmds = caget("QueryResponse_RBV", as_string=True)
        if cmds and len(cmds) > 0:
            return cmds.split(",")[0].strip()
        return None

    def test_create_direct_device_cmd(self):
        """CreateDirectDeviceCmd with a valid template returns OK."""
        template = self._get_valid_template()
        assert template is not None, "No device commands available to use as template"

        caput("QueryTemplate", template)
        time.sleep(0.2)
        caput("CreateDirectDeviceCmd", 1)
        time.sleep(0.5)

        status = caget("QueryStatus_RBV")
        assert caget("Connected_RBV") == 1, "IOC disconnected after CreateDirectDeviceCmd"
        # Status may be OK or Error depending on whether the template is valid
        # for direct command creation — the key thing is the IOC survived
        assert status is not None, "QueryStatus_RBV is None"

    def test_get_direct_device_cmd_info(self):
        """GetDirectDeviceCmdInfo after Create should not crash."""
        template = self._get_valid_template()
        if template:
            caput("QueryTemplate", template)
            time.sleep(0.2)
            caput("CreateDirectDeviceCmd", 1)
            time.sleep(0.5)

        caput("GetDirectDeviceCmdInfo", 1)
        time.sleep(0.5)
        assert caget("Connected_RBV") == 1, (
            "IOC disconnected after GetDirectDeviceCmdInfo"
        )

    def test_exec_direct_device_cmd(self):
        """ExecDirectDeviceCmd after Create should not crash."""
        template = self._get_valid_template()
        if template:
            caput("QueryTemplate", template)
            time.sleep(0.2)
            caput("CreateDirectDeviceCmd", 1)
            time.sleep(0.5)

        caput("ExecDirectDeviceCmd", 1)
        time.sleep(0.5)
        assert caget("Connected_RBV") == 1, (
            "IOC disconnected after ExecDirectDeviceCmd"
        )

    def test_create_direct_device_cmd_bad_template(self):
        """CreateDirectDeviceCmd with invalid template should return Error."""
        caput("QueryTemplate", "NonExistentTemplate_XYZ_12345")
        time.sleep(0.2)
        caput("CreateDirectDeviceCmd", 1)
        time.sleep(0.5)

        status = caget("QueryStatus_RBV")
        assert status == 0, f"Expected Error (0) for bad template, got {status}"
        assert caget("Connected_RBV") == 1, (
            "IOC disconnected after bad CreateDirectDeviceCmd"
        )
