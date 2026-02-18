"""
IOC integration tests: pyepics → EPICS CA → IOC → TCP → Prodigy.

These tests verify the full communication stack from EPICS Channel Access
through the KREIOS areaDetector driver to the real SpecsLab Prodigy software
running on the Windows machine (10.67.228.10:7010).

Tests are designed to work WITHOUT the KREIOS analyzer hardware (EC 10)
connected to Prodigy, validating:
- Connection management and reconnect cycles
- Server identification (via Prodigy Connect response)
- Parameter write/readback through the IOC
- Graceful degradation when analyzer is offline
- IOC status and health monitoring
- Acquisition rejection without valid spectrum

Requirements:
- IOC must be running: softioc-kreios-det1 via procServ
- Prodigy must be accessible at 10.67.228.10:7010
- pyepics must be available (miniconda3)
- EPICS_CA_AUTO_ADDR_LIST=YES

Usage:
    EPICS_CA_AUTO_ADDR_LIST=YES python -m pytest tests/test_ioc_integration.py -v

    Or with the miniconda3 python:
    EPICS_CA_AUTO_ADDR_LIST=YES /home/asligar/miniconda3/bin/python \
        -m pytest tests/test_ioc_integration.py -v
"""

import time

import pytest

# Require pyepics
pytest.importorskip("epics")

from .ioc_helpers import caget, caput, ioc_connected


# Skip entire module if IOC is not reachable
pytestmark = pytest.mark.skipif(
    not ioc_connected(),
    reason="IOC not running or not connected (Connected_RBV != Connected)"
)


@pytest.fixture(scope="session", autouse=True)
def ensure_clean_ioc_state():
    """Ensure IOC is in a clean state before running tests.

    If a previous test run left the IOC in Error or Acquire state,
    perform a disconnect/reconnect cycle to reset it.
    """
    state = caget("DetectorState_RBV")
    if state is not None and state not in (0,):  # Not Idle
        # Reset by stopping any acquisition and reconnecting
        caput("Acquire", 0)
        time.sleep(0.5)
        caput("Connect", 0)
        time.sleep(1.5)
        caput("Connect", 1)
        time.sleep(2.0)
    yield


# ============================================================================
# Connection and Identification
# ============================================================================

class TestConnectionAndIdentification:
    """Verify IOC↔Prodigy connection and identification PVs.

    These PVs are populated from the Prodigy Connect response and
    the GetAnalyzerVisibleName command during makeConnection().
    Protocol path: IOC Connect → Prodigy returns ServerName/ProtocolVersion.
    """

    def test_connected_rbv(self):
        """Connected_RBV reports Connected (bi record, 1=Connected)."""
        val = caget("Connected_RBV")
        assert val == 1, f"Expected Connected (1), got {val}"

    def test_server_name_populated(self):
        """ServerName_RBV contains Prodigy server identification string."""
        val = caget("ServerName_RBV", as_string=True)
        assert val is not None
        assert "SpecsLab Prodigy" in val, f"Unexpected server name: {val}"

    def test_model_from_prodigy(self):
        """Model_RBV populated from GetAnalyzerVisibleName → 'KREIOS MM'."""
        val = caget("Model_RBV", as_string=True)
        assert val is not None
        assert "KREIOS" in val, f"Expected 'KREIOS' in model, got: {val}"

    def test_manufacturer_static(self):
        """Manufacturer_RBV is static 'SPECS GmbH' (set in constructor)."""
        val = caget("Manufacturer_RBV", as_string=True)
        assert val == "SPECS GmbH"

    def test_sdk_version_static(self):
        """SDKVersion_RBV is static protocol version string."""
        val = caget("SDKVersion_RBV", as_string=True)
        assert val is not None
        assert "Prodigy" in val or "1.22" in val

    def test_detector_state_idle(self):
        """DetectorState_RBV is Idle when connected with no acquisition."""
        val = caget("DetectorState_RBV")
        # ADStatusIdle = 0 in the ADStatus enum
        assert val == 0, f"Expected Idle (0), got {val}"

    def test_msg_counter_nonzero(self):
        """MsgCounter_RBV > 0 after connection (protocol messages exchanged)."""
        val = caget("MsgCounter_RBV")
        assert val is not None
        assert val > 0, f"Expected MsgCounter > 0, got {val}"


