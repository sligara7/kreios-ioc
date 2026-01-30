"""
KREIOS-150 Ophyd Device Classes.

Device classes for the KREIOS-150 Momentum Microscope photoelectron spectrometer.
These classes connect to the areaDetector-based EPICS IOC.

PV Prefix: KREIOS:cam1:* (configurable)

Data dimensionality:
- 1D: Integrated spectrum (energy axis only)
- 2D: Image (energy x detector pixels)
- 3D: Volume (slices x energy x pixels)

Operating modes: Spectroscopy, Momentum, PEEM
Run modes: FAT, SFAT, FRR, FE, LVS
"""

import time
from ophyd import Component as Cpt
from ophyd import Device, EpicsSignal, EpicsSignalRO, Kind
from ophyd.status import SubscriptionStatus, DeviceStatus


class KreiosDetector(Device):
    """
    KREIOS-150 Momentum Microscope - Full Control.

    Complete ophyd device for the KREIOS-150 photoelectron spectrometer.
    Supports 1D (spectrum), 2D (imaging), and 3D (depth profiling) modes.

    Parameters
    ----------
    prefix : str
        EPICS PV prefix (e.g., "KREIOS:cam1:")
    name : str
        Device name for bluesky

    Examples
    --------
    >>> kreios = KreiosDetector("KREIOS:cam1:", name="kreios")
    >>> kreios.wait_for_connection()
    >>> kreios.configure_1d(280, 300, 0.1, pass_energy=20)
    >>> status = kreios.trigger()
    """

    # ==================== Connection Management ====================
    connect = Cpt(EpicsSignal, "Connect", kind=Kind.omitted)
    connected = Cpt(EpicsSignalRO, "Connected_RBV", kind=Kind.config)
    server_name = Cpt(EpicsSignalRO, "ServerName_RBV", kind=Kind.config)
    msg_counter = Cpt(EpicsSignalRO, "MsgCounter_RBV", kind=Kind.omitted)
    manufacturer = Cpt(EpicsSignalRO, "Manufacturer_RBV", kind=Kind.config)
    model = Cpt(EpicsSignalRO, "Model_RBV", kind=Kind.config)

    # ==================== Acquisition Control ====================
    acquire = Cpt(EpicsSignal, "Acquire", kind=Kind.omitted)
    acquire_rbv = Cpt(EpicsSignalRO, "Acquire_RBV", kind=Kind.normal)
    define_spectrum = Cpt(EpicsSignal, "DefineSpectrum", kind=Kind.omitted)
    validate_spectrum = Cpt(EpicsSignal, "ValidateSpectrum", kind=Kind.omitted)
    spectrum_valid = Cpt(EpicsSignalRO, "SpectrumValid_RBV", kind=Kind.normal)

    # Pause control (use acq_ prefix to avoid reserved 'pause' name in bluesky)
    acq_pause = Cpt(EpicsSignal, "Pause", kind=Kind.omitted)
    acq_pause_rbv = Cpt(EpicsSignalRO, "Pause_RBV", kind=Kind.normal)

    # Safe state control
    safe_state = Cpt(EpicsSignal, "SafeState", kind=Kind.config)
    safe_state_rbv = Cpt(EpicsSignalRO, "SafeState_RBV", kind=Kind.config)

    # Data delay
    data_delay_max = Cpt(EpicsSignal, "DataDelayMax", kind=Kind.config)
    data_delay_max_rbv = Cpt(EpicsSignalRO, "DataDelayMax_RBV", kind=Kind.config)

    # ==================== Energy Parameters (eV) ====================
    start_energy = Cpt(EpicsSignal, "StartEnergy", kind=Kind.config)
    start_energy_rbv = Cpt(EpicsSignalRO, "StartEnergy_RBV", kind=Kind.config)
    end_energy = Cpt(EpicsSignal, "EndEnergy", kind=Kind.config)
    end_energy_rbv = Cpt(EpicsSignalRO, "EndEnergy_RBV", kind=Kind.config)
    energy_width_rbv = Cpt(EpicsSignalRO, "EnergyWidth_RBV", kind=Kind.config)
    step_width = Cpt(EpicsSignal, "StepWidth", kind=Kind.config)
    step_width_rbv = Cpt(EpicsSignalRO, "StepWidth_RBV", kind=Kind.config)
    pass_energy = Cpt(EpicsSignal, "PassEnergy", kind=Kind.config)
    pass_energy_rbv = Cpt(EpicsSignalRO, "PassEnergy_RBV", kind=Kind.config)
    kinetic_energy = Cpt(EpicsSignal, "KineticEnergy", kind=Kind.config)
    kinetic_energy_rbv = Cpt(EpicsSignalRO, "KineticEnergy_RBV", kind=Kind.config)
    retarding_ratio = Cpt(EpicsSignal, "RetardingRatio", kind=Kind.config)
    retarding_ratio_rbv = Cpt(EpicsSignalRO, "RetardingRatio_RBV", kind=Kind.config)

    # ==================== Acquisition Mode ====================
    run_mode = Cpt(EpicsSignal, "RunMode", kind=Kind.config)
    run_mode_rbv = Cpt(EpicsSignalRO, "RunMode_RBV", kind=Kind.config)
    operating_mode = Cpt(EpicsSignal, "OperatingMode", kind=Kind.config)
    operating_mode_rbv = Cpt(EpicsSignalRO, "OperatingMode_RBV", kind=Kind.config)
    lens_mode = Cpt(EpicsSignal, "LensMode", kind=Kind.config)
    lens_mode_rbv = Cpt(EpicsSignalRO, "LensMode_RBV", kind=Kind.config)
    scan_range = Cpt(EpicsSignal, "ScanRange", kind=Kind.config)
    scan_range_rbv = Cpt(EpicsSignalRO, "ScanRange_RBV", kind=Kind.config)

    # ==================== Dimension Parameters ====================
    samples = Cpt(EpicsSignal, "Samples", kind=Kind.config)
    samples_rbv = Cpt(EpicsSignalRO, "Samples_RBV", kind=Kind.config)
    samples_iteration_rbv = Cpt(EpicsSignalRO, "SamplesIteration_RBV", kind=Kind.config)
    values_per_sample = Cpt(EpicsSignal, "ValuesPerSample", kind=Kind.config)
    values_per_sample_rbv = Cpt(EpicsSignalRO, "ValuesPerSample_RBV", kind=Kind.config)
    num_slices = Cpt(EpicsSignal, "NumSlices", kind=Kind.config)
    num_slices_rbv = Cpt(EpicsSignalRO, "NumSlices_RBV", kind=Kind.config)

    # Non-energy axis
    non_energy_channels_rbv = Cpt(EpicsSignalRO, "NonEnergyChannels_RBV", kind=Kind.config)
    non_energy_units_rbv = Cpt(EpicsSignalRO, "NonEnergyUnits_RBV", kind=Kind.config)
    non_energy_min_rbv = Cpt(EpicsSignalRO, "NonEnergyMin_RBV", kind=Kind.config)
    non_energy_max_rbv = Cpt(EpicsSignalRO, "NonEnergyMax_RBV", kind=Kind.config)

    # ==================== Progress Monitoring ====================
    current_sample = Cpt(EpicsSignalRO, "CurrentSample_RBV", kind=Kind.normal)
    current_sample_iteration = Cpt(EpicsSignalRO, "CurrentSampleIteration_RBV", kind=Kind.normal)
    progress = Cpt(EpicsSignalRO, "Progress_RBV", kind=Kind.normal)
    progress_iteration = Cpt(EpicsSignalRO, "ProgressIteration_RBV", kind=Kind.normal)
    remaining_time = Cpt(EpicsSignalRO, "RemainingTime_RBV", kind=Kind.normal)
    remaining_time_iteration = Cpt(EpicsSignalRO, "RemainingTimeIteration_RBV", kind=Kind.normal)

    # ==================== Data Arrays ====================
    spectrum = Cpt(EpicsSignalRO, "Spectrum", kind=Kind.hinted)
    image = Cpt(EpicsSignalRO, "Image", kind=Kind.normal)
    volume = Cpt(EpicsSignalRO, "Volume", kind=Kind.normal)
    energy_axis = Cpt(EpicsSignalRO, "EnergyAxis", kind=Kind.normal)

    # ==================== Hardware Parameters ====================
    detector_voltage = Cpt(EpicsSignal, "DetectorVoltage", kind=Kind.config)
    detector_voltage_rbv = Cpt(EpicsSignalRO, "DetectorVoltage_RBV", kind=Kind.config)
    bias_voltage = Cpt(EpicsSignal, "BiasVoltage", kind=Kind.config)
    bias_voltage_rbv = Cpt(EpicsSignalRO, "BiasVoltage_RBV", kind=Kind.config)

    # ==================== Momentum Microscopy (k-space) ====================
    kx_min = Cpt(EpicsSignal, "KxMin", kind=Kind.config)
    kx_min_rbv = Cpt(EpicsSignalRO, "KxMin_RBV", kind=Kind.config)
    kx_max = Cpt(EpicsSignal, "KxMax", kind=Kind.config)
    kx_max_rbv = Cpt(EpicsSignalRO, "KxMax_RBV", kind=Kind.config)
    ky_min = Cpt(EpicsSignal, "KyMin", kind=Kind.config)
    ky_min_rbv = Cpt(EpicsSignalRO, "KyMin_RBV", kind=Kind.config)
    ky_max = Cpt(EpicsSignal, "KyMax", kind=Kind.config)
    ky_max_rbv = Cpt(EpicsSignalRO, "KyMax_RBV", kind=Kind.config)

    # ==================== PEEM Parameters ====================
    field_of_view = Cpt(EpicsSignal, "FieldOfView", kind=Kind.config)
    field_of_view_rbv = Cpt(EpicsSignalRO, "FieldOfView_RBV", kind=Kind.config)
    magnification = Cpt(EpicsSignal, "Magnification", kind=Kind.config)
    magnification_rbv = Cpt(EpicsSignalRO, "Magnification_RBV", kind=Kind.config)

    def trigger(self):
        """Trigger acquisition and return status."""
        def check_done(value, old_value, **kwargs):
            return value == 0
        status = SubscriptionStatus(self.acquire_rbv, check_done, timeout=600)
        self.acquire.put(1)
        return status

    def configure_1d(self, start_e, end_e, step_e, pass_energy=20.0):
        """Configure for 1D spectrum acquisition."""
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
        """Configure for 2D image acquisition."""
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
        """Configure for 3D volume acquisition."""
        self.start_energy.put(start_e, wait=True)
        self.end_energy.put(end_e, wait=True)
        self.step_width.put(step_e, wait=True)
        self.pass_energy.put(pass_energy, wait=True)
        self.values_per_sample.put(n_pixels, wait=True)
        self.num_slices.put(n_slices, wait=True)
        time.sleep(0.2)
        self.define_spectrum.put(1, wait=True)
        time.sleep(0.3)

    # ==================== Flyer Interface ====================
    def kickoff(self):
        status = DeviceStatus(self)
        self.acquire.put(1)
        status.set_finished()
        return status

    def complete(self):
        def check_done(value, old_value, **kwargs):
            return value == 0
        return SubscriptionStatus(self.acquire_rbv, check_done, timeout=600)

    def collect(self):
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


