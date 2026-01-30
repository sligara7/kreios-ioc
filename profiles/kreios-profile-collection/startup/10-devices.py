"""
KREIOS-150 Ophyd Device Definitions.

Defines ophyd devices for the KREIOS-150 Momentum Microscope photoelectron
spectrometer connected via the areaDetector-based EPICS IOC.

PV Prefix: KREIOS:cam1:* (configurable via KREIOS_PREFIX env var)

Device Classes:
- KreiosDetector: Full spectrometer control and readout
- KreiosSpectrum: 1D spectrum-only device
- KreiosImage: 2D image-only device

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
print(f"Loading file {__file__!r} ...")

import os
import time
import warnings

from ophyd import Component as Cpt
from ophyd import Device, EpicsSignal, EpicsSignalRO, Kind
from ophyd.status import SubscriptionStatus, DeviceStatus

# Suppress ophyd connection warnings during startup
warnings.filterwarnings("ignore", category=UserWarning, module="ophyd")

# Get PV prefix from environment
KREIOS_PREFIX = os.environ.get("KREIOS_PREFIX", "KREIOS:cam1:")


# =============================================================================
# KREIOS Detector Device - Full Control
# =============================================================================

class KreiosDetector(Device):
    """
    KREIOS-150 Momentum Microscope - Full Control.

    Full ophyd device for controlling the KREIOS-150 via the areaDetector IOC.
    Supports 1D (spectrum), 2D (imaging), and 3D (depth profiling) modes.

    PV naming follows areaDetector conventions with _RBV suffixes for readbacks.
    """

    # =========================================================================
    # Connection Management
    # =========================================================================
    connect = Cpt(EpicsSignal, "Connect", kind=Kind.omitted,
                  doc="Force connection to Prodigy server")
    connected = Cpt(EpicsSignalRO, "Connected_RBV", kind=Kind.config,
                    doc="Connection status to Prodigy server")
    server_name = Cpt(EpicsSignalRO, "ServerName_RBV", kind=Kind.config,
                      doc="Connected server name")
    msg_counter = Cpt(EpicsSignalRO, "MsgCounter_RBV", kind=Kind.omitted,
                      doc="Protocol message counter")

    # From ADBase template
    manufacturer = Cpt(EpicsSignalRO, "Manufacturer_RBV", kind=Kind.config)
    model = Cpt(EpicsSignalRO, "Model_RBV", kind=Kind.config)

    # =========================================================================
    # Acquisition Control
    # =========================================================================
    acquire = Cpt(EpicsSignal, "Acquire", kind=Kind.omitted,
                  doc="Start/stop acquisition (1=start, 0=stop)")
    acquire_rbv = Cpt(EpicsSignalRO, "Acquire_RBV", kind=Kind.normal,
                      doc="Acquisition status readback")

    # Spectrum definition
    define_spectrum = Cpt(EpicsSignal, "DefineSpectrum", kind=Kind.omitted,
                          doc="Define spectrum parameters")
    validate_spectrum = Cpt(EpicsSignal, "ValidateSpectrum", kind=Kind.omitted,
                            doc="Validate spectrum before acquisition")
    spectrum_valid = Cpt(EpicsSignalRO, "SpectrumValid_RBV", kind=Kind.normal,
                         doc="Spectrum validation status")

    # Pause control (use acq_ prefix to avoid reserved 'pause' name in bluesky)
    acq_pause = Cpt(EpicsSignal, "Pause", kind=Kind.omitted,
                    doc="Pause acquisition")
    acq_pause_rbv = Cpt(EpicsSignalRO, "Pause_RBV", kind=Kind.normal,
                        doc="Pause status readback")

    # Safe state control
    safe_state = Cpt(EpicsSignal, "SafeState", kind=Kind.config,
                     doc="Return to safe state after scan")
    safe_state_rbv = Cpt(EpicsSignalRO, "SafeState_RBV", kind=Kind.config)

    # Data delay
    data_delay_max = Cpt(EpicsSignal, "DataDelayMax", kind=Kind.config,
                         doc="Maximum data delay (seconds)")
    data_delay_max_rbv = Cpt(EpicsSignalRO, "DataDelayMax_RBV", kind=Kind.config)

    # =========================================================================
    # Energy Parameters (eV)
    # =========================================================================
    start_energy = Cpt(EpicsSignal, "StartEnergy", kind=Kind.config,
                       doc="Start energy (eV)")
    start_energy_rbv = Cpt(EpicsSignalRO, "StartEnergy_RBV", kind=Kind.config)

    end_energy = Cpt(EpicsSignal, "EndEnergy", kind=Kind.config,
                     doc="End energy (eV)")
    end_energy_rbv = Cpt(EpicsSignalRO, "EndEnergy_RBV", kind=Kind.config)

    energy_width_rbv = Cpt(EpicsSignalRO, "EnergyWidth_RBV", kind=Kind.config,
                           doc="Energy width (calculated)")

    step_width = Cpt(EpicsSignal, "StepWidth", kind=Kind.config,
                     doc="Energy step width (eV)")
    step_width_rbv = Cpt(EpicsSignalRO, "StepWidth_RBV", kind=Kind.config)

    pass_energy = Cpt(EpicsSignal, "PassEnergy", kind=Kind.config,
                      doc="Analyzer pass energy (eV)")
    pass_energy_rbv = Cpt(EpicsSignalRO, "PassEnergy_RBV", kind=Kind.config)

    kinetic_energy = Cpt(EpicsSignal, "KineticEnergy", kind=Kind.config,
                         doc="Kinetic energy for FE mode (eV)")
    kinetic_energy_rbv = Cpt(EpicsSignalRO, "KineticEnergy_RBV", kind=Kind.config)

    retarding_ratio = Cpt(EpicsSignal, "RetardingRatio", kind=Kind.config,
                          doc="Retarding ratio for FRR mode")
    retarding_ratio_rbv = Cpt(EpicsSignalRO, "RetardingRatio_RBV", kind=Kind.config)

    # =========================================================================
    # Acquisition Mode
    # =========================================================================
    run_mode = Cpt(EpicsSignal, "RunMode", kind=Kind.config,
                   doc="Run mode: 0=FAT, 1=SFAT, 2=FRR, 3=FE, 4=LVS")
    run_mode_rbv = Cpt(EpicsSignalRO, "RunMode_RBV", kind=Kind.config)

    operating_mode = Cpt(EpicsSignal, "OperatingMode", kind=Kind.config,
                         doc="Operating mode: 0=Spectroscopy, 1=Momentum, 2=PEEM")
    operating_mode_rbv = Cpt(EpicsSignalRO, "OperatingMode_RBV", kind=Kind.config)

    lens_mode = Cpt(EpicsSignal, "LensMode", kind=Kind.config,
                    doc="Lens mode (dynamically populated)")
    lens_mode_rbv = Cpt(EpicsSignalRO, "LensMode_RBV", kind=Kind.config)

    scan_range = Cpt(EpicsSignal, "ScanRange", kind=Kind.config,
                     doc="Scan range (dynamically populated)")
    scan_range_rbv = Cpt(EpicsSignalRO, "ScanRange_RBV", kind=Kind.config)

    # =========================================================================
    # Dimension Parameters (for 1D/2D/3D modes)
    # =========================================================================
    samples = Cpt(EpicsSignal, "Samples", kind=Kind.config,
                  doc="Number of energy samples")
    samples_rbv = Cpt(EpicsSignalRO, "Samples_RBV", kind=Kind.config)
    samples_iteration_rbv = Cpt(EpicsSignalRO, "SamplesIteration_RBV", kind=Kind.config,
                                doc="Samples per iteration")

    values_per_sample = Cpt(EpicsSignal, "ValuesPerSample", kind=Kind.config,
                            doc="Detector pixels per sample (1=1D, N=2D)")
    values_per_sample_rbv = Cpt(EpicsSignalRO, "ValuesPerSample_RBV", kind=Kind.config)

    num_slices = Cpt(EpicsSignal, "NumSlices", kind=Kind.config,
                     doc="Number of slices (1=1D/2D, N=3D)")
    num_slices_rbv = Cpt(EpicsSignalRO, "NumSlices_RBV", kind=Kind.config)

    # Non-energy axis parameters
    non_energy_channels_rbv = Cpt(EpicsSignalRO, "NonEnergyChannels_RBV", kind=Kind.config)
    non_energy_units_rbv = Cpt(EpicsSignalRO, "NonEnergyUnits_RBV", kind=Kind.config)
    non_energy_min_rbv = Cpt(EpicsSignalRO, "NonEnergyMin_RBV", kind=Kind.config)
    non_energy_max_rbv = Cpt(EpicsSignalRO, "NonEnergyMax_RBV", kind=Kind.config)

    # =========================================================================
    # Progress Monitoring
    # =========================================================================
    current_sample = Cpt(EpicsSignalRO, "CurrentSample_RBV", kind=Kind.normal)
    current_sample_iteration = Cpt(EpicsSignalRO, "CurrentSampleIteration_RBV", kind=Kind.normal)
    progress = Cpt(EpicsSignalRO, "Progress_RBV", kind=Kind.normal,
                   doc="Total acquisition progress (%)")
    progress_iteration = Cpt(EpicsSignalRO, "ProgressIteration_RBV", kind=Kind.normal,
                             doc="Iteration progress (%)")
    remaining_time = Cpt(EpicsSignalRO, "RemainingTime_RBV", kind=Kind.normal,
                         doc="Total remaining time (seconds)")
    remaining_time_iteration = Cpt(EpicsSignalRO, "RemainingTimeIteration_RBV", kind=Kind.normal,
                                   doc="Iteration remaining time (seconds)")

    # =========================================================================
    # Data Arrays
    # =========================================================================
    spectrum = Cpt(EpicsSignalRO, "Spectrum", kind=Kind.hinted,
                   doc="1D integrated spectrum array")
    image = Cpt(EpicsSignalRO, "Image", kind=Kind.normal,
                doc="2D image array (energy x pixels)")
    volume = Cpt(EpicsSignalRO, "Volume", kind=Kind.normal,
                 doc="3D volume array (slices x energy x pixels)")
    energy_axis = Cpt(EpicsSignalRO, "EnergyAxis", kind=Kind.normal,
                      doc="Energy axis values (eV)")

    # =========================================================================
    # Hardware Parameters
    # =========================================================================
    detector_voltage = Cpt(EpicsSignal, "DetectorVoltage", kind=Kind.config,
                           doc="Detector voltage (V)")
    detector_voltage_rbv = Cpt(EpicsSignalRO, "DetectorVoltage_RBV", kind=Kind.config)
    bias_voltage = Cpt(EpicsSignal, "BiasVoltage", kind=Kind.config,
                       doc="Bias voltage (V)")
    bias_voltage_rbv = Cpt(EpicsSignalRO, "BiasVoltage_RBV", kind=Kind.config)

    # =========================================================================
    # Momentum Microscopy Parameters (k-space)
    # =========================================================================
    kx_min = Cpt(EpicsSignal, "KxMin", kind=Kind.config, doc="Kx minimum (A^-1)")
    kx_min_rbv = Cpt(EpicsSignalRO, "KxMin_RBV", kind=Kind.config)
    kx_max = Cpt(EpicsSignal, "KxMax", kind=Kind.config, doc="Kx maximum (A^-1)")
    kx_max_rbv = Cpt(EpicsSignalRO, "KxMax_RBV", kind=Kind.config)
    ky_min = Cpt(EpicsSignal, "KyMin", kind=Kind.config, doc="Ky minimum (A^-1)")
    ky_min_rbv = Cpt(EpicsSignalRO, "KyMin_RBV", kind=Kind.config)
    ky_max = Cpt(EpicsSignal, "KyMax", kind=Kind.config, doc="Ky maximum (A^-1)")
    ky_max_rbv = Cpt(EpicsSignalRO, "KyMax_RBV", kind=Kind.config)

    # =========================================================================
    # PEEM Parameters
    # =========================================================================
    field_of_view = Cpt(EpicsSignal, "FieldOfView", kind=Kind.config,
                        doc="Field of view (um)")
    field_of_view_rbv = Cpt(EpicsSignalRO, "FieldOfView_RBV", kind=Kind.config)
    magnification = Cpt(EpicsSignal, "Magnification", kind=Kind.config,
                        doc="Magnification")
    magnification_rbv = Cpt(EpicsSignalRO, "Magnification_RBV", kind=Kind.config)

    # =========================================================================
    # Methods
    # =========================================================================

    def trigger(self):
        """
        Trigger spectrum acquisition and wait for completion.

        Returns an ophyd Status object that completes when acquisition finishes.
        """
        def check_done(value, old_value, **kwargs):
            # Acquisition done when Acquire_RBV goes back to 0
            return value == 0

        status = SubscriptionStatus(self.acquire_rbv, check_done, timeout=600)
        self.acquire.put(1)
        return status

    def configure_1d(self, start_e, end_e, step_e, pass_energy=20.0):
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
        self.start_energy.put(start_e, wait=True)
        self.end_energy.put(end_e, wait=True)
        self.step_width.put(step_e, wait=True)
        self.pass_energy.put(pass_energy, wait=True)
        self.values_per_sample.put(1, wait=True)
        self.num_slices.put(1, wait=True)
        time.sleep(0.2)
        self.define_spectrum.put(1, wait=True)
        time.sleep(0.3)

    def configure_2d(self, start_e, end_e, step_e, n_pixels, pass_energy=20.0):
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
        self.start_energy.put(start_e, wait=True)
        self.end_energy.put(end_e, wait=True)
        self.step_width.put(step_e, wait=True)
        self.pass_energy.put(pass_energy, wait=True)
        self.values_per_sample.put(n_pixels, wait=True)
        self.num_slices.put(1, wait=True)
        time.sleep(0.2)
        self.define_spectrum.put(1, wait=True)
        time.sleep(0.3)

    def configure_3d(self, start_e, end_e, step_e, n_pixels, n_slices, pass_energy=20.0):
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
        self.start_energy.put(start_e, wait=True)
        self.end_energy.put(end_e, wait=True)
        self.step_width.put(step_e, wait=True)
        self.pass_energy.put(pass_energy, wait=True)
        self.values_per_sample.put(n_pixels, wait=True)
        self.num_slices.put(n_slices, wait=True)
        time.sleep(0.2)
        self.define_spectrum.put(1, wait=True)
        time.sleep(0.3)

    # =========================================================================
    # Flyer Interface (for continuous scanning)
    # =========================================================================

    def kickoff(self):
        """Start a flyer-style acquisition."""
        status = DeviceStatus(self)
        self.acquire.put(1)
        status.set_finished()
        return status

    def complete(self):
        """Wait for acquisition to complete."""
        def check_done(value, old_value, **kwargs):
            return value == 0

        return SubscriptionStatus(self.acquire_rbv, check_done, timeout=600)

    def collect(self):
        """Collect data after acquisition (flyer interface)."""
        import time as time_module

        now = time_module.time()
        spectrum_data = self.spectrum.get()
        energy_data = self.energy_axis.get()

        yield {
            "data": {
                self.spectrum.name: spectrum_data,
                self.energy_axis.name: energy_data,
            },
            "timestamps": {
                self.spectrum.name: now,
                self.energy_axis.name: now,
            },
            "time": now,
        }

    def describe_collect(self):
        """Describe collected data (flyer interface)."""
        n_samples = int(self.samples_rbv.get()) or 1000
        return {
            "primary": {
                self.spectrum.name: {
                    "source": f"PV:{self.spectrum.pvname}",
                    "dtype": "array",
                    "shape": [n_samples],
                },
                self.energy_axis.name: {
                    "source": f"PV:{self.energy_axis.pvname}",
                    "dtype": "array",
                    "shape": [n_samples],
                },
            }
        }


# =============================================================================
# Simplified Devices for Specific Use Cases
# =============================================================================

class KreiosSpectrum(Device):
    """
    Simplified KREIOS device for 1D spectrum acquisition only.

    Use this for basic XPS/UPS measurements where you only need
    energy parameters and spectrum readout.
    """
    # Acquisition
    acquire = Cpt(EpicsSignal, "Acquire", kind=Kind.omitted)
    acquire_rbv = Cpt(EpicsSignalRO, "Acquire_RBV", kind=Kind.normal)

    # Energy parameters
    start_energy = Cpt(EpicsSignal, "StartEnergy", kind=Kind.config)
    end_energy = Cpt(EpicsSignal, "EndEnergy", kind=Kind.config)
    step_width = Cpt(EpicsSignal, "StepWidth", kind=Kind.config)
    pass_energy = Cpt(EpicsSignal, "PassEnergy", kind=Kind.config)

    # Spectrum definition
    define_spectrum = Cpt(EpicsSignal, "DefineSpectrum", kind=Kind.omitted)
    spectrum_valid = Cpt(EpicsSignalRO, "SpectrumValid_RBV", kind=Kind.normal)

    # Data
    spectrum = Cpt(EpicsSignalRO, "Spectrum", kind=Kind.hinted)
    energy_axis = Cpt(EpicsSignalRO, "EnergyAxis", kind=Kind.normal)

    # Progress
    progress = Cpt(EpicsSignalRO, "Progress_RBV", kind=Kind.normal)

    def trigger(self):
        def check_done(value, old_value, **kwargs):
            return value == 0
        status = SubscriptionStatus(self.acquire_rbv, check_done, timeout=300)
        self.acquire.put(1)
        return status


class KreiosImage(Device):
    """
    Simplified KREIOS device for 2D image acquisition.

    Use this for ARPES or imaging measurements where you need
    2D data (energy x detector pixels).
    """
    # Acquisition
    acquire = Cpt(EpicsSignal, "Acquire", kind=Kind.omitted)
    acquire_rbv = Cpt(EpicsSignalRO, "Acquire_RBV", kind=Kind.normal)

    # Energy parameters
    start_energy = Cpt(EpicsSignal, "StartEnergy", kind=Kind.config)
    end_energy = Cpt(EpicsSignal, "EndEnergy", kind=Kind.config)
    step_width = Cpt(EpicsSignal, "StepWidth", kind=Kind.config)
    pass_energy = Cpt(EpicsSignal, "PassEnergy", kind=Kind.config)

    # Dimension
    values_per_sample = Cpt(EpicsSignal, "ValuesPerSample", kind=Kind.config)

    # Spectrum definition
    define_spectrum = Cpt(EpicsSignal, "DefineSpectrum", kind=Kind.omitted)
    spectrum_valid = Cpt(EpicsSignalRO, "SpectrumValid_RBV", kind=Kind.normal)

    # Data
    image = Cpt(EpicsSignalRO, "Image", kind=Kind.hinted)

    # Progress
    progress = Cpt(EpicsSignalRO, "Progress_RBV", kind=Kind.normal)

    def trigger(self):
        def check_done(value, old_value, **kwargs):
            return value == 0
        status = SubscriptionStatus(self.acquire_rbv, check_done, timeout=300)
        self.acquire.put(1)
        return status


# =============================================================================
# Device Instantiation
# =============================================================================

print(f"  Creating KREIOS devices with prefix: {KREIOS_PREFIX}")

# Main spectrometer device
kreios = KreiosDetector(KREIOS_PREFIX, name="kreios")

# Simplified devices
kreios_spectrum = KreiosSpectrum(KREIOS_PREFIX, name="kreios_spectrum")
kreios_image = KreiosImage(KREIOS_PREFIX, name="kreios_image")


# =============================================================================
# Connection Check
# =============================================================================

def wait_for_connection(device, timeout=10.0):
    """Wait for a device to connect."""
    try:
        device.wait_for_connection(timeout=timeout)
        return True
    except Exception as e:
        print(f"  Warning: {device.name} connection issue: {e}")
        return False


print("  Connecting to KREIOS IOC...")
connected = wait_for_connection(kreios, timeout=10.0)

if connected:
    print(f"    kreios connected: {kreios.prefix}")
    try:
        mfr = kreios.manufacturer.get()
        model = kreios.model.get()
        conn = kreios.connected.get()
        print(f"    Manufacturer: {mfr}")
        print(f"    Model: {model}")
        print(f"    Connected to Prodigy: {conn}")
    except Exception as e:
        print(f"    Could not read device info: {e}")
else:
    print("    WARNING: KREIOS IOC not available")
    print("    Start the IOC with: docker compose --profile full up -d")
    print("    (in /home/asligar/git_projects/systems/kreios_ioc/docker)")

print()
