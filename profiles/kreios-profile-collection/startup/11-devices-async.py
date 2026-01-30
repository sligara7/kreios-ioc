"""
KREIOS-150 Ophyd-Async Device Definitions.

Asynchronous ophyd device classes for the KREIOS-150 Momentum Microscope
photoelectron spectrometer connected via the areaDetector-based EPICS IOC.

PV Prefix: KREIOS:cam1:* (configurable)

Device Classes:
- KreiosDetectorAsync: Full spectrometer control and readout
- KreiosSpectrumAsync: 1D spectrum-only device
- KreiosImageAsync: 2D image-only device

Data dimensionality support:
- 1D: Integrated spectrum (energy axis only)
- 2D: Image (energy x detector pixels)
- 3D: Volume (slices x energy x pixels)

Operating modes:
- Spectroscopy: Standard XPS/UPS measurements
- Momentum: ARPES k-space imaging
- PEEM: Photoemission electron microscopy

Run modes:
- FAT: Fixed Analyzer Transmission
- SFAT: Snapshot FAT
- FRR: Fixed Retarding Ratio
- FE: Fixed Energy
- LVS: Lens Voltage Scan
"""

from enum import IntEnum
from typing import Annotated as A

import numpy as np

from ophyd_async.core import (
    Array1D,
    AsyncStatus,
    ConfigSignal,
    HintedSignal,
    SignalR,
    SignalRW,
    StandardReadable,
    observe_value,
    wait_for_value,
)
from ophyd_async.epics.core import (
    EpicsDevice,
    PvSuffix,
)


# =============================================================================
# Enums for KREIOS modes
# =============================================================================


class RunMode(IntEnum):
    """KREIOS run modes."""

    FAT = 0  # Fixed Analyzer Transmission
    SFAT = 1  # Snapshot FAT
    FRR = 2  # Fixed Retarding Ratio
    FE = 3  # Fixed Energy
    LVS = 4  # Lens Voltage Scan


class OperatingMode(IntEnum):
    """KREIOS operating modes."""

    SPECTROSCOPY = 0
    MOMENTUM = 1
    PEEM = 2


# =============================================================================
# KREIOS Detector Device - Full Control (Async)
# =============================================================================


