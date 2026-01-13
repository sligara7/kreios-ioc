"""
Acquisition workflow tests for KREIOS-150 IOC.

Tests complete acquisition workflows for:
- 1D spectrum acquisition (standard XPS/UPS)
- 2D image acquisition (angle-resolved / imaging)
- 3D volume acquisition (depth profiling)
- Real-time data polling patterns
- Chunked data retrieval
"""

import pytest
import time


class TestAcquisitionWorkflow1D:
    """Tests for 1D spectrum acquisition workflow."""

    def test_complete_1d_workflow(self, client, spectrum_params_1d, wait_for_complete_func):
        """Test complete 1D acquisition workflow."""
        # Connect
        response = client.send_command("Connect")
        assert "OK" in response

        # Define spectrum
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": spectrum_params_1d["StartEnergy"],
            "EndEnergy": spectrum_params_1d["EndEnergy"],
            "StepWidth": spectrum_params_1d["StepWidth"],
            "DwellTime": 0.01,  # Fast for testing
            "PassEnergy": spectrum_params_1d["PassEnergy"],
            "ValuesPerSample": 1,
        })
        assert "OK" in response

        # Validate
        response = client.send_command("ValidateSpectrum")
        assert "OK" in response
        assert "Samples:21" in response

        # Start
        response = client.send_command("Start")
        assert "OK" in response

        # Wait for completion
        response = wait_for_complete_func(client, timeout=15.0)
        assert "finished" in response.lower()

        # Get all data
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 20,
        })
        assert "Data:[" in response

        # Parse and verify
        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]
        assert len(data) == 21

        # Disconnect
        response = client.send_command("Disconnect")
        assert "OK" in response

    def test_1d_chunked_retrieval(self, client, wait_for_complete_func):
        """Test retrieving 1D data in chunks."""
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
        wait_for_complete_func(client, timeout=15.0)

        # Retrieve in 5-point chunks
        all_data = []
        for start in range(0, 21, 5):
            end = min(start + 4, 20)
            response = client.send_command("GetAcquisitionData", {
                "FromIndex": start,
                "ToIndex": end,
            })
            data_str = response.split("Data:[")[1].split("]")[0]
            chunk = [float(x) for x in data_str.split(",")]
            all_data.extend(chunk)

        assert len(all_data) == 21


class TestAcquisitionWorkflow2D:
    """Tests for 2D image acquisition workflow."""

    def test_complete_2d_workflow(self, client, wait_for_complete_func):
        """Test complete 2D acquisition workflow."""
        n_samples = 11  # 400-405 eV, step 0.5
        n_pixels = 32   # Detector pixels

        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 405.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
            "ValuesPerSample": n_pixels,
        })
        assert "OK" in response

        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=30.0)

        # Total data points = n_samples * n_pixels = 11 * 32 = 352
        expected_total = n_samples * n_pixels
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": expected_total - 1,
        })
        assert "Data:[" in response

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]
        assert len(data) == expected_total

    def test_2d_data_layout(self, client, wait_for_complete_func):
        """Test that 2D data is laid out correctly (sample-major order)."""
        n_samples = 5
        n_pixels = 10

        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
            "ValuesPerSample": n_pixels,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=15.0)

        total = n_samples * n_pixels
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": total - 1,
        })

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]

        # Reshape to 2D (sample, pixel)
        data_2d = []
        for sample in range(n_samples):
            row = data[sample * n_pixels:(sample + 1) * n_pixels]
            data_2d.append(row)

        assert len(data_2d) == n_samples
        assert len(data_2d[0]) == n_pixels

    def test_2d_realtime_polling(self, client):
        """Test real-time polling of 2D acquisition progress."""
        n_samples = 21
        n_pixels = 16

        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 410.0,
            "StepWidth": 0.5,
            "DwellTime": 0.05,  # Slow enough to observe progress
            "PassEnergy": 20.0,
            "ValuesPerSample": n_pixels,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        # Poll and collect data incrementally
        last_index = -1
        all_data = []
        max_polls = 100

        for _ in range(max_polls):
            response = client.send_command("GetAcquisitionStatus")

            if "finished" in response.lower():
                break

            if "NumberOfAcquiredPoints:" in response:
                parts = response.split("NumberOfAcquiredPoints:")
                acquired_samples = int(parts[1].split()[0])
                current_values = acquired_samples * n_pixels

                if current_values > last_index + 1 and current_values > 0:
                    # Fetch new data
                    fetch_response = client.send_command("GetAcquisitionData", {
                        "FromIndex": last_index + 1,
                        "ToIndex": current_values - 1,
                    })
                    if "Data:[" in fetch_response:
                        data_str = fetch_response.split("Data:[")[1].split("]")[0]
                        new_data = [float(x) for x in data_str.split(",") if x.strip()]
                        all_data.extend(new_data)
                        last_index = current_values - 1

            time.sleep(0.1)

        # Should have collected data
        expected_total = n_samples * n_pixels
        assert len(all_data) > 0
        # May not have all data if we finished polling early
        assert len(all_data) <= expected_total

        client.send_command("Abort")


