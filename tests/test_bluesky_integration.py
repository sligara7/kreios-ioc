"""
Integration tests for KREIOS-150 IOC with ophyd and Bluesky.

These tests run against the real EPICS areaDetector IOC to verify:
1. PV connectivity via Channel Access
2. 1D spectrum acquisition (XPS/UPS)
3. 2D image acquisition (ARPES/momentum)
4. Ophyd device integration
5. Bluesky plan execution

Prerequisites:
    Start the KREIOS IOC containers:
    cd docker && docker compose --profile full up -d

    Wait for IOC to be ready (~30s for first start):
    docker compose logs -f ioc

Run tests:
    KREIOS_IOC_AVAILABLE=1 pytest tests/test_bluesky_integration.py -v

    Or auto-detect:
    pytest tests/test_bluesky_integration.py -v
"""

import os
import time

import pytest

# Set EPICS environment for Channel Access
os.environ.setdefault("EPICS_CA_ADDR_LIST", "localhost")
os.environ.setdefault("EPICS_CA_AUTO_ADDR_LIST", "NO")
os.environ.setdefault("EPICS_CA_MAX_ARRAY_BYTES", "10000000")

# IMPORTANT: Import ophyd BEFORE any epics usage to ensure pyepics uses
# ophyd's PyepicsShimPV class which has get_all_metadata_callback().
# Without this, epics.PV objects created before ophyd import will lack
# the method ophyd expects, causing AttributeError.
import ophyd  # noqa: E402, F401 - must be before epics import

# Test configuration
KREIOS_PREFIX = os.environ.get("KREIOS_PREFIX", "KREIOS:cam1:")
KREIOS_IOC_AVAILABLE = os.environ.get("KREIOS_IOC_AVAILABLE", "0") == "1"


def check_kreios_ioc_running() -> bool:
    """Check if the KREIOS IOC is running and accessible."""
    try:
        import epics

        pv = epics.PV(f"{KREIOS_PREFIX}Manufacturer_RBV", connection_timeout=3.0)
        connected = pv.wait_for_connection(timeout=3.0)
        pv.disconnect()
        return connected
    except ImportError:
        # pyepics not installed
        return False
    except Exception:
        return False


# Skip all tests if IOC not available (unless explicitly enabled)
IOC_AVAILABLE = KREIOS_IOC_AVAILABLE or check_kreios_ioc_running()


@pytest.fixture(scope="module")
def epics_env():
    """Ensure EPICS environment is set up."""
    import epics

    return epics


@pytest.mark.skipif(not IOC_AVAILABLE, reason="KREIOS IOC not running")
class TestKreiosPVConnectivity:
    """Test basic PV connectivity to KREIOS IOC."""

    def test_manufacturer_pv(self, epics_env):
        """Test Manufacturer PV is accessible."""
        value = epics_env.caget(f"{KREIOS_PREFIX}Manufacturer_RBV", timeout=5.0)
        assert value is not None
        assert "SPECS" in value or "KREIOS" in value

    def test_model_pv(self, epics_env):
        """Test Model PV is accessible."""
        value = epics_env.caget(f"{KREIOS_PREFIX}Model_RBV", timeout=5.0)
        assert value is not None

    def test_connection_status(self, epics_env):
        """Test Connected_RBV PV shows connection status."""
        value = epics_env.caget(f"{KREIOS_PREFIX}Connected_RBV", timeout=5.0)
        assert value is not None
        # Should be connected to simulator
        assert value == 1, "IOC should be connected to Prodigy simulator"

    def test_energy_parameters(self, epics_env):
        """Test energy parameter PVs are accessible."""
        pvs = ["StartEnergy", "EndEnergy", "StepWidth", "PassEnergy"]
        for pv_suffix in pvs:
            value = epics_env.caget(f"{KREIOS_PREFIX}{pv_suffix}", timeout=5.0)
            assert value is not None, f"{pv_suffix} PV returned None"

    def test_dimension_parameters(self, epics_env):
        """Test dimension parameter PVs for 1D/2D/3D support."""
        pvs = ["ValuesPerSample", "NumSlices", "Samples_RBV"]
        for pv_suffix in pvs:
            value = epics_env.caget(f"{KREIOS_PREFIX}{pv_suffix}", timeout=5.0)
            assert value is not None, f"{pv_suffix} PV returned None"