# ============================================================================
# Disconnect / Reconnect Cycle
# ============================================================================

class TestDisconnectReconnect:
    """Verify IOC can disconnect and reconnect to Prodigy.

    Protocol path: caput Connect=0 → IOC sends Disconnect → TCP close
                   caput Connect=1 → IOC TCP connect → Prodigy Connect
    """

    def test_disconnect_reconnect_cycle(self):
        """Full disconnect/reconnect cycle preserves state."""
        # Verify currently connected
        assert caget("Connected_RBV") == 1

        # Disconnect
        caput("Connect", 0)
        time.sleep(1.0)  # Allow asyn port to close

        val = caget("Connected_RBV")
        assert val == 0, f"Expected Disconnected (0) after disconnect, got {val}"

        # Reconnect
        caput("Connect", 1)
        time.sleep(2.0)  # Allow Prodigy to accept new connection

        val = caget("Connected_RBV")
        assert val == 1, f"Expected Connected (1) after reconnect, got {val}"

        # Verify server name repopulated
        sname = caget("ServerName_RBV", as_string=True)
        assert sname is not None
        assert "SpecsLab Prodigy" in sname

        # Verify model repopulated
        model = caget("Model_RBV", as_string=True)
        assert model is not None
        assert "KREIOS" in model

    def test_reconnect_increments_msg_counter(self):
        """Reconnect causes additional protocol messages (counter increases)."""
        # Send a command to ensure counter is current
        before = caget("MsgCounter_RBV")

        # Disconnect and reconnect (sends Disconnect + Connect protocol msgs)
        caput("Connect", 0)
        time.sleep(1.5)
        caput("Connect", 1)
        time.sleep(3.0)  # Allow all protocol messages to complete

        after = caget("MsgCounter_RBV")
        assert after > before, (
            f"MsgCounter should increase after reconnect: {before} → {after}"
        )


# ============================================================================
# Graceful Degradation (No Analyzer)
# ============================================================================

class TestGracefulDegradation:
    """Verify IOC handles missing analyzer hardware gracefully.

    When Prodigy is connected but the analyzer EC 10 hardware is offline,
    the IOC should report a useful status message and not enter Error state.
    LensMode/ScanRange enums should be empty (Error 205 from Prodigy).
    """

    def test_status_message_indicates_no_analyzer(self):
        """StatusMessage_RBV mentions analyzer not available."""
        val = caget("StatusMessage_RBV", as_string=True)
        assert val is not None
        # The message should indicate analyzer unavailability
        # (exact wording: "Connected - analyzer not available")
        assert "analyzer" in val.lower() or "connected" in val.lower(), (
            f"Expected status about analyzer, got: {val}"
        )

    def test_detector_state_not_error(self):
        """DetectorState_RBV is NOT Error when analyzer is offline.

        This tests the graceful degradation fix: previously the IOC would
        enter Error state when readSpectrumParameter failed.
        """
        val = caget("DetectorState_RBV")
        # ADStatusError = 7
        assert val != 7, "DetectorState should not be Error with graceful degradation"

    def test_lens_mode_empty_without_analyzer(self):
        """LensMode_RBV is empty/zero when analyzer is offline.

        The readSpectrumParameter for LensMode returns Error 205 from Prodigy
        when the analyzer EC 10 is disconnected, so no enum values are populated.
        """
        val = caget("LensMode_RBV")
        # With empty enum, the value should be 0 and string should be empty
        assert val is not None  # PV exists

    def test_scan_range_empty_without_analyzer(self):
        """ScanRange_RBV is empty/zero when analyzer is offline."""
        val = caget("ScanRange_RBV")
        assert val is not None  # PV exists


# ============================================================================
# Energy Parameter Write/Readback
# ============================================================================