class KreiosSpectrum(Device):
    """
    Simplified KREIOS device for 1D spectrum acquisition.

    Use for basic XPS/UPS measurements.
    """
    acquire = Cpt(EpicsSignal, "Acquire", kind=Kind.omitted)
    acquire_rbv = Cpt(EpicsSignalRO, "Acquire_RBV", kind=Kind.normal)
    start_energy = Cpt(EpicsSignal, "StartEnergy", kind=Kind.config)
    end_energy = Cpt(EpicsSignal, "EndEnergy", kind=Kind.config)
    step_width = Cpt(EpicsSignal, "StepWidth", kind=Kind.config)
    pass_energy = Cpt(EpicsSignal, "PassEnergy", kind=Kind.config)
    define_spectrum = Cpt(EpicsSignal, "DefineSpectrum", kind=Kind.omitted)
    spectrum_valid = Cpt(EpicsSignalRO, "SpectrumValid_RBV", kind=Kind.normal)
    spectrum = Cpt(EpicsSignalRO, "Spectrum", kind=Kind.hinted)
    energy_axis = Cpt(EpicsSignalRO, "EnergyAxis", kind=Kind.normal)
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

    Use for ARPES or imaging measurements.
    """
    acquire = Cpt(EpicsSignal, "Acquire", kind=Kind.omitted)
    acquire_rbv = Cpt(EpicsSignalRO, "Acquire_RBV", kind=Kind.normal)
    start_energy = Cpt(EpicsSignal, "StartEnergy", kind=Kind.config)
    end_energy = Cpt(EpicsSignal, "EndEnergy", kind=Kind.config)
    step_width = Cpt(EpicsSignal, "StepWidth", kind=Kind.config)
    pass_energy = Cpt(EpicsSignal, "PassEnergy", kind=Kind.config)
    values_per_sample = Cpt(EpicsSignal, "ValuesPerSample", kind=Kind.config)
    define_spectrum = Cpt(EpicsSignal, "DefineSpectrum", kind=Kind.omitted)
    spectrum_valid = Cpt(EpicsSignalRO, "SpectrumValid_RBV", kind=Kind.normal)
    image = Cpt(EpicsSignalRO, "Image", kind=Kind.hinted)
    progress = Cpt(EpicsSignalRO, "Progress_RBV", kind=Kind.normal)

    def trigger(self):
        def check_done(value, old_value, **kwargs):
            return value == 0
        status = SubscriptionStatus(self.acquire_rbv, check_done, timeout=300)
        self.acquire.put(1)
        return status