@pytest.mark.skipif(not IOC_AVAILABLE, reason="KREIOS IOC not running")
class TestKreiosAcquisition:
    """Test acquisition workflows via EPICS PVs."""

    def test_set_energy_parameters(self, epics_env):
        """Test setting energy parameters."""
        # Set parameters
        epics_env.caput(f"{KREIOS_PREFIX}StartEnergy", 400.0, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}EndEnergy", 410.0, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}StepWidth", 0.5, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}PassEnergy", 20.0, wait=True)

        # Verify readbacks
        start = epics_env.caget(f"{KREIOS_PREFIX}StartEnergy_RBV")
        end = epics_env.caget(f"{KREIOS_PREFIX}EndEnergy_RBV")
        assert abs(start - 400.0) < 0.01
        assert abs(end - 410.0) < 0.01

    def test_1d_spectrum_acquisition(self, epics_env):
        """Test 1D spectrum acquisition (XPS/UPS mode)."""
        # Configure for 1D acquisition
        epics_env.caput(f"{KREIOS_PREFIX}StartEnergy", 400.0, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}EndEnergy", 402.0, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}StepWidth", 0.5, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}AcquireTime", 0.01, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}ValuesPerSample", 1, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}NumSlices", 1, wait=True)

        # Define spectrum (sends parameters to Prodigy)
        epics_env.caput(f"{KREIOS_PREFIX}DefineSpectrum", 1, wait=True)
        time.sleep(0.3)

        # Validate spectrum (required step per Prodigy protocol)
        epics_env.caput(f"{KREIOS_PREFIX}ValidateSpectrum", 1, wait=True)
        time.sleep(0.3)

        # Check validation
        valid = epics_env.caget(f"{KREIOS_PREFIX}SpectrumValid_RBV")
        assert valid == 1, "Spectrum should be valid after validate"

        # Start acquisition
        epics_env.caput(f"{KREIOS_PREFIX}Acquire", 1, wait=True)

        # Wait for completion (with timeout)
        for _ in range(50):
            acquiring = epics_env.caget(f"{KREIOS_PREFIX}Acquire_RBV")
            if acquiring == 0:
                break
            time.sleep(0.1)

        # Check we got data
        samples = epics_env.caget(f"{KREIOS_PREFIX}Samples_RBV")
        assert samples > 0, "Should have acquired samples"

        # Get spectrum data (waveform PV without _RBV suffix)
        spectrum = epics_env.caget(f"{KREIOS_PREFIX}Spectrum", count=int(samples))
        assert spectrum is not None
        assert len(spectrum) >= samples

    def test_2d_image_acquisition(self, epics_env):
        """Test 2D image acquisition (angle-resolved mode)."""
        # Configure for 2D acquisition
        epics_env.caput(f"{KREIOS_PREFIX}StartEnergy", 400.0, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}EndEnergy", 401.0, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}StepWidth", 0.5, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}AcquireTime", 0.01, wait=True)
        epics_env.caput(f"{KREIOS_PREFIX}ValuesPerSample", 64, wait=True)  # 64 detector pixels
        epics_env.caput(f"{KREIOS_PREFIX}NumSlices", 1, wait=True)

        # Define spectrum (sends parameters to Prodigy)
        epics_env.caput(f"{KREIOS_PREFIX}DefineSpectrum", 1, wait=True)
        time.sleep(0.3)

        # Validate spectrum (required step per Prodigy protocol)
        epics_env.caput(f"{KREIOS_PREFIX}ValidateSpectrum", 1, wait=True)
        time.sleep(0.3)

        # Start acquisition
        epics_env.caput(f"{KREIOS_PREFIX}Acquire", 1, wait=True)

        # Wait for completion
        for _ in range(100):
            acquiring = epics_env.caget(f"{KREIOS_PREFIX}Acquire_RBV")
            if acquiring == 0:
                break
            time.sleep(0.1)

        # Check 2D data dimensions
        samples = epics_env.caget(f"{KREIOS_PREFIX}Samples_RBV")
        values_per_sample = epics_env.caget(f"{KREIOS_PREFIX}ValuesPerSample_RBV")
        assert samples > 0
        assert values_per_sample == 64

        # Get image data (waveform PV without _RBV suffix)
        image_size = samples * values_per_sample
        image = epics_env.caget(f"{KREIOS_PREFIX}Image", count=int(image_size))
        assert image is not None
        assert len(image) >= image_size