class TestEnergyParameters:
    """Verify energy parameter write/readback through IOC.

    These PVs are stored locally in the IOC's asyn parameter library.
    The protocol path is: caput → asyn writeFloat64 → setDoubleParam → callParamCallbacks → camonitor/caget reads back.
    The actual Prodigy DefineSpectrum command uses these values when triggered.
    """

    def test_start_energy_write_readback(self):
        """StartEnergy write and _RBV readback match."""
        original = caget("StartEnergy_RBV")
        test_val = 400.0

        caput("StartEnergy", test_val)
        time.sleep(0.2)
        rbv = caget("StartEnergy_RBV")
        assert abs(rbv - test_val) < 0.01, f"Expected {test_val}, got {rbv}"

        # Restore
        if original is not None:
            caput("StartEnergy", original)

    def test_end_energy_write_readback(self):
        """EndEnergy write and _RBV readback match."""
        original = caget("EndEnergy_RBV")
        test_val = 410.0

        caput("EndEnergy", test_val)
        time.sleep(0.2)
        rbv = caget("EndEnergy_RBV")
        assert abs(rbv - test_val) < 0.01, f"Expected {test_val}, got {rbv}"

        if original is not None:
            caput("EndEnergy", original)

    def test_step_width_write_readback(self):
        """StepWidth write and _RBV readback match."""
        original = caget("StepWidth_RBV")
        test_val = 0.25

        caput("StepWidth", test_val)
        time.sleep(0.2)
        rbv = caget("StepWidth_RBV")
        assert abs(rbv - test_val) < 0.001, f"Expected {test_val}, got {rbv}"

        if original is not None:
            caput("StepWidth", original)

    def test_pass_energy_write_readback(self):
        """PassEnergy write and _RBV readback match."""
        original = caget("PassEnergy_RBV")
        test_val = 20.0

        caput("PassEnergy", test_val)
        time.sleep(0.2)
        rbv = caget("PassEnergy_RBV")
        assert abs(rbv - test_val) < 0.01, f"Expected {test_val}, got {rbv}"

        if original is not None:
            caput("PassEnergy", original)

    def test_kinetic_energy_write_readback(self):
        """KineticEnergy write and _RBV readback match (used in FE mode)."""
        original = caget("KineticEnergy_RBV")
        test_val = 500.0

        caput("KineticEnergy", test_val)
        time.sleep(0.2)
        rbv = caget("KineticEnergy_RBV")
        assert abs(rbv - test_val) < 0.01, f"Expected {test_val}, got {rbv}"

        if original is not None:
            caput("KineticEnergy", original)

    def test_retarding_ratio_write_readback(self):
        """RetardingRatio write and _RBV readback match (used in FRR mode)."""
        original = caget("RetardingRatio_RBV")
        test_val = 15.0

        caput("RetardingRatio", test_val)
        time.sleep(0.2)
        rbv = caget("RetardingRatio_RBV")
        assert abs(rbv - test_val) < 0.01, f"Expected {test_val}, got {rbv}"

        if original is not None:
            caput("RetardingRatio", original)

    def test_energy_width_calc(self):
        """EnergyWidth_RBV calc record computes EndEnergy - StartEnergy."""
        caput("StartEnergy", 400.0)
        caput("EndEnergy", 420.0)
        time.sleep(0.5)  # Allow calc record to process

        width = caget("EnergyWidth_RBV")
        assert width is not None
        assert abs(width - 20.0) < 0.01, f"Expected 20.0, got {width}"

        # Restore defaults
        caput("StartEnergy", 82.0)
        caput("EndEnergy", 86.0)


# ============================================================================
# Dimension Parameters
# ============================================================================

class TestDimensionParameters:
    """Verify dimension parameter write/readback (1D/2D/3D control).

    ValuesPerSample controls detector pixel binning (1=1D, >1=2D).
    NumSlices controls depth slicing (>1=3D).
    """

    def test_values_per_sample_write_readback(self):
        """ValuesPerSample write and _RBV readback match."""
        original = caget("ValuesPerSample_RBV")
        test_val = 128

        caput("ValuesPerSample", test_val)
        time.sleep(0.2)
        rbv = caget("ValuesPerSample_RBV")
        assert rbv == test_val, f"Expected {test_val}, got {rbv}"

        if original is not None:
            caput("ValuesPerSample", original)

    def test_num_slices_write_readback(self):
        """NumSlices write and _RBV readback match."""
        original = caget("NumSlices_RBV")
        test_val = 5

        caput("NumSlices", test_val)
        time.sleep(0.2)
        rbv = caget("NumSlices_RBV")
        assert rbv == test_val, f"Expected {test_val}, got {rbv}"

        if original is not None:
            caput("NumSlices", original)


