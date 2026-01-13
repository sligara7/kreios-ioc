#!/usr/bin/env python3
"""
Caproto IOC for KREIOS-150 Area Detector.

This IOC provides EPICS PVs for controlling and reading data from the KREIOS-150
photoelectron spectrometer via the SpecsLab Prodigy Remote In protocol.

Based on the specsAnalyser areaDetector driver but extended for:
- 1D spectra (standard XPS/UPS)
- 2D images (angle-resolved / imaging detector)
- 3D volumes (depth profiling / multi-slice)

PV Structure (following NSLS-II areaDetector conventions):
- {Prefix}Acquire          - Start/stop acquisition
- {Prefix}LOW_ENERGY       - Start energy (eV)
- {Prefix}HIGH_ENERGY      - End energy (eV)
- {Prefix}STEP_SIZE        - Energy step width (eV)
- {Prefix}PASS_ENERGY      - Analyzer pass energy (eV)
- {Prefix}DWELL_TIME       - Dwell time per point (s)
- {Prefix}ACQ_MODE         - Acquisition mode (FAT, SFAT, FRR, FE)
- {Prefix}INT_SPECTRUM     - 1D integrated spectrum waveform
- {Prefix}IMAGE            - 2D image waveform
- {Prefix}VOLUME           - 3D volume waveform
- {Prefix}ValuesPerSample  - Detector pixels (for 2D/3D)
- {Prefix}NumSlices        - Number of slices (for 3D)

Communication:
- Connects to SpecsLab Prodigy simulator or real hardware via TCP:7010
- Uses Prodigy Remote In protocol v1.2

Usage:
    python kreios_areadetector_ioc.py --list-pvs
    python kreios_areadetector_ioc.py --prefix SIM:KREIOS:

Author: Claude Code / NSLS-II
Date: January 2026
"""

import asyncio
import math
import socket
import time
from datetime import datetime
from enum import IntEnum
from textwrap import dedent

from caproto.server import PVGroup, SubGroup, ioc_arg_parser, pvproperty, run


class AcquisitionMode(IntEnum):
    """Acquisition mode enumeration matching specsAnalyser."""
    FAT = 0      # Fixed Analyzer Transmission
    SFAT = 1     # Snapshot FAT
    FRR = 2      # Fixed Retard Ratio
    FE = 3       # Fixed Energies


class AcquisitionState(IntEnum):
    """Acquisition state enumeration."""
    IDLE = 0
    VALIDATED = 1
    ACQUIRING = 2
    PAUSED = 3
    FINISHED = 4
    ABORTED = 5
    ERROR = 6


class LensMode(IntEnum):
    """Lens mode enumeration."""
    HIGH_MAGNIFICATION = 0
    MEDIUM_MAGNIFICATION = 1
    LOW_MAGNIFICATION = 2
    WIDE_ANGLE = 3


class ScanRange(IntEnum):
    """Scan range enumeration."""
    SMALL_AREA = 0
    MEDIUM_AREA = 1
    LARGE_AREA = 2


# Maximum array sizes
MAX_SPECTRUM_SIZE = 100000      # 1D spectrum max points
MAX_IMAGE_SIZE = 2000000        # 2D image max points (e.g., 1000 x 2000)
MAX_VOLUME_SIZE = 50000000      # 3D volume max points (e.g., 100 x 500 x 1000)