@pytest.mark.skipif(not IOC_AVAILABLE, reason="KREIOS IOC not running")
class TestKreiosOphyd:
    """Test KREIOS IOC integration with ophyd."""

    @pytest.fixture
    def kreios_detector(self):
        """Create ophyd Device for KREIOS detector."""
        from ophyd import Component as Cpt, Device, EpicsSignal, EpicsSignalRO, Kind
        from ophyd.status import SubscriptionStatus

        class KreiosDetector(Device):
            """KREIOS-150 Photoelectron Spectrometer ophyd device."""

            # Connection
            connected = Cpt(EpicsSignalRO, "Connected_RBV", kind=Kind.normal)

            # Acquisition control
            acquire = Cpt(EpicsSignal, "Acquire", kind=Kind.omitted)
            acquire_rbv = Cpt(EpicsSignalRO, "Acquire_RBV", kind=Kind.normal)

            # Energy parameters
            start_energy = Cpt(EpicsSignal, "StartEnergy", kind=Kind.config)
            end_energy = Cpt(EpicsSignal, "EndEnergy", kind=Kind.config)
            step_width = Cpt(EpicsSignal, "StepWidth", kind=Kind.config)
            pass_energy = Cpt(EpicsSignal, "PassEnergy", kind=Kind.config)
            acquire_time = Cpt(EpicsSignal, "AcquireTime", kind=Kind.config)

            # Dimension parameters
            values_per_sample = Cpt(EpicsSignal, "ValuesPerSample", kind=Kind.config)
            num_slices = Cpt(EpicsSignal, "NumSlices", kind=Kind.config)
            samples_rbv = Cpt(EpicsSignalRO, "Samples_RBV", kind=Kind.normal)

            # Spectrum definition
            define_spectrum = Cpt(EpicsSignal, "DefineSpectrum", kind=Kind.omitted)
            spectrum_valid = Cpt(EpicsSignalRO, "SpectrumValid_RBV", kind=Kind.normal)

            # Progress
            progress = Cpt(EpicsSignalRO, "Progress_RBV", kind=Kind.normal)
            current_sample = Cpt(EpicsSignalRO, "CurrentSample_RBV", kind=Kind.normal)

            # Data arrays (waveforms without _RBV suffix)
            spectrum = Cpt(EpicsSignalRO, "Spectrum", kind=Kind.hinted)
            image = Cpt(EpicsSignalRO, "Image", kind=Kind.normal)

            def trigger(self):
                """Trigger acquisition and wait for completion."""

                def check_done(value, old_value, **kwargs):
                    return value == 0  # Acquire_RBV goes to 0 when done

                status = SubscriptionStatus(self.acquire_rbv, check_done, timeout=60)
                self.acquire.put(1)
                return status

            def configure_1d(self, start, end, step, pass_energy=20, acquire_time=0.1):
                """Configure for 1D spectrum acquisition."""
                self.start_energy.put(start)
                self.end_energy.put(end)
                self.step_width.put(step)
                self.pass_energy.put(pass_energy)
                self.acquire_time.put(acquire_time)
                self.values_per_sample.put(1)
                self.num_slices.put(1)
                time.sleep(0.2)
                self.define_spectrum.put(1)
                time.sleep(0.3)

        det = KreiosDetector(KREIOS_PREFIX, name="kreios")
        det.wait_for_connection(timeout=10)
        return det

    def test_ophyd_connection(self, kreios_detector):
        """Test ophyd device connects to IOC."""
        assert kreios_detector.connected.get() == 1

    def test_ophyd_read_configuration(self, kreios_detector):
        """Test reading configuration from device."""
        config = kreios_detector.read_configuration()
        assert "kreios_start_energy" in config
        assert "kreios_pass_energy" in config

    def test_ophyd_trigger(self, kreios_detector):
        """Test triggering acquisition via ophyd."""
        # Configure for fast acquisition
        kreios_detector.configure_1d(400, 401, 0.5, pass_energy=20, acquire_time=0.01)

        # Trigger and wait
        status = kreios_detector.trigger()
        status.wait(timeout=30)

        # Read data
        reading = kreios_detector.read()
        assert "kreios_spectrum" in reading