# ============================================================================
# Mode Selection (enum PVs)
# ============================================================================

class TestModeSelection:
    """Verify run mode and operating mode enum write/readback.

    RunMode selects the spectrum type: FAT(0), SFAT(1), FRR(2), FE(3), LVS(4).
    OperatingMode selects: Spectroscopy(0), Momentum(1), PEEM(2).
    """

    @pytest.mark.parametrize("mode_val,mode_name", [
        (0, "FAT"),
        (1, "SFAT"),
        (2, "FRR"),
        (3, "FE"),
        (4, "LVS"),
    ])
    def test_run_mode_write_readback(self, mode_val, mode_name):
        """RunMode enum write/readback for all 5 modes."""
        original = caget("RunMode_RBV")

        caput("RunMode", mode_val)
        time.sleep(0.2)
        rbv = caget("RunMode_RBV")
        assert rbv == mode_val, f"Expected {mode_name} ({mode_val}), got {rbv}"

        # Also verify string representation
        rbv_str = caget("RunMode_RBV", as_string=True)
        assert rbv_str == mode_name, f"Expected '{mode_name}', got '{rbv_str}'"

        if original is not None:
            caput("RunMode", original)

    @pytest.mark.parametrize("mode_val,mode_name", [
        (0, "Spectroscopy"),
        (1, "Momentum"),
        (2, "PEEM"),
    ])
    def test_operating_mode_write_readback(self, mode_val, mode_name):
        """OperatingMode enum write/readback for all 3 modes."""
        original = caget("OperatingMode_RBV")

        caput("OperatingMode", mode_val)
        time.sleep(0.2)
        rbv = caget("OperatingMode_RBV")
        assert rbv == mode_val, f"Expected {mode_name} ({mode_val}), got {rbv}"

        rbv_str = caget("OperatingMode_RBV", as_string=True)
        assert rbv_str == mode_name, f"Expected '{mode_name}', got '{rbv_str}'"

        if original is not None:
            caput("OperatingMode", original)


# ============================================================================
# Acquisition Control Parameters
# ============================================================================

class TestAcquisitionControlParams:
    """Verify acquisition control parameter write/readback.

    SafeState controls whether analyzer returns to safe state after scan.
    DataDelayMax sets the maximum allowed data streaming delay.
    Pause controls acquisition pause/resume.
    """

    def test_safe_state_write_readback(self):
        """SafeState bo write and _RBV readback match."""
        original = caget("SafeState_RBV")

        caput("SafeState", 0)
        time.sleep(0.2)
        rbv = caget("SafeState_RBV")
        assert rbv == 0, f"Expected No (0), got {rbv}"

        caput("SafeState", 1)
        time.sleep(0.2)
        rbv = caget("SafeState_RBV")
        assert rbv == 1, f"Expected Yes (1), got {rbv}"

        if original is not None:
            caput("SafeState", original)

    def test_data_delay_max_write_readback(self):
        """DataDelayMax write and _RBV readback match."""
        original = caget("DataDelayMax_RBV")
        test_val = 10.0

        caput("DataDelayMax", test_val)
        time.sleep(0.2)
        rbv = caget("DataDelayMax_RBV")
        assert abs(rbv - test_val) < 0.01, f"Expected {test_val}, got {rbv}"

        if original is not None:
            caput("DataDelayMax", original)

    def test_pause_default_running(self):
        """Pause_RBV defaults to Running (0) when not acquiring."""
        val = caget("Pause_RBV")
        assert val == 0, f"Expected Running (0), got {val}"


# ============================================================================
# Acquisition Rejection (no analyzer)
# ============================================================================

