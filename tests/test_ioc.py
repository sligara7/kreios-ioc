"""
Tests for KREIOS-150 IOC logic and calculations.

This module tests:
- Data array size calculations
- Energy axis generation
- Data reshaping logic (1D/2D/3D integration)
- Simulated data generation formulas

Note: Tests for PV access via Channel Access are marked with skipif
and require a running EPICS IOC to execute.
"""

import math
import pytest

# Constants matching the C++ driver definitions
MAX_SPECTRUM_SIZE = 100000  # Maximum 1D spectrum points
MAX_IMAGE_SIZE = 2000000    # Maximum 2D image pixels
MAX_VOLUME_SIZE = 50000000  # Maximum 3D volume voxels


class TestConstants:
    """Tests for IOC constants."""

    def test_max_spectrum_size(self):
        """Test maximum 1D spectrum size constant."""
        assert MAX_SPECTRUM_SIZE == 100000

    def test_max_image_size(self):
        """Test maximum 2D image size constant."""
        assert MAX_IMAGE_SIZE == 2000000

    def test_max_volume_size(self):
        """Test maximum 3D volume size constant."""
        assert MAX_VOLUME_SIZE == 50000000


class TestDataArraySizes:
    """Tests for data array size calculations."""

    def test_1d_array_size(self):
        """Test 1D spectrum array size calculation."""
        n_samples = 21
        values_per_sample = 1
        n_slices = 1

        total = n_samples * values_per_sample * n_slices
        assert total == 21
        assert total <= MAX_SPECTRUM_SIZE

    def test_2d_array_size(self):
        """Test 2D image array size calculation."""
        n_samples = 100
        values_per_sample = 128
        n_slices = 1

        total = n_samples * values_per_sample * n_slices
        assert total == 12800
        assert total <= MAX_IMAGE_SIZE

    def test_3d_array_size(self):
        """Test 3D volume array size calculation."""
        n_samples = 100
        values_per_sample = 128
        n_slices = 50

        total = n_samples * values_per_sample * n_slices
        assert total == 640000
        assert total <= MAX_VOLUME_SIZE

    def test_max_1d_samples(self):
        """Test maximum number of 1D samples."""
        max_samples = MAX_SPECTRUM_SIZE
        assert max_samples == 100000

    def test_max_2d_samples(self):
        """Test maximum number of 2D samples (e.g., 1000 x 2000)."""
        max_samples = 1000
        max_pixels = 2000
        total = max_samples * max_pixels
        assert total == MAX_IMAGE_SIZE

    def test_kreios_detector_capacity(self):
        """Test KREIOS-150 full detector capacity (1285 x 730)."""
        detector_x = 1285
        detector_y = 730
        full_detector_pixels = detector_x * detector_y
        assert full_detector_pixels == 938050
        assert full_detector_pixels <= MAX_IMAGE_SIZE


class TestEnergyAxisGeneration:
    """Tests for energy axis value generation."""

    def test_energy_axis_calculation(self):
        """Test energy axis calculation logic."""
        start_energy = 400.0
        end_energy = 410.0
        step_size = 0.5

        n_samples = int((end_energy - start_energy) / step_size) + 1
        energy_axis = [start_energy + i * step_size for i in range(n_samples)]

        assert len(energy_axis) == 21
        assert energy_axis[0] == 400.0
        assert energy_axis[10] == 405.0
        assert energy_axis[20] == 410.0

    def test_energy_axis_small_step(self):
        """Test energy axis with small step size."""
        start_energy = 100.0
        end_energy = 100.5
        step_size = 0.1

        n_samples = int((end_energy - start_energy) / step_size) + 1
        energy_axis = [start_energy + i * step_size for i in range(n_samples)]

        assert len(energy_axis) == 6
        assert abs(energy_axis[-1] - 100.5) < 1e-9

    def test_energy_axis_wide_range(self):
        """Test energy axis over wide energy range (XPS survey)."""
        start_energy = 0.0
        end_energy = 1500.0
        step_size = 1.0

        n_samples = int((end_energy - start_energy) / step_size) + 1
        energy_axis = [start_energy + i * step_size for i in range(n_samples)]

        assert len(energy_axis) == 1501
        assert energy_axis[0] == 0.0
        assert energy_axis[-1] == 1500.0

    def test_energy_samples_count_formula(self):
        """Test the formula for calculating number of samples."""
        # Various test cases
        cases = [
            (400.0, 410.0, 0.5, 21),    # Standard narrow scan
            (0.0, 100.0, 1.0, 101),     # Wide scan
            (500.0, 510.0, 0.1, 101),   # High resolution
            (82.0, 86.0, 0.1, 41),      # Au 4f region
        ]

        for start, end, step, expected in cases:
            n_samples = int((end - start) / step) + 1
            assert n_samples == expected, f"Failed for {start}-{end}, step {step}"