class ProdigyClient:
    """
    Async TCP client for SpecsLab Prodigy Remote In protocol.

    Handles connection, command sending, and response parsing.
    """

    def __init__(self, host: str = "localhost", port: int = 7010):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.connected = False
        self.message_counter = 0
        self.server_name = ""
        self.protocol_version = ""

    async def connect(self) -> bool:
        """Connect to Prodigy server."""
        try:
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=5.0
            )

            # Send Connect command
            response = await self.send_command("Connect")
            if response and "OK" in response:
                self.connected = True
                # Parse server info
                if "ServerName:" in response:
                    start = response.find('ServerName:"') + 12
                    end = response.find('"', start)
                    self.server_name = response[start:end]
                if "ProtocolVersion:" in response:
                    parts = response.split("ProtocolVersion:")
                    if len(parts) > 1:
                        self.protocol_version = parts[1].split()[0]
                return True
            return False

        except Exception as e:
            print(f"[ProdigyClient] Connection error: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from Prodigy server."""
        if self.connected:
            try:
                await self.send_command("Disconnect")
            except Exception:
                pass

        if self.writer:
            self.writer.close()
            try:
                await self.writer.wait_closed()
            except Exception:
                pass

        self.connected = False
        self.reader = None
        self.writer = None

    async def send_command(self, command: str, params: dict = None) -> str:
        """Send command and return response."""
        if not self.writer:
            return None

        # Build command string
        self.message_counter = (self.message_counter + 1) % 10000
        req_id = f"{self.message_counter:04X}"

        cmd_str = f"?{req_id} {command}"
        if params:
            for key, value in params.items():
                if isinstance(value, str) and ' ' in value:
                    cmd_str += f' {key}:"{value}"'
                elif isinstance(value, list):
                    cmd_str += f' {key}:[{",".join(str(v) for v in value)}]'
                else:
                    cmd_str += f' {key}:{value}'

        cmd_str += "\n"

        try:
            self.writer.write(cmd_str.encode('utf-8'))
            await self.writer.drain()

            # Read response
            response = await asyncio.wait_for(
                self.reader.readline(),
                timeout=10.0
            )
            return response.decode('utf-8').strip()

        except Exception as e:
            print(f"[ProdigyClient] Command error: {e}")
            return None

    def parse_data_response(self, response: str) -> list:
        """Parse data array from response."""
        if not response or "Data:" not in response:
            return []

        try:
            start = response.find("Data:[") + 6
            end = response.find("]", start)
            data_str = response[start:end]
            return [float(x) for x in data_str.split(",") if x.strip()]
        except Exception:
            return []


class KreiosDetector(PVGroup):
    """
    KREIOS-150 Area Detector IOC.

    Provides EPICS PVs for spectroscopy data acquisition with support for:
    - 1D integrated spectra
    - 2D imaging detector data
    - 3D volumetric (depth profiling) data
    """

    # ==================== Connection PVs ====================

    connect_cmd = pvproperty(
        value=0, dtype=int, name="CONNECT",
        doc="Force connection to Prodigy server"
    )

    connected_rbv = pvproperty(
        value=0, dtype=int, name="CONNECTED_RBV", read_only=True,
        doc="Connection status (0=Disconnected, 1=Connected)"
    )

    server_name_rbv = pvproperty(
        value="", dtype=str, name="SERVER_NAME_RBV", read_only=True,
        max_length=256, doc="Connected server name"
    )

    protocol_version_rbv = pvproperty(
        value="", dtype=str, name="PROTOCOL_VERSION_RBV", read_only=True,
        max_length=32, doc="Protocol version"
    )

    prodigy_host = pvproperty(
        value="localhost", dtype=str, name="PRODIGY_HOST",
        max_length=256, doc="Prodigy server hostname"
    )

    prodigy_port = pvproperty(
        value=7010, dtype=int, name="PRODIGY_PORT",
        doc="Prodigy server port"
    )

    # ==================== Acquisition Control ====================

    acquire = pvproperty(
        value=0, dtype=int, name="Acquire",
        doc="Start/stop acquisition (0=Done, 1=Acquire)"
    )

    acquire_rbv = pvproperty(
        value=0, dtype=int, name="Acquire_RBV", read_only=True,
        doc="Acquisition status readback"
    )

    detector_state = pvproperty(
        value=0, dtype=int, name="DetectorState_RBV", read_only=True,
        doc="Detector state (0=Idle, 1=Validated, 2=Acquiring, 3=Paused, 4=Finished, 5=Aborted, 6=Error)"
    )

    status_message = pvproperty(
        value="Idle", dtype=str, name="StatusMessage_RBV", read_only=True,
        max_length=256, doc="Status message"
    )

    pause = pvproperty(
        value=0, dtype=int, name="PAUSE",
        doc="Pause acquisition (0=Run, 1=Pause)"
    )

    pause_rbv = pvproperty(
        value=0, dtype=int, name="PAUSE_RBV", read_only=True,
        doc="Pause status readback"
    )

    abort = pvproperty(
        value=0, dtype=int, name="ABORT",
        doc="Abort acquisition"
    )

    define_spectrum = pvproperty(
        value=0, dtype=int, name="DEFINE_SPECTRUM",
        doc="Define spectrum with current parameters"
    )

    validate_spectrum = pvproperty(
        value=0, dtype=int, name="VALIDATE_SPECTRUM",
        doc="Validate defined spectrum"
    )

    # ==================== Acquisition Mode ====================

    acq_mode = pvproperty(
        value=0, dtype=int, name="ACQ_MODE",
        doc="Acquisition mode (0=FAT, 1=SFAT, 2=FRR, 3=FE)"
    )

    acq_mode_rbv = pvproperty(
        value=0, dtype=int, name="ACQ_MODE_RBV", read_only=True,
        doc="Acquisition mode readback"
    )

    lens_mode = pvproperty(
        value=0, dtype=int, name="LENS_MODE",
        doc="Lens mode (0=HighMag, 1=MedMag, 2=LowMag, 3=WideAngle)"
    )

    lens_mode_rbv = pvproperty(
        value=0, dtype=int, name="LENS_MODE_RBV", read_only=True,
        doc="Lens mode readback"
    )

    scan_range = pvproperty(
        value=1, dtype=int, name="SCAN_RANGE",
        doc="Scan range (0=Small, 1=Medium, 2=Large)"
    )

    scan_range_rbv = pvproperty(
        value=1, dtype=int, name="SCAN_RANGE_RBV", read_only=True,
        doc="Scan range readback"
    )

    # ==================== Energy Parameters ====================

    low_energy = pvproperty(
        value=400.0, dtype=float, name="LOW_ENERGY",
        doc="Start energy (eV)"
    )

    low_energy_rbv = pvproperty(
        value=400.0, dtype=float, name="LOW_ENERGY_RBV", read_only=True,
        doc="Start energy readback"
    )

    high_energy = pvproperty(
        value=410.0, dtype=float, name="HIGH_ENERGY",
        doc="End energy (eV)"
    )

    high_energy_rbv = pvproperty(
        value=410.0, dtype=float, name="HIGH_ENERGY_RBV", read_only=True,
        doc="End energy readback"
    )

    step_size = pvproperty(
        value=0.5, dtype=float, name="STEP_SIZE",
        doc="Energy step width (eV)"
    )

    step_size_rbv = pvproperty(
        value=0.5, dtype=float, name="STEP_SIZE_RBV", read_only=True,
        doc="Step size readback"
    )

    pass_energy = pvproperty(
        value=20.0, dtype=float, name="PASS_ENERGY",
        doc="Analyzer pass energy (eV)"
    )

    pass_energy_rbv = pvproperty(
        value=20.0, dtype=float, name="PASS_ENERGY_RBV", read_only=True,
        doc="Pass energy readback"
    )

    kinetic_energy = pvproperty(
        value=300.0, dtype=float, name="KINETIC_ENERGY",
        doc="Kinetic energy for FE mode (eV)"
    )

    kinetic_energy_rbv = pvproperty(
        value=300.0, dtype=float, name="KINETIC_ENERGY_RBV", read_only=True,
        doc="Kinetic energy readback"
    )

    retarding_ratio = pvproperty(
        value=10.0, dtype=float, name="RETARDING_RATIO",
        doc="Retarding ratio for FRR mode"
    )

    retarding_ratio_rbv = pvproperty(
        value=10.0, dtype=float, name="RETARDING_RATIO_RBV", read_only=True,
        doc="Retarding ratio readback"
    )

    dwell_time = pvproperty(
        value=0.1, dtype=float, name="DWELL_TIME",
        doc="Dwell time per point (seconds)"
    )

    dwell_time_rbv = pvproperty(
        value=0.1, dtype=float, name="DWELL_TIME_RBV", read_only=True,
        doc="Dwell time readback"
    )

    # ==================== Data Dimensions ====================

    num_samples = pvproperty(
        value=21, dtype=int, name="NumSamples",
        doc="Number of energy samples"
    )

    num_samples_rbv = pvproperty(
        value=21, dtype=int, name="NumSamples_RBV", read_only=True,
        doc="Number of samples readback"
    )

    values_per_sample = pvproperty(
        value=1, dtype=int, name="ValuesPerSample",
        doc="Detector pixels per energy (1=1D, N=2D)"
    )

    values_per_sample_rbv = pvproperty(
        value=1, dtype=int, name="ValuesPerSample_RBV", read_only=True,
        doc="Values per sample readback"
    )

    num_slices = pvproperty(
        value=1, dtype=int, name="NumSlices",
        doc="Number of slices (1=1D/2D, N=3D)"
    )

    num_slices_rbv = pvproperty(
        value=1, dtype=int, name="NumSlices_RBV", read_only=True,
        doc="Number of slices readback"
    )

    num_scans = pvproperty(
        value=1, dtype=int, name="NumScans",
        doc="Number of scan iterations"
    )

    num_scans_rbv = pvproperty(
        value=1, dtype=int, name="NumScans_RBV", read_only=True,
        doc="Number of scans readback"
    )

    # ==================== Progress ====================

    current_point = pvproperty(
        value=0, dtype=int, name="CURRENT_POINT_RBV", read_only=True,
        doc="Current sample in iteration"
    )

    total_points = pvproperty(
        value=0, dtype=int, name="TOTAL_POINTS_RBV", read_only=True,
        doc="Total points in spectrum"
    )

    progress = pvproperty(
        value=0.0, dtype=float, name="PROGRESS_RBV", read_only=True,
        doc="Acquisition progress (%)"
    )

    time_remaining = pvproperty(
        value=0.0, dtype=float, name="TIME_REMAINING_RBV", read_only=True,
        doc="Estimated time remaining (s)"
    )

    # ==================== Data Arrays ====================

    # 1D Integrated Spectrum
    int_spectrum = pvproperty(
        value=[0.0] * 1000, dtype=float, name="INT_SPECTRUM", read_only=True,
        max_length=MAX_SPECTRUM_SIZE, doc="Integrated 1D spectrum"
    )

    int_spectrum_size = pvproperty(
        value=0, dtype=int, name="INT_SPECTRUM_SIZE_RBV", read_only=True,
        doc="Current 1D spectrum size"
    )

    # 2D Image
    image = pvproperty(
        value=[0.0] * 1000, dtype=float, name="IMAGE", read_only=True,
        max_length=MAX_IMAGE_SIZE, doc="2D detector image"
    )

    image_size_x = pvproperty(
        value=0, dtype=int, name="IMAGE_SIZE_X_RBV", read_only=True,
        doc="Image X dimension (energy samples)"
    )

    image_size_y = pvproperty(
        value=0, dtype=int, name="IMAGE_SIZE_Y_RBV", read_only=True,
        doc="Image Y dimension (detector pixels)"
    )

    # 3D Volume
    volume = pvproperty(
        value=[0.0] * 1000, dtype=float, name="VOLUME", read_only=True,
        max_length=MAX_VOLUME_SIZE, doc="3D volume data"
    )

    volume_size_x = pvproperty(
        value=0, dtype=int, name="VOLUME_SIZE_X_RBV", read_only=True,
        doc="Volume X dimension (energy samples)"
    )

    volume_size_y = pvproperty(
        value=0, dtype=int, name="VOLUME_SIZE_Y_RBV", read_only=True,
        doc="Volume Y dimension (detector pixels)"
    )

    volume_size_z = pvproperty(
        value=0, dtype=int, name="VOLUME_SIZE_Z_RBV", read_only=True,
        doc="Volume Z dimension (slices)"
    )

    # Energy axis for plotting
    energy_axis = pvproperty(
        value=[0.0] * 1000, dtype=float, name="ENERGY_AXIS", read_only=True,
        max_length=MAX_SPECTRUM_SIZE, doc="Energy axis values"
    )

    # ==================== Detector Parameters ====================

    detector_voltage = pvproperty(
        value=0.0, dtype=float, name="DETECTOR_VOLTAGE",
        doc="Detector high voltage (V)"
    )

    detector_voltage_rbv = pvproperty(
        value=0.0, dtype=float, name="DETECTOR_VOLTAGE_RBV", read_only=True,
        doc="Detector voltage readback"
    )

    bias_voltage = pvproperty(
        value=0.0, dtype=float, name="BIAS_VOLTAGE",
        doc="Bias voltage electrons (V)"
    )

    bias_voltage_rbv = pvproperty(
        value=0.0, dtype=float, name="BIAS_VOLTAGE_RBV", read_only=True,
        doc="Bias voltage readback"
    )

    # ==================== Internal State ====================

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = None
        self._acquisition_task = None
        self._poll_task = None
        self._state = AcquisitionState.IDLE
        self._simulated_mode = True  # Use simulated data when not connected
        self._acquired_data = []
        self._spectrum_defined = False
        self._spectrum_validated = False

    async def __ainit__(self, async_lib):
        """Initialize async resources."""
        await super().__ainit__(async_lib)
        # Start background polling task
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def _poll_loop(self):
        """Background task to update readback PVs."""
        while True:
            try:
                # Update readback PVs from setpoints
                await self.low_energy_rbv.write(self.low_energy.value)
                await self.high_energy_rbv.write(self.high_energy.value)
                await self.step_size_rbv.write(self.step_size.value)
                await self.pass_energy_rbv.write(self.pass_energy.value)
                await self.dwell_time_rbv.write(self.dwell_time.value)
                await self.acq_mode_rbv.write(self.acq_mode.value)
                await self.lens_mode_rbv.write(self.lens_mode.value)
                await self.scan_range_rbv.write(self.scan_range.value)
                await self.values_per_sample_rbv.write(self.values_per_sample.value)
                await self.num_slices_rbv.write(self.num_slices.value)
                await self.num_scans_rbv.write(self.num_scans.value)
                await self.kinetic_energy_rbv.write(self.kinetic_energy.value)
                await self.retarding_ratio_rbv.write(self.retarding_ratio.value)
                await self.detector_voltage_rbv.write(self.detector_voltage.value)
                await self.bias_voltage_rbv.write(self.bias_voltage.value)

                # Calculate number of samples
                if self.step_size.value > 0:
                    n_samples = int((self.high_energy.value - self.low_energy.value) /
                                   self.step_size.value) + 1
                    await self.num_samples_rbv.write(n_samples)

                # Update detector state
                await self.detector_state.write(self._state)

                # Update connection status
                connected = 1 if (self._client and self._client.connected) else 0
                await self.connected_rbv.write(connected)

            except Exception as e:
                print(f"[Poll] Error: {e}")

            await asyncio.sleep(0.1)

    # ==================== PV Putters ====================

    @connect_cmd.putter
    async def connect_cmd(self, instance, value):
        """Handle connection request."""
        if value == 1:
            await self._connect_to_prodigy()
        return 0

    @acquire.putter
    async def acquire(self, instance, value):
        """Handle acquisition start/stop."""
        if value == 1 and self._state not in [AcquisitionState.ACQUIRING]:
            # Start acquisition
            asyncio.create_task(self._run_acquisition())
        elif value == 0 and self._state == AcquisitionState.ACQUIRING:
            # Stop acquisition
            await self._abort_acquisition()

        await self.acquire_rbv.write(value)
        return value

    @pause.putter
    async def pause(self, instance, value):
        """Handle pause request."""
        if value == 1 and self._state == AcquisitionState.ACQUIRING:
            self._state = AcquisitionState.PAUSED
            await self.status_message.write("Paused")
            if self._client and self._client.connected:
                await self._client.send_command("Pause")
        elif value == 0 and self._state == AcquisitionState.PAUSED:
            self._state = AcquisitionState.ACQUIRING
            await self.status_message.write("Acquiring")
            if self._client and self._client.connected:
                await self._client.send_command("Resume")

        await self.pause_rbv.write(value)
        return value

    @abort.putter
    async def abort(self, instance, value):
        """Handle abort request."""
        if value == 1:
            await self._abort_acquisition()
        return 0

    @define_spectrum.putter
    async def define_spectrum(self, instance, value):
        """Define spectrum with current parameters."""
        if value == 1:
            await self._define_spectrum()
        return 0

    @validate_spectrum.putter
    async def validate_spectrum(self, instance, value):
        """Validate defined spectrum."""
        if value == 1:
            await self._validate_spectrum()
        return 0

    # ==================== Internal Methods ====================

    async def _connect_to_prodigy(self):
        """Connect to Prodigy server."""
        if self._client:
            await self._client.disconnect()

        self._client = ProdigyClient(
            host=self.prodigy_host.value,
            port=self.prodigy_port.value
        )

        await self.status_message.write(f"Connecting to {self.prodigy_host.value}:{self.prodigy_port.value}...")

        if await self._client.connect():
            await self.connected_rbv.write(1)
            await self.server_name_rbv.write(self._client.server_name)
            await self.protocol_version_rbv.write(self._client.protocol_version)
            await self.status_message.write(f"Connected to {self._client.server_name}")
            self._simulated_mode = False
        else:
            await self.connected_rbv.write(0)
            await self.status_message.write("Connection failed - using simulated mode")
            self._simulated_mode = True

    async def _define_spectrum(self):
        """Send DefineSpectrum command to Prodigy."""
        mode = AcquisitionMode(self.acq_mode.value)

        params = {
            "StartEnergy": self.low_energy.value,
            "EndEnergy": self.high_energy.value,
            "StepWidth": self.step_size.value,
            "DwellTime": self.dwell_time.value,
            "PassEnergy": self.pass_energy.value,
            "ValuesPerSample": self.values_per_sample.value,
            "NumberOfSlices": self.num_slices.value,
        }

        # Add lens mode and scan range as strings
        lens_modes = ["HighMagnification", "MediumMagnification", "LowMagnification", "WideAngle"]
        scan_ranges = ["SmallArea", "MediumArea", "LargeArea"]
        params["LensMode"] = lens_modes[min(self.lens_mode.value, 3)]
        params["ScanRange"] = scan_ranges[min(self.scan_range.value, 2)]

        if self._client and self._client.connected:
            cmd = f"DefineSpectrum{mode.name}"
            response = await self._client.send_command(cmd, params)
            if response and "OK" in response:
                self._spectrum_defined = True
                await self.status_message.write("Spectrum defined")
            else:
                await self.status_message.write(f"Define failed: {response}")
        else:
            # Simulated mode
            self._spectrum_defined = True
            await self.status_message.write("Spectrum defined (simulated)")

    async def _validate_spectrum(self):
        """Validate the defined spectrum."""
        if self._client and self._client.connected:
            response = await self._client.send_command("ValidateSpectrum")
            if response and "OK" in response:
                self._spectrum_validated = True
                self._state = AcquisitionState.VALIDATED
                await self.status_message.write("Spectrum validated")
            else:
                await self.status_message.write(f"Validation failed: {response}")
        else:
            # Simulated mode
            self._spectrum_validated = True
            self._state = AcquisitionState.VALIDATED
            await self.status_message.write("Spectrum validated (simulated)")

    async def _run_acquisition(self):
        """Run data acquisition."""
        # Auto-define and validate if not done
        if not self._spectrum_defined:
            await self._define_spectrum()
        if not self._spectrum_validated:
            await self._validate_spectrum()

        self._state = AcquisitionState.ACQUIRING
        await self.status_message.write("Acquiring...")
        await self.detector_state.write(AcquisitionState.ACQUIRING)

        # Calculate data dimensions
        n_samples = int((self.high_energy.value - self.low_energy.value) /
                       self.step_size.value) + 1
        n_pixels = max(1, self.values_per_sample.value)
        n_slices = max(1, self.num_slices.value)
        total_points = n_samples * n_pixels * n_slices

        await self.total_points.write(total_points)
        await self.num_samples_rbv.write(n_samples)

        # Generate energy axis
        energy_axis = [self.low_energy.value + i * self.step_size.value
                      for i in range(n_samples)]
        await self.energy_axis.write(energy_axis)

        if self._client and self._client.connected:
            await self._acquire_from_prodigy(n_samples, n_pixels, n_slices)
        else:
            await self._acquire_simulated(n_samples, n_pixels, n_slices)

        # Mark acquisition complete
        if self._state == AcquisitionState.ACQUIRING:
            self._state = AcquisitionState.FINISHED
            await self.status_message.write("Acquisition complete")

        await self.acquire_rbv.write(0)
        await self.detector_state.write(self._state)
        self._spectrum_defined = False
        self._spectrum_validated = False

    async def _acquire_from_prodigy(self, n_samples, n_pixels, n_slices):
        """Acquire data from real Prodigy server."""
        # Start acquisition
        response = await self._client.send_command("Start")
        if not response or "OK" not in response:
            await self.status_message.write(f"Start failed: {response}")
            self._state = AcquisitionState.ERROR
            return

        # Poll for data
        last_index = -1
        all_data = []
        total_values = n_samples * n_pixels * n_slices

        while self._state == AcquisitionState.ACQUIRING:
            # Check status
            status = await self._client.send_command("GetAcquisitionStatus")
            if not status:
                await asyncio.sleep(0.1)
                continue

            # Parse status
            if "finished" in status.lower():
                break
            elif "aborted" in status.lower():
                self._state = AcquisitionState.ABORTED
                break
            elif "error" in status.lower():
                self._state = AcquisitionState.ERROR
                break

            # Get acquired points
            if "NumberOfAcquiredPoints:" in status:
                parts = status.split("NumberOfAcquiredPoints:")
                if len(parts) > 1:
                    acquired = int(parts[1].split()[0])
                    current_values = acquired * n_pixels

                    if current_values > last_index + 1:
                        # Fetch new data
                        data_response = await self._client.send_command(
                            "GetAcquisitionData",
                            {"FromIndex": last_index + 1, "ToIndex": current_values - 1}
                        )
                        new_data = self._client.parse_data_response(data_response)
                        all_data.extend(new_data)
                        last_index = current_values - 1

                        # Update progress
                        await self.current_point.write(acquired)
                        progress = 100.0 * len(all_data) / total_values
                        await self.progress.write(progress)

                        # Update live data arrays
                        await self._update_data_arrays(all_data, n_samples, n_pixels, n_slices)

            await asyncio.sleep(0.1)

        # Final data update
        if all_data:
            await self._update_data_arrays(all_data, n_samples, n_pixels, n_slices)

    async def _acquire_simulated(self, n_samples, n_pixels, n_slices):
        """Acquire simulated data for testing."""
        total_values = n_samples * n_pixels * n_slices
        all_data = []

        center_energy = (self.low_energy.value + self.high_energy.value) / 2
        sigma = (self.high_energy.value - self.low_energy.value) / 6

        for slice_idx in range(n_slices):
            for sample_idx in range(n_samples):
                # Check for pause/abort
                while self._state == AcquisitionState.PAUSED:
                    await asyncio.sleep(0.1)

                if self._state == AcquisitionState.ABORTED:
                    return

                energy = self.low_energy.value + sample_idx * self.step_size.value

                for pixel_idx in range(n_pixels):
                    # Gaussian peak with spatial variation
                    spatial_offset = (pixel_idx - n_pixels / 2) * 0.2 if n_pixels > 1 else 0
                    slice_offset = (slice_idx - n_slices / 2) * 0.1 if n_slices > 1 else 0

                    effective_energy = energy + spatial_offset + slice_offset
                    intensity = 1000 * math.exp(-((effective_energy - center_energy) ** 2) /
                                               (2 * sigma ** 2))

                    # Add noise
                    noise = intensity * 0.1 * (hash(str(time.time() + pixel_idx)) % 100 - 50) / 50
                    intensity = max(0, intensity + noise)
                    all_data.append(intensity)

                # Update progress
                current_point = slice_idx * n_samples + sample_idx + 1
                await self.current_point.write(current_point)
                progress = 100.0 * len(all_data) / total_values
                await self.progress.write(progress)

                # Simulate dwell time (accelerated)
                await asyncio.sleep(self.dwell_time.value / 20)

                # Periodic data update
                if sample_idx % 5 == 0:
                    await self._update_data_arrays(all_data, n_samples, n_pixels, n_slices)

        # Final update
        await self._update_data_arrays(all_data, n_samples, n_pixels, n_slices)
        await self.progress.write(100.0)

    async def _update_data_arrays(self, data, n_samples, n_pixels, n_slices):
        """Update 1D, 2D, and 3D data arrays from flat data."""
        if not data:
            return

        # 1D: Integrated spectrum (sum over pixels and slices)
        spectrum = [0.0] * n_samples
        for i, val in enumerate(data):
            sample_idx = (i // n_pixels) % n_samples
            if sample_idx < n_samples:
                spectrum[sample_idx] += val

        await self.int_spectrum.write(spectrum)
        await self.int_spectrum_size.write(len(spectrum))

        # 2D: Image (n_samples x n_pixels), sum over slices
        if n_pixels > 1:
            image_size = n_samples * n_pixels
            image = [0.0] * min(image_size, len(data))

            for slice_idx in range(n_slices):
                slice_offset = slice_idx * n_samples * n_pixels
                for i in range(min(n_samples * n_pixels, len(data) - slice_offset)):
                    if slice_offset + i < len(data):
                        image[i % image_size] += data[slice_offset + i]

            await self.image.write(image)
            await self.image_size_x.write(n_samples)
            await self.image_size_y.write(n_pixels)

        # 3D: Volume (n_slices x n_samples x n_pixels)
        if n_slices > 1 and n_pixels > 1:
            await self.volume.write(data[:MAX_VOLUME_SIZE])
            await self.volume_size_x.write(n_samples)
            await self.volume_size_y.write(n_pixels)
            await self.volume_size_z.write(n_slices)

    async def _abort_acquisition(self):
        """Abort running acquisition."""
        self._state = AcquisitionState.ABORTED
        await self.status_message.write("Aborted")

        if self._client and self._client.connected:
            await self._client.send_command("Abort")

        await self.acquire_rbv.write(0)


class KreiosIOC(PVGroup):
    """
    Main KREIOS-150 IOC with detector and standard areaDetector PVs.
    """

    detector = SubGroup(KreiosDetector, prefix="")


def main():
    """Run the KREIOS-150 IOC."""
    ioc_options, run_options = ioc_arg_parser(
        default_prefix="SIM:KREIOS:",
        desc=dedent(KreiosIOC.__doc__)
    )

    ioc = KreiosIOC(**ioc_options)
    run(ioc.pvdb, **run_options)


if __name__ == "__main__":
    main()
