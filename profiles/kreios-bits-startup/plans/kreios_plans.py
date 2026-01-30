"""
KREIOS-Specific Bluesky Plans.

Measurement plans for the KREIOS-150 photoelectron spectrometer.
"""

import bluesky.plan_stubs as bps
import bluesky.plans as bp


def kreios_xps_spectrum(kreios, start_e=280, end_e=300, step_e=0.1,
                        pass_energy=20.0, md=None):
    """
    Acquire a standard XPS spectrum (1D).

    Parameters
    ----------
    kreios : KreiosDetector
        The KREIOS device instance
    start_e : float
        Start energy in eV
    end_e : float
        End energy in eV
    step_e : float
        Energy step in eV
    pass_energy : float
        Analyzer pass energy in eV
    md : dict, optional
        Additional metadata

    Yields
    ------
    Msg
        Bluesky messages
    """
    _md = {
        "plan_name": "kreios_xps_spectrum",
        "start_energy": start_e,
        "end_energy": end_e,
        "step_width": step_e,
        "pass_energy": pass_energy,
        "measurement_type": "XPS",
        "data_dimensionality": "1D",
    }
    _md.update(md or {})

    yield from bps.mv(
        kreios.start_energy, start_e,
        kreios.end_energy, end_e,
        kreios.step_width, step_e,
        kreios.pass_energy, pass_energy,
        kreios.values_per_sample, 1,
        kreios.num_slices, 1,
    )
    yield from bps.sleep(0.2)
    yield from bps.mv(kreios.define_spectrum, 1)
    yield from bps.sleep(0.3)
    yield from bp.count([kreios], num=1, md=_md)


def kreios_survey(kreios, start_e=0, end_e=1200, step_e=1.0,
                  pass_energy=100.0, md=None):
    """
    Acquire a wide-range XPS survey spectrum.

    Parameters
    ----------
    kreios : KreiosDetector
        The KREIOS device instance
    start_e : float
        Start energy in eV
    end_e : float
        End energy in eV
    step_e : float
        Energy step in eV
    pass_energy : float
        Analyzer pass energy in eV
    md : dict, optional
        Additional metadata
    """
    _md = {
        "plan_name": "kreios_survey",
        "start_energy": start_e,
        "end_energy": end_e,
        "step_width": step_e,
        "pass_energy": pass_energy,
        "measurement_type": "XPS_survey",
        "data_dimensionality": "1D",
    }
    _md.update(md or {})

    yield from bps.mv(
        kreios.start_energy, start_e,
        kreios.end_energy, end_e,
        kreios.step_width, step_e,
        kreios.pass_energy, pass_energy,
        kreios.values_per_sample, 1,
        kreios.num_slices, 1,
    )
    yield from bps.sleep(0.2)
    yield from bps.mv(kreios.define_spectrum, 1)
    yield from bps.sleep(0.3)
    yield from bp.count([kreios], num=1, md=_md)


def kreios_arpes_image(kreios, start_e=80, end_e=90, step_e=0.05,
                       n_pixels=128, pass_energy=10.0, md=None):
    """
    Acquire an ARPES image (2D: energy x angle).

    Parameters
    ----------
    kreios : KreiosDetector
        The KREIOS device instance
    start_e : float
        Start energy in eV
    end_e : float
        End energy in eV
    step_e : float
        Energy step in eV
    n_pixels : int
        Number of detector pixels
    pass_energy : float
        Analyzer pass energy in eV
    md : dict, optional
        Additional metadata
    """
    _md = {
        "plan_name": "kreios_arpes_image",
        "start_energy": start_e,
        "end_energy": end_e,
        "step_width": step_e,
        "n_pixels": n_pixels,
        "pass_energy": pass_energy,
        "measurement_type": "ARPES",
        "data_dimensionality": "2D",
    }
    _md.update(md or {})

    yield from bps.mv(
        kreios.start_energy, start_e,
        kreios.end_energy, end_e,
        kreios.step_width, step_e,
        kreios.pass_energy, pass_energy,
        kreios.values_per_sample, n_pixels,
        kreios.num_slices, 1,
    )
    yield from bps.sleep(0.2)
    yield from bps.mv(kreios.define_spectrum, 1)
    yield from bps.sleep(0.3)
    yield from bp.count([kreios], num=1, md=_md)


def kreios_depth_profile(kreios, start_e=280, end_e=290, step_e=0.1,
                         n_pixels=1, n_slices=10,
                         pass_energy=20.0, md=None):
    """
    Acquire a depth profile (3D volume).

    Parameters
    ----------
    kreios : KreiosDetector
        The KREIOS device instance
    start_e : float
        Start energy in eV
    end_e : float
        End energy in eV
    step_e : float
        Energy step in eV
    n_pixels : int
        Number of detector pixels
    n_slices : int
        Number of depth slices
    pass_energy : float
        Analyzer pass energy in eV
    md : dict, optional
        Additional metadata
    """
    _md = {
        "plan_name": "kreios_depth_profile",
        "start_energy": start_e,
        "end_energy": end_e,
        "step_width": step_e,
        "n_pixels": n_pixels,
        "n_slices": n_slices,
        "pass_energy": pass_energy,
        "measurement_type": "depth_profile",
        "data_dimensionality": "3D",
    }
    _md.update(md or {})

    yield from bps.mv(
        kreios.start_energy, start_e,
        kreios.end_energy, end_e,
        kreios.step_width, step_e,
        kreios.pass_energy, pass_energy,
        kreios.values_per_sample, n_pixels,
        kreios.num_slices, n_slices,
    )
    yield from bps.sleep(0.2)
    yield from bps.mv(kreios.define_spectrum, 1)
    yield from bps.sleep(0.3)
    yield from bp.count([kreios], num=1, md=_md)


def kreios_quick_test(kreios, md=None):
    """
    Quick test acquisition for IOC connectivity.

    Parameters
    ----------
    kreios : KreiosDetector
        The KREIOS device instance
    md : dict, optional
        Additional metadata
    """
    _md = {
        "plan_name": "kreios_quick_test",
        "measurement_type": "test",
    }
    _md.update(md or {})

    yield from bps.mv(
        kreios.start_energy, 400,
        kreios.end_energy, 402,
        kreios.step_width, 0.5,
        kreios.pass_energy, 20,
        kreios.values_per_sample, 1,
        kreios.num_slices, 1,
    )
    yield from bps.sleep(0.2)
    yield from bps.mv(kreios.define_spectrum, 1)
    yield from bps.sleep(0.3)
    yield from bp.count([kreios], num=1, md=_md)