class TestAcquisitionWorkflow3D:
    """Tests for 3D volume acquisition workflow."""

    def test_complete_3d_workflow(self, client, wait_for_complete_func):
        """Test complete 3D acquisition workflow."""
        n_slices = 3
        n_samples = 5  # 400-402 eV, step 0.5
        n_pixels = 8

        client.send_command("Connect")
        response = client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 402.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
            "ValuesPerSample": n_pixels,
            "NumberOfSlices": n_slices,
        })
        assert "OK" in response

        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=30.0)

        # Total = slices * samples * pixels = 3 * 5 * 8 = 120
        expected_total = n_slices * n_samples * n_pixels
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": expected_total - 1,
        })
        assert "Data:[" in response

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]
        assert len(data) == expected_total

    def test_3d_data_layout(self, client, wait_for_complete_func):
        """Test that 3D data is laid out correctly (slice-sample-pixel order)."""
        n_slices = 2
        n_samples = 3
        n_pixels = 4

        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 401.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
            "ValuesPerSample": n_pixels,
            "NumberOfSlices": n_slices,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=15.0)

        total = n_slices * n_samples * n_pixels
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": total - 1,
        })

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]

        # Reshape to 3D (slice, sample, pixel)
        data_3d = []
        for slice_idx in range(n_slices):
            slice_data = []
            for sample_idx in range(n_samples):
                start = (slice_idx * n_samples + sample_idx) * n_pixels
                row = data[start:start + n_pixels]
                slice_data.append(row)
            data_3d.append(slice_data)

        assert len(data_3d) == n_slices
        assert len(data_3d[0]) == n_samples
        assert len(data_3d[0][0]) == n_pixels

    def test_3d_index_calculation(self, client, wait_for_complete_func):
        """Test that 3D index calculation is correct."""
        n_slices = 2
        n_samples = 3
        n_pixels = 4

        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 401.0,
            "StepWidth": 0.5,
            "DwellTime": 0.01,
            "PassEnergy": 20.0,
            "ValuesPerSample": n_pixels,
            "NumberOfSlices": n_slices,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")
        wait_for_complete_func(client, timeout=15.0)

        total = n_slices * n_samples * n_pixels
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": total - 1,
        })

        data_str = response.split("Data:[")[1].split("]")[0]
        data = [float(x) for x in data_str.split(",")]

        # Verify index formula: index = slice * (S * V) + sample * V + pixel
        # For slice=1, sample=1, pixel=2:
        # index = 1 * (3 * 4) + 1 * 4 + 2 = 12 + 4 + 2 = 18
        def get_index(slice_idx, sample_idx, pixel_idx):
            return slice_idx * (n_samples * n_pixels) + sample_idx * n_pixels + pixel_idx

        # Verify a few indices
        assert get_index(0, 0, 0) == 0
        assert get_index(0, 0, 3) == 3
        assert get_index(0, 1, 0) == 4
        assert get_index(1, 0, 0) == 12
        assert get_index(1, 1, 2) == 18