class KreiosDetectorAsync(StandardReadable, EpicsDevice):
    """
    KREIOS-150 Momentum Microscope - Full Control (Async).

    Asynchronous ophyd device for controlling the KREIOS-150 via the
    areaDetector IOC. Supports 1D (spectrum), 2D (imaging), and 3D
    (depth profiling) modes.

    PV naming follows areaDetector conventions with _RBV suffixes for readbacks.

    Parameters
    ----------
    prefix : str
        EPICS PV prefix (e.g., "KREIOS:cam1:")
    name : str
        Device name for bluesky

    Examples
    --------
    >>> kreios = KreiosDetectorAsync("KREIOS:cam1:", name="kreios")
    >>> await kreios.connect()
    >>> await kreios.configure_1d(280, 300, 0.1, pass_energy=20)
    >>> status = kreios.trigger()
    >>> await status
    """

    # =========================================================================
    # Connection Management
    # =========================================================================
    connect_cmd: A[SignalRW[int], PvSuffix("Connect")]
    connected: A[SignalR[int], PvSuffix("Connected_RBV"), ConfigSignal]
    server_name: A[SignalR[str], PvSuffix("ServerName_RBV"), ConfigSignal]
    msg_counter: A[SignalR[int], PvSuffix("MsgCounter_RBV")]

    # From ADBase template
    manufacturer: A[SignalR[str], PvSuffix("Manufacturer_RBV"), ConfigSignal]
    model: A[SignalR[str], PvSuffix("Model_RBV"), ConfigSignal]

    # =========================================================================
    # Acquisition Control
    # =========================================================================
    acquire: A[SignalRW[int], PvSuffix.rbv("Acquire")]
    define_spectrum: A[SignalRW[int], PvSuffix("DefineSpectrum")]
    validate_spectrum: A[SignalRW[int], PvSuffix("ValidateSpectrum")]
    spectrum_valid: A[SignalR[int], PvSuffix("SpectrumValid_RBV")]

    # Pause control
    acq_pause: A[SignalRW[int], PvSuffix.rbv("Pause")]

    # Safe state control
    safe_state: A[SignalRW[int], PvSuffix.rbv("SafeState"), ConfigSignal]

    # Data delay
    data_delay_max: A[SignalRW[float], PvSuffix.rbv("DataDelayMax"), ConfigSignal]

    # =========================================================================
    # Energy Parameters (eV)
    # =========================================================================
    start_energy: A[SignalRW[float], PvSuffix.rbv("StartEnergy"), ConfigSignal]
    end_energy: A[SignalRW[float], PvSuffix.rbv("EndEnergy"), ConfigSignal]
    energy_width: A[SignalR[float], PvSuffix("EnergyWidth_RBV"), ConfigSignal]
    step_width: A[SignalRW[float], PvSuffix.rbv("StepWidth"), ConfigSignal]
    pass_energy: A[SignalRW[float], PvSuffix.rbv("PassEnergy"), ConfigSignal]
    kinetic_energy: A[SignalRW[float], PvSuffix.rbv("KineticEnergy"), ConfigSignal]
    retarding_ratio: A[SignalRW[float], PvSuffix.rbv("RetardingRatio"), ConfigSignal]

    # =========================================================================
    # Acquisition Mode
    # =========================================================================
    run_mode: A[SignalRW[int], PvSuffix.rbv("RunMode"), ConfigSignal]
    operating_mode: A[SignalRW[int], PvSuffix.rbv("OperatingMode"), ConfigSignal]
    lens_mode: A[SignalRW[int], PvSuffix.rbv("LensMode"), ConfigSignal]
    scan_range: A[SignalRW[int], PvSuffix.rbv("ScanRange"), ConfigSignal]

    # =========================================================================
    # Dimension Parameters (for 1D/2D/3D modes)
    # =========================================================================
    samples: A[SignalRW[int], PvSuffix.rbv("Samples"), ConfigSignal]
    samples_iteration: A[SignalR[int], PvSuffix("SamplesIteration_RBV"), ConfigSignal]
    values_per_sample: A[SignalRW[int], PvSuffix.rbv("ValuesPerSample"), ConfigSignal]
    num_slices: A[SignalRW[int], PvSuffix.rbv("NumSlices"), ConfigSignal]

    # Non-energy axis parameters
    non_energy_channels: A[SignalR[int], PvSuffix("NonEnergyChannels_RBV"), ConfigSignal]
    non_energy_units: A[SignalR[str], PvSuffix("NonEnergyUnits_RBV"), ConfigSignal]
    non_energy_min: A[SignalR[float], PvSuffix("NonEnergyMin_RBV"), ConfigSignal]
    non_energy_max: A[SignalR[float], PvSuffix("NonEnergyMax_RBV"), ConfigSignal]

    # =========================================================================
    # Progress Monitoring
    # =========================================================================
    current_sample: A[SignalR[int], PvSuffix("CurrentSample_RBV")]
    current_sample_iteration: A[SignalR[int], PvSuffix("CurrentSampleIteration_RBV")]
    progress: A[SignalR[float], PvSuffix("Progress_RBV")]
    progress_iteration: A[SignalR[float], PvSuffix("ProgressIteration_RBV")]
    remaining_time: A[SignalR[float], PvSuffix("RemainingTime_RBV")]
    remaining_time_iteration: A[SignalR[float], PvSuffix("RemainingTimeIteration_RBV")]

    # =========================================================================
    # Data Arrays
    # =========================================================================
    spectrum: A[SignalR[Array1D[np.float64]], PvSuffix("Spectrum"), HintedSignal]
    image: A[SignalR[np.ndarray], PvSuffix("Image")]
    volume: A[SignalR[np.ndarray], PvSuffix("Volume")]
    energy_axis: A[SignalR[Array1D[np.float64]], PvSuffix("EnergyAxis")]

    # =========================================================================
    # Hardware Parameters
    # =========================================================================
    detector_voltage: A[SignalRW[float], PvSuffix.rbv("DetectorVoltage"), ConfigSignal]
    bias_voltage: A[SignalRW[float], PvSuffix.rbv("BiasVoltage"), ConfigSignal]

    # =========================================================================
    # Momentum Microscopy Parameters (k-space)
    # =========================================================================
    kx_min: A[SignalRW[float], PvSuffix.rbv("KxMin"), ConfigSignal]
    kx_max: A[SignalRW[float], PvSuffix.rbv("KxMax"), ConfigSignal]
    ky_min: A[SignalRW[float], PvSuffix.rbv("KyMin"), ConfigSignal]
    ky_max: A[SignalRW[float], PvSuffix.rbv("KyMax"), ConfigSignal]

    # =========================================================================
    # PEEM Parameters
    # =========================================================================
    field_of_view: A[SignalRW[float], PvSuffix.rbv("FieldOfView"), ConfigSignal]
    magnification: A[SignalRW[float], PvSuffix.rbv("Magnification"), ConfigSignal]

    # =========================================================================
    # Triggerable Interface
    # =========================================================================

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """
        Trigger spectrum acquisition and wait for completion.

        Returns an AsyncStatus that completes when acquisition finishes.
        """
        # Start acquisition
        await self.acquire.set(1)

        # Wait for acquisition to complete (acquire goes back to 0)
        async for value in observe_value(self.acquire, done_timeout=600):
            if value == 0:
                break

    # =========================================================================
    # Configuration Methods
    # =========================================================================

    async def configure_1d(
        self,
        start_e: float,
        end_e: float,
        step_e: float,
        pass_energy: float = 20.0,
    ) -> None:
        """
        Configure for 1D spectrum acquisition (standard XPS/UPS).

        Parameters
        ----------
        start_e : float
            Start energy (eV)
        end_e : float
            End energy (eV)
        step_e : float
            Energy step (eV)
        pass_energy : float
            Analyzer pass energy (eV)
        """
        await self.start_energy.set(start_e)
        await self.end_energy.set(end_e)
        await self.step_width.set(step_e)
        await self.pass_energy.set(pass_energy)
        await self.values_per_sample.set(1)
        await self.num_slices.set(1)
        await self.define_spectrum.set(1)

    async def configure_2d(
        self,
        start_e: float,
        end_e: float,
        step_e: float,
        n_pixels: int,
        pass_energy: float = 20.0,
    ) -> None:
        """
        Configure for 2D image acquisition (ARPES mode).

        Parameters
        ----------
        start_e : float
            Start energy (eV)
        end_e : float
            End energy (eV)
        step_e : float
            Energy step (eV)
        n_pixels : int
            Number of detector pixels
        pass_energy : float
            Analyzer pass energy (eV)
        """
        await self.start_energy.set(start_e)
        await self.end_energy.set(end_e)
        await self.step_width.set(step_e)
        await self.pass_energy.set(pass_energy)
        await self.values_per_sample.set(n_pixels)
        await self.num_slices.set(1)
        await self.define_spectrum.set(1)

    async def configure_3d(
        self,
        start_e: float,
        end_e: float,
        step_e: float,
        n_pixels: int,
        n_slices: int,
        pass_energy: float = 20.0,
    ) -> None:
        """
        Configure for 3D volume acquisition (depth profiling).

        Parameters
        ----------
        start_e : float
            Start energy (eV)
        end_e : float
            End energy (eV)
        step_e : float
            Energy step (eV)
        n_pixels : int
            Number of detector pixels
        n_slices : int
            Number of depth slices
        pass_energy : float
            Analyzer pass energy (eV)
        """
        await self.start_energy.set(start_e)
        await self.end_energy.set(end_e)
        await self.step_width.set(step_e)
        await self.pass_energy.set(pass_energy)
        await self.values_per_sample.set(n_pixels)
        await self.num_slices.set(n_slices)
        await self.define_spectrum.set(1)

    # =========================================================================
    # Flyer Interface (for continuous scanning)
    # =========================================================================

    @AsyncStatus.wrap
    async def kickoff(self) -> None:
        """Start a flyer-style acquisition."""
        await self.acquire.set(1)

    @AsyncStatus.wrap
    async def complete(self) -> None:
        """Wait for acquisition to complete."""
        await wait_for_value(self.acquire, 0, timeout=600)


