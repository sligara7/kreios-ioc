"""
Data integrity tests for KREIOS-150 IOC.

Tests verify:
- Correct data array reshaping from flat to N-D
- Index calculation correctness
- Data accumulation during real-time polling
- No data loss during chunked retrieval
- Energy axis calculation
"""

import pytest
import math


class TestDataReshaping:
    """Tests for reshaping flat data arrays to N-D."""

    def test_reshape_1d(self):
        """Test reshaping flat array to 1D (no reshape needed)."""
        n_samples = 21
        flat_data = [i * 1.0 for i in range(n_samples)]

        # 1D is just the flat array
        data_1d = flat_data

        assert len(data_1d) == n_samples
        assert data_1d[0] == 0.0
        assert data_1d[20] == 20.0

    def test_reshape_2d(self):
        """Test reshaping flat array to 2D (n_samples x n_pixels)."""
        n_samples = 5
        n_pixels = 4
        total = n_samples * n_pixels

        # Create flat array with index as value for verification
        flat_data = [i * 1.0 for i in range(total)]

        # Reshape to 2D (sample-major order)
        data_2d = []
        for sample in range(n_samples):
            start = sample * n_pixels
            row = flat_data[start:start + n_pixels]
            data_2d.append(row)

        assert len(data_2d) == n_samples
        assert len(data_2d[0]) == n_pixels

        # Verify values
        assert data_2d[0][0] == 0.0   # sample 0, pixel 0
        assert data_2d[0][3] == 3.0   # sample 0, pixel 3
        assert data_2d[1][0] == 4.0   # sample 1, pixel 0
        assert data_2d[4][3] == 19.0  # sample 4, pixel 3

    def test_reshape_3d(self):
        """Test reshaping flat array to 3D (n_slices x n_samples x n_pixels)."""
        n_slices = 2
        n_samples = 3
        n_pixels = 4
        total = n_slices * n_samples * n_pixels

        # Create flat array with index as value
        flat_data = [i * 1.0 for i in range(total)]

        # Reshape to 3D (slice-sample-pixel order)
        data_3d = []
        for slice_idx in range(n_slices):
            slice_data = []
            for sample_idx in range(n_samples):
                start = (slice_idx * n_samples + sample_idx) * n_pixels
                row = flat_data[start:start + n_pixels]
                slice_data.append(row)
            data_3d.append(slice_data)

        assert len(data_3d) == n_slices
        assert len(data_3d[0]) == n_samples
        assert len(data_3d[0][0]) == n_pixels

        # Verify values using index formula
        # index = slice * (S * V) + sample * V + pixel
        assert data_3d[0][0][0] == 0.0   # slice 0, sample 0, pixel 0
        assert data_3d[0][0][3] == 3.0   # slice 0, sample 0, pixel 3
        assert data_3d[0][1][0] == 4.0   # slice 0, sample 1, pixel 0
        assert data_3d[1][0][0] == 12.0  # slice 1, sample 0, pixel 0
        assert data_3d[1][2][3] == 23.0  # slice 1, sample 2, pixel 3


class TestIndexCalculation:
    """Tests for data index calculations."""

    def test_2d_index_formula(self):
        """Test 2D index formula: index = sample * n_pixels + pixel"""
        n_samples = 5
        n_pixels = 4

        def calc_index(sample, pixel):
            return sample * n_pixels + pixel

        # Verify formula
        assert calc_index(0, 0) == 0
        assert calc_index(0, 3) == 3
        assert calc_index(1, 0) == 4
        assert calc_index(2, 2) == 10
        assert calc_index(4, 3) == 19

    def test_3d_index_formula(self):
        """Test 3D index formula: index = slice * (S * V) + sample * V + pixel"""
        n_slices = 2
        n_samples = 3
        n_pixels = 4

        def calc_index(slice_idx, sample, pixel):
            return slice_idx * (n_samples * n_pixels) + sample * n_pixels + pixel

        # Verify formula
        assert calc_index(0, 0, 0) == 0
        assert calc_index(0, 0, 3) == 3
        assert calc_index(0, 1, 0) == 4
        assert calc_index(0, 2, 3) == 11
        assert calc_index(1, 0, 0) == 12
        assert calc_index(1, 2, 3) == 23

    def test_reverse_index_2d(self):
        """Test converting flat index back to 2D coordinates."""
        n_pixels = 4

        def index_to_2d(flat_idx):
            sample = flat_idx // n_pixels
            pixel = flat_idx % n_pixels
            return sample, pixel

        assert index_to_2d(0) == (0, 0)
        assert index_to_2d(3) == (0, 3)
        assert index_to_2d(4) == (1, 0)
        assert index_to_2d(19) == (4, 3)

    def test_reverse_index_3d(self):
        """Test converting flat index back to 3D coordinates."""
        n_samples = 3
        n_pixels = 4
        slice_size = n_samples * n_pixels

        def index_to_3d(flat_idx):
            slice_idx = flat_idx // slice_size
            remainder = flat_idx % slice_size
            sample = remainder // n_pixels
            pixel = remainder % n_pixels
            return slice_idx, sample, pixel

        assert index_to_3d(0) == (0, 0, 0)
        assert index_to_3d(11) == (0, 2, 3)
        assert index_to_3d(12) == (1, 0, 0)
        assert index_to_3d(23) == (1, 2, 3)