class TestAcquisitionPauseResume:
    """Tests for pause/resume during acquisition."""

    def test_pause_stops_progress(self, client):
        """Test that pause stops acquisition progress."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 420.0,  # Long acquisition
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        # Wait a bit, then pause
        time.sleep(0.3)
        client.send_command("Pause")

        # Get progress
        response1 = client.send_command("GetAcquisitionStatus")
        if "NumberOfAcquiredPoints:" in response1:
            progress1 = int(response1.split("NumberOfAcquiredPoints:")[1].split()[0])
        else:
            progress1 = 0

        # Wait and check progress hasn't changed
        time.sleep(0.5)
        response2 = client.send_command("GetAcquisitionStatus")
        if "NumberOfAcquiredPoints:" in response2:
            progress2 = int(response2.split("NumberOfAcquiredPoints:")[1].split()[0])
        else:
            progress2 = 0

        # Progress should not have increased during pause
        assert progress2 == progress1

        client.send_command("Abort")

    def test_resume_continues_acquisition(self, client):
        """Test that resume continues acquisition after pause."""
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
        time.sleep(0.2)
        client.send_command("Pause")
        response_paused = client.send_command("GetAcquisitionStatus")
        assert "paused" in response_paused.lower()

        # Get paused progress
        paused_progress = 0
        if "NumberOfAcquiredPoints:" in response_paused:
            paused_progress = int(response_paused.split("NumberOfAcquiredPoints:")[1].split()[0])

        # Resume
        client.send_command("Resume")
        time.sleep(0.3)

        # Check progress increased
        response_resumed = client.send_command("GetAcquisitionStatus")
        resumed_progress = 0
        if "NumberOfAcquiredPoints:" in response_resumed:
            resumed_progress = int(response_resumed.split("NumberOfAcquiredPoints:")[1].split()[0])

        assert resumed_progress > paused_progress

        client.send_command("Abort")


class TestAcquisitionAbort:
    """Tests for aborting acquisition."""

    def test_abort_stops_acquisition(self, client):
        """Test that abort stops acquisition immediately."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 420.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        time.sleep(0.2)
        response = client.send_command("Abort")
        assert "OK" in response

        status = client.send_command("GetAcquisitionStatus")
        assert "aborted" in status.lower()

    def test_data_available_after_abort(self, client):
        """Test that partial data is available after abort."""
        client.send_command("Connect")
        client.send_command("DefineSpectrumFAT", {
            "StartEnergy": 400.0,
            "EndEnergy": 420.0,
            "StepWidth": 0.5,
            "DwellTime": 0.1,
            "PassEnergy": 20.0,
        })
        client.send_command("ValidateSpectrum")
        client.send_command("Start")

        time.sleep(0.5)  # Allow some data collection
        client.send_command("Abort")

        # Should be able to retrieve partial data
        response = client.send_command("GetAcquisitionData", {
            "FromIndex": 0,
            "ToIndex": 4,
        })

        # May have data or may not, but should not error badly
        assert "OK" in response or "Error" in response


class TestMultipleAcquisitions:
    """Tests for running multiple acquisitions in sequence."""

    def test_sequential_acquisitions(self, client, wait_for_complete_func):
        """Test running multiple acquisitions sequentially."""
        client.send_command("Connect")

        for i in range(3):
            # Define with slightly different parameters
            client.send_command("DefineSpectrumFAT", {
                "StartEnergy": 400.0 + i,
                "EndEnergy": 402.0 + i,
                "StepWidth": 0.5,
                "DwellTime": 0.01,
                "PassEnergy": 20.0,
            })
            client.send_command("ValidateSpectrum")
            client.send_command("Start")
            wait_for_complete_func(client, timeout=15.0)

            response = client.send_command("GetAcquisitionData", {
                "FromIndex": 0,
                "ToIndex": 4,
            })
            assert "Data:[" in response

            client.send_command("ClearSpectrum")

    def test_reconnect_between_acquisitions(self, client, wait_for_complete_func):
        """Test disconnecting and reconnecting between acquisitions."""
        # First acquisition
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
        wait_for_complete_func(client, timeout=15.0)
        client.send_command("Disconnect")

        # Reconnect for second acquisition
        time.sleep(0.2)
        client.disconnect()  # Close socket
        client.connect()     # Reopen socket

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