# =============================================================================
# Simplified Devices for Specific Use Cases
# =============================================================================


class KreiosSpectrumAsync(StandardReadable, EpicsDevice):
    """
    Simplified KREIOS device for 1D spectrum acquisition only (Async).

    Use this for basic XPS/UPS measurements where you only need
    energy parameters and spectrum readout.

    Parameters
    ----------
    prefix : str
        EPICS PV prefix (e.g., "KREIOS:cam1:")
    name : str
        Device name for bluesky
    """

    # Acquisition
    acquire: A[SignalRW[int], PvSuffix.rbv("Acquire")]

    # Energy parameters
    start_energy: A[SignalRW[float], PvSuffix.rbv("StartEnergy"), ConfigSignal]
    end_energy: A[SignalRW[float], PvSuffix.rbv("EndEnergy"), ConfigSignal]
    step_width: A[SignalRW[float], PvSuffix.rbv("StepWidth"), ConfigSignal]
    pass_energy: A[SignalRW[float], PvSuffix.rbv("PassEnergy"), ConfigSignal]

    # Spectrum definition
    define_spectrum: A[SignalRW[int], PvSuffix("DefineSpectrum")]
    spectrum_valid: A[SignalR[int], PvSuffix("SpectrumValid_RBV")]

    # Data
    spectrum: A[SignalR[Array1D[np.float64]], PvSuffix("Spectrum"), HintedSignal]
    energy_axis: A[SignalR[Array1D[np.float64]], PvSuffix("EnergyAxis")]

    # Progress
    progress: A[SignalR[float], PvSuffix("Progress_RBV")]

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """Trigger spectrum acquisition and wait for completion."""
        await self.acquire.set(1)
        async for value in observe_value(self.acquire, done_timeout=300):
            if value == 0:
                break