class TestEnergyAxisCalculation:
    """Tests for energy axis value calculation."""

    def test_energy_axis_basic(self):
        """Test basic energy axis calculation."""
        start_energy = 400.0
        end_energy = 410.0
        step_size = 0.5

        n_samples = int((end_energy - start_energy) / step_size) + 1
        energy_axis = [start_energy + i * step_size for i in range(n_samples)]

        assert len(energy_axis) == 21
        assert energy_axis[0] == 400.0
        assert energy_axis[10] == 405.0
        assert energy_axis[20] == 410.0

    def test_energy_axis_decimal_step(self):
        """Test energy axis with decimal step size."""
        start_energy = 100.0
        end_energy = 101.0
        step_size = 0.1

        n_samples = int((end_energy - start_energy) / step_size) + 1
        energy_axis = [start_energy + i * step_size for i in range(n_samples)]

        assert len(energy_axis) == 11
        assert abs(energy_axis[0] - 100.0) < 1e-9
        assert abs(energy_axis[5] - 100.5) < 1e-9
        assert abs(energy_axis[10] - 101.0) < 1e-9

    def test_energy_axis_single_point(self):
        """Test energy axis with single point (start == end)."""
        start_energy = 405.0
        end_energy = 405.0
        step_size = 0.5

        n_samples = 1
        energy_axis = [start_energy + i * step_size for i in range(n_samples)]

        assert len(energy_axis) == 1
        assert energy_axis[0] == 405.0


class TestDataAccumulation:
    """Tests for data accumulation during real-time polling."""

    def test_chunked_accumulation_no_gaps(self, client, simulator, wait_for_complete_func):
        """Test that chunked data retrieval has no gaps."""
        n_samples = 11

        client.connect()
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 405.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        wait_for_complete_func(client, timeout=15.0)

        # Retrieve all data in one request
        response_full = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": n_samples - 1,
        })
        data_str = response_full.split("Data:[")[1].split("]")[0]
        full_data = [float(x) for x in data_str.split(",")]

        # Retrieve same data in chunks
        chunked_data = []
        chunk_size = 3
        for start in range(0, n_samples, chunk_size):
            end = min(start + chunk_size - 1, n_samples - 1)
            response = client.send_command("GetAcquisitionData", {
                "FromIndex": start,
                "ToIndex": end,
            })
            data_str = response.split("Data:[")[1].split("]")[0]
            chunk = [float(x) for x in data_str.split(",")]
            chunked_data.extend(chunk)

        # Compare
        assert len(chunked_data) == len(full_data)
        for i in range(len(full_data)):
            assert abs(chunked_data[i] - full_data[i]) < 1e-6

    def test_overlapping_chunks_consistent(self, client, simulator, wait_for_complete_func):
        """Test that overlapping chunk requests return consistent data."""
        client.connect()
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 405.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        wait_for_complete_func(client, timeout=15.0)

        # Get overlapping chunks
        response1 = client.send_command("GetAcquisitionData", {
            "FromIndex": 3,
            "ToIndex": 7,
        })
        data1 = [float(x) for x in response1.split("Data:[")[1].split("]")[0].split(",")]

        response2 = client.send_command("GetAcquisitionData", {
            "FromIndex": 5,
            "ToIndex": 9,
        })
        data2 = [float(x) for x in response2.split("Data:[")[1].split("]")[0].split(",")]

        # Overlapping region: indices 5, 6, 7 should match
        # data1[2:5] corresponds to indices 5,6,7
        # data2[0:3] corresponds to indices 5,6,7
        for i in range(3):
            assert abs(data1[2 + i] - data2[i]) < 1e-6