@pytest.mark.skipif(not IOC_AVAILABLE, reason="KREIOS IOC not running")
class TestKreiosBluesky:
    """Test KREIOS IOC integration with Bluesky RunEngine."""

    @pytest.fixture
    def run_engine(self):
        """Create Bluesky RunEngine."""
        from bluesky import RunEngine
        from bluesky.callbacks.best_effort import BestEffortCallback

        RE = RunEngine({})
        bec = BestEffortCallback()
        RE.subscribe(bec)
        return RE

    @pytest.fixture
    def kreios_for_bluesky(self):
        """Create ophyd Device configured for Bluesky."""
        from ophyd import Component as Cpt, Device, EpicsSignal, EpicsSignalRO, Kind
        from ophyd.status import SubscriptionStatus

        class KreiosForBluesky(Device):
            """KREIOS detector for Bluesky integration."""

            connected = Cpt(EpicsSignalRO, "Connected_RBV", kind=Kind.normal)
            acquire = Cpt(EpicsSignal, "Acquire", kind=Kind.omitted)
            acquire_rbv = Cpt(EpicsSignalRO, "Acquire_RBV", kind=Kind.normal)
            start_energy = Cpt(EpicsSignal, "StartEnergy", kind=Kind.config)
            end_energy = Cpt(EpicsSignal, "EndEnergy", kind=Kind.config)
            step_width = Cpt(EpicsSignal, "StepWidth", kind=Kind.config)
            pass_energy = Cpt(EpicsSignal, "PassEnergy", kind=Kind.config)
            acquire_time = Cpt(EpicsSignal, "AcquireTime", kind=Kind.config)
            values_per_sample = Cpt(EpicsSignal, "ValuesPerSample", kind=Kind.config)
            num_slices = Cpt(EpicsSignal, "NumSlices", kind=Kind.config)
            define_spectrum = Cpt(EpicsSignal, "DefineSpectrum", kind=Kind.omitted)
            spectrum_valid = Cpt(EpicsSignalRO, "SpectrumValid_RBV", kind=Kind.normal)
            spectrum = Cpt(EpicsSignalRO, "Spectrum", kind=Kind.hinted)
            samples_rbv = Cpt(EpicsSignalRO, "Samples_RBV", kind=Kind.normal)

            def trigger(self):
                def check_done(value, old_value, **kwargs):
                    return value == 0

                status = SubscriptionStatus(self.acquire_rbv, check_done, timeout=60)
                self.acquire.put(1)
                return status

        det = KreiosForBluesky(KREIOS_PREFIX, name="kreios")
        det.wait_for_connection(timeout=10)

        # Pre-configure for fast test
        det.start_energy.put(400)
        det.end_energy.put(401)
        det.step_width.put(0.5)
        det.pass_energy.put(20)
        det.acquire_time.put(0.01)
        det.values_per_sample.put(1)
        det.num_slices.put(1)
        time.sleep(0.2)
        det.define_spectrum.put(1)
        time.sleep(0.3)

        return det

    def test_bluesky_count(self, run_engine, kreios_for_bluesky):
        """Test Bluesky count plan with KREIOS detector."""
        from bluesky.plans import count

        uids = run_engine(count([kreios_for_bluesky], num=1))
        assert len(uids) == 1

    def test_bluesky_multiple_counts(self, run_engine, kreios_for_bluesky):
        """Test multiple acquisitions via Bluesky."""
        from bluesky.plans import count

        uids = run_engine(count([kreios_for_bluesky], num=2))
        assert len(uids) == 1  # One run with 2 events


# =============================================================================
# Test Utilities
# =============================================================================


def verify_kreios_ioc() -> dict:
    """Check KREIOS IOC status and return diagnostic info."""
    import epics

    result = {
        "ioc_available": False,
        "connected_to_simulator": False,
        "pvs_accessible": [],
        "pvs_failed": [],
    }

    test_pvs = [
        f"{KREIOS_PREFIX}Manufacturer_RBV",
        f"{KREIOS_PREFIX}Model_RBV",
        f"{KREIOS_PREFIX}Connected_RBV",
        f"{KREIOS_PREFIX}StartEnergy",
    ]

    for pv_name in test_pvs:
        try:
            pv = epics.PV(pv_name, connection_timeout=2.0)
            if pv.wait_for_connection(timeout=2.0):
                result["pvs_accessible"].append(pv_name)
                result["ioc_available"] = True
            else:
                result["pvs_failed"].append(pv_name)
            pv.disconnect()
        except Exception as e:
            result["pvs_failed"].append(f"{pv_name}: {e}")

    # Check simulator connection
    try:
        connected = epics.caget(f"{KREIOS_PREFIX}Connected_RBV", timeout=2.0)
        result["connected_to_simulator"] = connected == 1
    except Exception:
        pass

    return result


if __name__ == "__main__":
    print("KREIOS IOC Bluesky Integration Test Diagnostics")
    print("=" * 50)
    print(f"KREIOS_PREFIX: {KREIOS_PREFIX}")
    print(f"EPICS_CA_ADDR_LIST: {os.environ.get('EPICS_CA_ADDR_LIST', 'not set')}")
    print()

    try:
        status = verify_kreios_ioc()
        print(f"IOC Available: {status['ioc_available']}")
        print(f"Connected to Simulator: {status['connected_to_simulator']}")
        print(f"PVs Accessible: {len(status['pvs_accessible'])}")
        for pv in status["pvs_accessible"]:
            print(f"  - {pv}")
        if status["pvs_failed"]:
            print(f"PVs Failed: {len(status['pvs_failed'])}")
            for pv in status["pvs_failed"]:
                print(f"  - {pv}")
    except ImportError:
        print("ERROR: pyepics not installed. Run: pip install pyepics")