class KreiosImageAsync(StandardReadable, EpicsDevice):
    """
    Simplified KREIOS device for 2D image acquisition (Async).

    Use this for ARPES or imaging measurements where you need
    2D data (energy x detector pixels).

    Parameters
    ----------
    prefix : str
        EPICS PV prefix (e.g., "KREIOS:cam1:")
    name : str
        Device name for bluesky
    """

    # Acquisition
    acquire: A[SignalRW[int], PvSuffix.rbv("Acquire")]

    # Energy parameters
    start_energy: A[SignalRW[float], PvSuffix.rbv("StartEnergy"), ConfigSignal]
    end_energy: A[SignalRW[float], PvSuffix.rbv("EndEnergy"), ConfigSignal]
    step_width: A[SignalRW[float], PvSuffix.rbv("StepWidth"), ConfigSignal]
    pass_energy: A[SignalRW[float], PvSuffix.rbv("PassEnergy"), ConfigSignal]

    # Dimension
    values_per_sample: A[SignalRW[int], PvSuffix.rbv("ValuesPerSample"), ConfigSignal]

    # Spectrum definition
    define_spectrum: A[SignalRW[int], PvSuffix("DefineSpectrum")]
    spectrum_valid: A[SignalR[int], PvSuffix("SpectrumValid_RBV")]

    # Data
    image: A[SignalR[np.ndarray], PvSuffix("Image"), HintedSignal]

    # Progress
    progress: A[SignalR[float], PvSuffix("Progress_RBV")]

    @AsyncStatus.wrap
    async def trigger(self) -> None:
        """Trigger image acquisition and wait for completion."""
        await self.acquire.set(1)
        async for value in observe_value(self.acquire, done_timeout=300):
            if value == 0:
                break