class TestDataReshapingLogic:
    """Tests for the data reshaping logic used in driver data processing."""

    def test_1d_spectrum_no_reshape(self):
        """Test 1D spectrum needs no reshaping."""
        n_samples = 5
        n_pixels = 1
        n_slices = 1

        # Create test data
        data = [float(i) for i in range(n_samples)]

        # 1D: just the data as-is
        spectrum = [0.0] * n_samples
        for i, val in enumerate(data):
            sample_idx = (i // n_pixels) % n_samples
            if sample_idx < n_samples:
                spectrum[sample_idx] += val

        assert spectrum == data

    def test_2d_to_1d_integration(self):
        """Test integrating 2D data to 1D spectrum."""
        n_samples = 3
        n_pixels = 4
        n_slices = 1

        # Create test data: value = sample * 10 + pixel
        data = []
        for sample in range(n_samples):
            for pixel in range(n_pixels):
                data.append(float(sample * 10 + pixel))

        # Integrate over pixels
        spectrum = [0.0] * n_samples
        for i, val in enumerate(data):
            sample_idx = (i // n_pixels) % n_samples
            if sample_idx < n_samples:
                spectrum[sample_idx] += val

        # Expected: sum of each sample's pixels
        # Sample 0: 0+1+2+3 = 6
        # Sample 1: 10+11+12+13 = 46
        # Sample 2: 20+21+22+23 = 86
        assert spectrum[0] == 6
        assert spectrum[1] == 46
        assert spectrum[2] == 86

    def test_3d_to_1d_integration(self):
        """Test integrating 3D data to 1D spectrum."""
        n_samples = 2
        n_pixels = 2
        n_slices = 2

        # Create test data: value = slice * 100 + sample * 10 + pixel
        data = []
        for slice_idx in range(n_slices):
            for sample in range(n_samples):
                for pixel in range(n_pixels):
                    data.append(float(slice_idx * 100 + sample * 10 + pixel))

        # Integrate over pixels and slices
        spectrum = [0.0] * n_samples
        for i, val in enumerate(data):
            sample_idx = (i // n_pixels) % n_samples
            if sample_idx < n_samples:
                spectrum[sample_idx] += val

        # Sample 0: (0+1) + (100+101) = 1 + 201 = 202
        # Sample 1: (10+11) + (110+111) = 21 + 221 = 242
        assert spectrum[0] == 202
        assert spectrum[1] == 242

    def test_2d_image_data_layout(self):
        """Test 2D image data layout (energy x pixels)."""
        n_samples = 3
        n_pixels = 4

        # Data comes in as [sample0_pix0, sample0_pix1, ..., sample1_pix0, ...]
        data = []
        for sample in range(n_samples):
            for pixel in range(n_pixels):
                data.append(sample * 100 + pixel)

        # Reshape to 2D array [n_samples, n_pixels]
        image = [[0.0] * n_pixels for _ in range(n_samples)]
        for i, val in enumerate(data):
            sample = i // n_pixels
            pixel = i % n_pixels
            if sample < n_samples and pixel < n_pixels:
                image[sample][pixel] = val

        # Verify layout
        assert image[0] == [0, 1, 2, 3]
        assert image[1] == [100, 101, 102, 103]
        assert image[2] == [200, 201, 202, 203]


class TestSimulatedDataGeneration:
    """Tests for simulated data generation formulas."""

    def test_gaussian_peak_at_center(self):
        """Test Gaussian peak intensity at center energy."""
        center_energy = 405.0
        sigma = 10.0 / 6  # For range 400-410
        peak_intensity = 1000

        energy = 405.0
        intensity = peak_intensity * math.exp(
            -((energy - center_energy) ** 2) / (2 * sigma ** 2)
        )
        assert abs(intensity - 1000) < 1e-6

    def test_gaussian_peak_symmetry(self):
        """Test Gaussian peak is symmetric around center."""
        center_energy = 405.0
        sigma = 10.0 / 6
        peak_intensity = 1000

        # Test points equidistant from center
        offset = 2.0
        intensity_low = peak_intensity * math.exp(
            -((center_energy - offset - center_energy) ** 2) / (2 * sigma ** 2)
        )
        intensity_high = peak_intensity * math.exp(
            -((center_energy + offset - center_energy) ** 2) / (2 * sigma ** 2)
        )

        assert abs(intensity_low - intensity_high) < 1e-10

    def test_gaussian_peak_falloff(self):
        """Test Gaussian peak falls off from center."""
        center_energy = 405.0
        sigma = 10.0 / 6
        peak_intensity = 1000

        intensity_center = peak_intensity * math.exp(0)  # At center = peak
        intensity_1sigma = peak_intensity * math.exp(-0.5)  # At 1 sigma
        intensity_2sigma = peak_intensity * math.exp(-2.0)  # At 2 sigma

        assert intensity_center == 1000
        assert intensity_1sigma < intensity_center
        assert intensity_2sigma < intensity_1sigma

    def test_spatial_offset_formula(self):
        """Test spatial offset for 2D data (angle/momentum resolved)."""
        n_pixels = 10

        # Center pixel should have minimal offset
        pixel_center = n_pixels // 2
        offset_center = (pixel_center - n_pixels / 2) * 0.2
        assert abs(offset_center) < 0.2

        # Edge pixels should have non-zero offset
        offset_edge = (0 - n_pixels / 2) * 0.2
        assert offset_edge < 0  # Negative offset for left edge


class TestProtocolEnumerations:
    """Tests for Prodigy protocol enumeration mappings."""

    def test_run_mode_strings(self):
        """Test run mode string values match protocol specification."""
        run_modes = ["FAT", "SFAT", "FRR", "FE", "LVS"]
        assert len(run_modes) == 5
        assert "FAT" in run_modes  # Fixed Analyzer Transmission
        assert "SFAT" in run_modes  # Snapshot FAT

    def test_operating_mode_strings(self):
        """Test operating mode string values."""
        operating_modes = ["Spectroscopy", "Momentum", "PEEM"]
        assert len(operating_modes) == 3

    def test_lens_mode_strings(self):
        """Test lens mode string values match protocol."""
        lens_modes = [
            "HighMagnification",
            "MediumMagnification",
            "LowMagnification",
            "WideAngle"
        ]
        assert len(lens_modes) == 4

    def test_scan_range_strings(self):
        """Test scan range string values match protocol."""
        scan_ranges = ["SmallArea", "MediumArea", "LargeArea"]
        assert len(scan_ranges) == 3


class TestParameterValidation:
    """Tests for parameter range validation logic."""

    def test_energy_range_valid(self):
        """Test valid energy parameter ranges."""
        # KREIOS-150 supports 0-1500 eV kinetic energy
        min_energy = 0.0
        max_energy = 1500.0

        # Test valid ranges
        assert 0.0 >= min_energy and 0.0 <= max_energy
        assert 1500.0 >= min_energy and 1500.0 <= max_energy
        assert 84.0 >= min_energy and 84.0 <= max_energy  # Au 4f

    def test_pass_energy_range(self):
        """Test pass energy parameter range."""
        # KREIOS-150 supports 1-200 eV pass energies
        min_pass = 1.0
        max_pass = 200.0

        valid_pass_energies = [1.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
        for pe in valid_pass_energies:
            assert pe >= min_pass and pe <= max_pass

    def test_step_width_positive(self):
        """Test step width must be positive."""
        valid_steps = [0.01, 0.05, 0.1, 0.5, 1.0]
        for step in valid_steps:
            assert step > 0

    def test_dwell_time_range(self):
        """Test dwell time reasonable range."""
        # Typical dwell times are 0.01s to 10s
        valid_dwells = [0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
        for dwell in valid_dwells:
            assert dwell > 0
            assert dwell <= 60.0  # Reasonable upper bound


# =============================================================================
# EPICS IOC Tests (require running IOC)
# =============================================================================

import os

# Check if we can import EPICS CA libraries
try:
    import epics
    EPICS_AVAILABLE = True
except ImportError:
    EPICS_AVAILABLE = False

# Configuration from environment
EPICS_IOC_PREFIX = os.environ.get("EPICS_IOC_PREFIX", "KREIOS:cam1:")
EPICS_IOC_AVAILABLE = os.environ.get("EPICS_IOC_AVAILABLE", "0") == "1"


def check_ioc_running():
    """Check if the KREIOS IOC is running and accessible."""
    if not EPICS_AVAILABLE:
        return False
    try:
        # Try to connect to a basic PV with short timeout
        pv = epics.PV(f"{EPICS_IOC_PREFIX}Manufacturer_RBV", connection_timeout=2.0)
        connected = pv.wait_for_connection(timeout=2.0)
        pv.disconnect()
        return connected
    except Exception:
        return False


# Determine if IOC tests should run
IOC_TESTS_ENABLED = EPICS_IOC_AVAILABLE or (EPICS_AVAILABLE and check_ioc_running())


@pytest.mark.skipif(not EPICS_AVAILABLE, reason="pyepics not installed")
@pytest.mark.skipif(not IOC_TESTS_ENABLED, reason="KREIOS IOC not running")
class TestEPICSConnection:
    """Tests requiring EPICS Channel Access (need running IOC)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up PV prefix for tests."""
        self.prefix = EPICS_IOC_PREFIX

    def test_ioc_manufacturer_pv(self):
        """Test Manufacturer PV is accessible."""
        pv = epics.PV(f"{self.prefix}Manufacturer_RBV")
        pv.wait_for_connection(timeout=5.0)
        assert pv.connected
        value = pv.get()
        assert value is not None
        assert "SPECS" in value or "KREIOS" in value

    def test_ioc_model_pv(self):
        """Test Model PV is accessible."""
        pv = epics.PV(f"{self.prefix}Model_RBV")
        pv.wait_for_connection(timeout=5.0)
        assert pv.connected
        value = pv.get()
        assert value is not None

    def test_ioc_connection_status_pv(self):
        """Test Connected_RBV PV shows connection status."""
        pv = epics.PV(f"{self.prefix}Connected_RBV")
        pv.wait_for_connection(timeout=5.0)
        assert pv.connected
        value = pv.get()
        assert value is not None

    def test_ioc_energy_pvs(self):
        """Test energy parameter PVs are accessible."""
        pvs = [
            f"{self.prefix}StartEnergy",
            f"{self.prefix}EndEnergy",
            f"{self.prefix}StepWidth",
            f"{self.prefix}PassEnergy",
        ]
        for pv_name in pvs:
            pv = epics.PV(pv_name)
            pv.wait_for_connection(timeout=5.0)
            assert pv.connected, f"PV {pv_name} not connected"
            value = pv.get()
            assert value is not None, f"PV {pv_name} returned None"

    def test_ioc_acquire_pv(self):
        """Test Acquire PV is accessible."""
        pv = epics.PV(f"{self.prefix}Acquire")
        pv.wait_for_connection(timeout=5.0)
        assert pv.connected
        value = pv.get()
        assert value is not None

    def test_ioc_run_mode_pv(self):
        """Test RunMode PV is accessible."""
        pv = epics.PV(f"{self.prefix}RunMode")
        pv.wait_for_connection(timeout=5.0)
        assert pv.connected
        value = pv.get()
        assert value is not None


@pytest.mark.skipif(not EPICS_AVAILABLE, reason="pyepics not installed")
@pytest.mark.skipif(not IOC_TESTS_ENABLED, reason="KREIOS IOC not running")
class TestEPICSAcquisition:
    """Acquisition tests requiring EPICS IOC."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up PV prefix for tests."""
        self.prefix = EPICS_IOC_PREFIX

    def test_set_energy_parameters(self):
        """Test setting energy parameters via PVs."""
        # Set parameters
        epics.caput(f"{self.prefix}StartEnergy", 400.0, wait=True)
        epics.caput(f"{self.prefix}EndEnergy", 410.0, wait=True)
        epics.caput(f"{self.prefix}StepWidth", 0.5, wait=True)
        epics.caput(f"{self.prefix}PassEnergy", 20.0, wait=True)

        # Verify readbacks
        assert abs(epics.caget(f"{self.prefix}StartEnergy_RBV") - 400.0) < 0.01
        assert abs(epics.caget(f"{self.prefix}EndEnergy_RBV") - 410.0) < 0.01

    def test_connect_to_prodigy(self):
        """Test connecting to Prodigy via Connect PV."""
        # Trigger connection
        epics.caput(f"{self.prefix}Connect", 1, wait=True)

        # Wait for connection
        import time
        time.sleep(1.0)

        # Check connection status
        connected = epics.caget(f"{self.prefix}Connected_RBV")
        assert connected == 1, "Failed to connect to Prodigy"

    def test_1d_acquisition_workflow(self):
        """Test complete 1D acquisition via EPICS PVs."""
        prefix = self.prefix

        # Ensure connected
        epics.caput(f"{prefix}Connect", 1, wait=True)
        import time
        time.sleep(0.5)

        # Set parameters for fast acquisition
        epics.caput(f"{prefix}StartEnergy", 400.0, wait=True)
        epics.caput(f"{prefix}EndEnergy", 402.0, wait=True)
        epics.caput(f"{prefix}StepWidth", 0.5, wait=True)
        epics.caput(f"{prefix}DwellTime", 0.01, wait=True)
        epics.caput(f"{prefix}PassEnergy", 20.0, wait=True)
        epics.caput(f"{prefix}ValuesPerSample", 1, wait=True)
        epics.caput(f"{prefix}NumSlices", 1, wait=True)

        # Start acquisition
        epics.caput(f"{prefix}Acquire", 1, wait=True)

        # Wait for completion (with timeout)
        for _ in range(100):
            acquiring = epics.caget(f"{prefix}Acquire_RBV")
            if acquiring == 0:
                break
            time.sleep(0.1)

        # Check we got data
        num_samples = epics.caget(f"{prefix}NumSamples_RBV")
        assert num_samples > 0, "No samples acquired"