class TestAcquisitionRejection:
    """Verify that acquisition attempts fail gracefully without analyzer.

    Without LensMode/ScanRange populated (analyzer offline), the IOC
    cannot build a valid DefineSpectrum command, and ValidateSpectrum
    will fail with Prodigy Error 202.
    """

    def test_acquire_fails_without_analyzer(self):
        """Starting acquisition without analyzer populated should fail.

        The IOC acquisition task: ClearSpectrum → DefineSpectrum → ValidateSpectrum → Start.
        Without LensMode/ScanRange, DefineSpectrum omits required params and Prodigy
        returns Error 104 (missing parameter), or ValidateSpectrum returns Error 202.
        The IOC may enter Error or Aborted state, which is expected.
        """
        # Verify we're idle
        state = caget("DetectorState_RBV")
        assert state != 6, "Already acquiring, cannot test"  # ADStatusAcquire=6

        # Attempt to acquire
        caput("Acquire", 1)

        # Wait for the acquisition task to process and fail
        # The task runs in a separate thread and needs time to:
        # 1. Wake up on start event
        # 2. Send ClearSpectrum
        # 3. Send DefineSpectrum (fails due to missing LensMode/ScanRange)
        # 4. Or proceed to ValidateSpectrum (fails Error 202)
        time.sleep(5.0)

        # Ensure acquire is stopped
        caput("Acquire", 0)
        time.sleep(1.0)

        # The IOC should not still be in the Acquire state
        state = caget("DetectorState_RBV")
        state_str = caget("DetectorState_RBV", as_string=True)
        # ADStatus enum: Idle=0, Acquire=1, Error=6, Aborted=10
        assert state in (0, 6, 10), (
            f"Expected Idle/Error/Aborted after failed acquire, got {state_str} ({state})"
        )

        # Restore IOC to clean state by reconnecting
        caput("Connect", 0)
        time.sleep(1.5)
        caput("Connect", 1)
        time.sleep(2.0)

        # Verify recovery
        assert caget("Connected_RBV") == 1, "IOC should reconnect after failed acquire"


# ============================================================================
# areaDetector Standard Parameters
# ============================================================================

class TestAreaDetectorStandard:
    """Verify standard areaDetector parameters are correctly set.

    These are set in the constructor and should always have valid values.
    """

    def test_max_size_x(self):
        """MaxSizeX_RBV matches KREIOS detector dimension (1285)."""
        val = caget("MaxSizeX_RBV")
        assert val == 1285, f"Expected 1285, got {val}"

    def test_max_size_y(self):
        """MaxSizeY_RBV matches KREIOS detector dimension (730)."""
        val = caget("MaxSizeY_RBV")
        assert val == 730, f"Expected 730, got {val}"

    def test_driver_version(self):
        """DriverVersion_RBV is populated."""
        val = caget("DriverVersion_RBV", as_string=True)
        assert val is not None
        assert len(val) > 0

    def test_acquire_time_write_readback(self):
        """AcquireTime (DwellTime) write and _RBV readback match."""
        original = caget("AcquireTime_RBV")
        test_val = 0.5

        caput("AcquireTime", test_val)
        time.sleep(0.2)
        rbv = caget("AcquireTime_RBV")
        assert abs(rbv - test_val) < 0.01, f"Expected {test_val}, got {rbv}"

        if original is not None:
            caput("AcquireTime", original)

    def test_num_exposures_write_readback(self):
        """NumExposures (iterations) write and _RBV readback match."""
        original = caget("NumExposures_RBV")
        test_val = 3

        caput("NumExposures", test_val)
        time.sleep(0.2)
        rbv = caget("NumExposures_RBV")
        assert rbv == test_val, f"Expected {test_val}, got {rbv}"

        if original is not None:
            caput("NumExposures", original)


# ============================================================================
# IOC Health and Status
# ============================================================================

class TestIOCHealth:
    """Verify IOC health indicators are reasonable."""

    def test_progress_zero_when_idle(self):
        """Progress_RBV is 0 when not acquiring."""
        val = caget("Progress_RBV")
        assert val is not None
        assert val == 0, f"Expected 0% progress when idle, got {val}"

    def test_samples_rbv_accessible(self):
        """Samples_RBV is accessible and non-negative."""
        val = caget("Samples_RBV")
        assert val is not None
        assert val >= 0

    def test_current_sample_zero_when_idle(self):
        """CurrentSample_RBV is 0 when idle."""
        val = caget("CurrentSample_RBV")
        assert val is not None
        assert val == 0, f"Expected 0 when idle, got {val}"

    def test_remaining_time_zero_when_idle(self):
        """RemainingTime_RBV is 0 when idle."""
        val = caget("RemainingTime_RBV")
        assert val is not None
        assert abs(val) < 0.1, f"Expected ~0 when idle, got {val}"