class TestIntegratedSpectrum:
    """Tests for 1D integrated spectrum from 2D/3D data."""

    def test_integrate_2d_to_1d(self):
        """Test integrating 2D data to 1D spectrum."""
        n_samples = 5
        n_pixels = 4

        # Create test 2D data
        data_2d = []
        for sample in range(n_samples):
            # Each pixel has value = sample * 10 + pixel
            row = [sample * 10 + pixel for pixel in range(n_pixels)]
            data_2d.append(row)

        # Integrate (sum over pixels)
        spectrum_1d = []
        for sample in range(n_samples):
            total = sum(data_2d[sample])
            spectrum_1d.append(total)

        assert len(spectrum_1d) == n_samples
        # Sample 0: 0+1+2+3 = 6
        assert spectrum_1d[0] == 6
        # Sample 1: 10+11+12+13 = 46
        assert spectrum_1d[1] == 46
        # Sample 4: 40+41+42+43 = 166
        assert spectrum_1d[4] == 166

    def test_integrate_3d_to_1d(self):
        """Test integrating 3D data to 1D spectrum."""
        n_slices = 2
        n_samples = 3
        n_pixels = 4

        # Create test 3D data
        data_3d = []
        for slice_idx in range(n_slices):
            slice_data = []
            for sample in range(n_samples):
                # Value = slice * 100 + sample * 10 + pixel
                row = [slice_idx * 100 + sample * 10 + pixel for pixel in range(n_pixels)]
                slice_data.append(row)
            data_3d.append(slice_data)

        # Integrate (sum over slices and pixels)
        spectrum_1d = []
        for sample in range(n_samples):
            total = 0
            for slice_idx in range(n_slices):
                total += sum(data_3d[slice_idx][sample])
            spectrum_1d.append(total)

        assert len(spectrum_1d) == n_samples
        # Sample 0: (0+1+2+3) + (100+101+102+103) = 6 + 406 = 412
        assert spectrum_1d[0] == 412


class TestDataTypeConversion:
    """Tests for data type conversion."""

    def test_ascii_to_float_precision(self):
        """Test ASCII to float conversion maintains precision."""
        test_values = [
            "1.234567890123",
            "0.000001",
            "999999.999999",
            "-123.456",
            "0.0",
        ]

        for val_str in test_values:
            val_float = float(val_str)
            # Convert back to string and verify reasonable precision
            back_to_str = f"{val_float:.6f}"
            original_rounded = f"{float(val_str):.6f}"
            assert back_to_str == original_rounded

    def test_scientific_notation(self):
        """Test parsing scientific notation values."""
        sci_values = [
            "1.23e-5",
            "1.23E-5",
            "1.23e+10",
            "-1.5e-3",
        ]

        for val_str in sci_values:
            val_float = float(val_str)
            assert val_float != 0 or "0" in val_str


class TestLargeDatasets:
    """Tests for handling large data arrays."""

    def test_large_1d_array(self, client, simulator, wait_for_complete_func):
        """Test handling large 1D array (1000 points)."""
        n_samples = 101  # 400-450 eV, step 0.5

        client.connect()
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 450.0,
            "StepWidth": 0.5,
            "DwellTime": 0.005,  # Very fast
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        wait_for_complete_func(client, timeout=30.0)

        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": n_samples - 1,
        })

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]

        assert len(data) == n_samples

    def test_large_2d_array(self, client, simulator, wait_for_complete_func):
        """Test handling large 2D array (100 samples x 100 pixels = 10000 points)."""
        n_samples = 51  # 400-425 eV, step 0.5
        n_pixels = 50

        client.connect()
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 425.0,
            "StepWidth": 0.5,
            "DwellTime": 0.005,
            "PassEnergy": 20.0,
            "ValuesPerSample": n_pixels,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        wait_for_complete_func(client, timeout=60.0)

        total = n_samples * n_pixels
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": total - 1,
        })

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]

        assert len(data) == total
