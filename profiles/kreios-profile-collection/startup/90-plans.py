"""
KREIOS-Specific Bluesky Plans.

Custom plans for KREIOS-150 photoelectron spectrometer measurements.
These plans configure the spectrometer and acquire data using
the ophyd-async devices defined in 11-devices-async.py.

Note: Devices (kreios, kreios_spectrum, kreios_image) are available
in the global namespace from earlier startup scripts. This follows
the pattern used by real profile collections (tst, xpd).
"""
print(f"Loading file {__file__!r} ...")

import bluesky.plan_stubs as bps
import bluesky.plans as bp


def kreios_xps_spectrum(start_e=280, end_e=300, step_e=0.1,
                        pass_energy=20.0, md=None):
    """
    Acquire a standard XPS spectrum.

    This is the most common measurement: a 1D energy scan with
    integrated intensity at each point.

    Parameters
    ----------
    start_e : float
        Start energy in eV (default: 280)
    end_e : float
        End energy in eV (default: 300)
    step_e : float
        Energy step in eV (default: 0.1)
    pass_energy : float
        Analyzer pass energy in eV (default: 20)
    md : dict, optional
        Additional metadata

    Yields
    ------
    Msg
        Bluesky messages for RunEngine

    Example
    -------
    >>> RE(kreios_xps_spectrum(start_e=280, end_e=300, step_e=0.1))
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

    # Configure spectrometer for 1D acquisition
    yield from bps.mv(
        kreios.start_energy, start_e,
        kreios.end_energy, end_e,
        kreios.step_width, step_e,
        kreios.pass_energy, pass_energy,
        kreios.values_per_sample, 1,
        kreios.num_slices, 1,
    )

    # Define spectrum
    yield from bps.sleep(0.2)
    yield from bps.mv(kreios.define_spectrum, 1)
    yield from bps.sleep(0.3)

    # Acquire using count plan
    yield from bp.count([kreios], num=1, md=_md)


def kreios_survey(start_e=0, end_e=1200, step_e=1.0,
                  pass_energy=100.0, md=None):
    """
    Acquire a wide-range XPS survey spectrum.

    Fast, low-resolution scan to identify elements present.

    Parameters
    ----------
    start_e : float
        Start energy in eV (default: 0)
    end_e : float
        End energy in eV (default: 1200)
    step_e : float
        Energy step in eV (default: 1.0)
    pass_energy : float
        Analyzer pass energy in eV (default: 100)
    md : dict, optional
        Additional metadata

    Yields
    ------
    Msg
        Bluesky messages for RunEngine
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


def kreios_arpes_image(start_e=80, end_e=90, step_e=0.05,
                       n_pixels=128, pass_energy=10.0, md=None):
    """
    Acquire an ARPES (angle-resolved) image.

    2D acquisition: energy axis x detector pixels (angular resolution).

    Parameters
    ----------
    start_e : float
        Start energy in eV (default: 80)
    end_e : float
        End energy in eV (default: 90)
    step_e : float
        Energy step in eV (default: 0.05)
    n_pixels : int
        Number of detector pixels (default: 128)
    pass_energy : float
        Analyzer pass energy in eV (default: 10)
    md : dict, optional
        Additional metadata

    Yields
    ------
    Msg
        Bluesky messages for RunEngine
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


def kreios_depth_profile(start_e=280, end_e=290, step_e=0.1,
                         n_pixels=1, n_slices=10,
                         pass_energy=20.0, md=None):
    """
    Acquire a depth profile (3D volume).

    Multiple iterations with sputtering between each slice.
    Note: Sputtering control is not included - this just acquires
    multiple spectra that can be correlated with external sputtering.

    Parameters
    ----------
    start_e : float
        Start energy in eV (default: 280)
    end_e : float
        End energy in eV (default: 290)
    step_e : float
        Energy step in eV (default: 0.1)
    n_pixels : int
        Number of detector pixels (default: 1 for 1D per slice)
    n_slices : int
        Number of depth slices (default: 10)
    pass_energy : float
        Analyzer pass energy in eV (default: 20)
    md : dict, optional
        Additional metadata

    Yields
    ------
    Msg
        Bluesky messages for RunEngine
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


def kreios_quick_test(md=None):
    """
    Quick test acquisition for verifying IOC connectivity.

    Short, fast acquisition for testing the KREIOS IOC setup.

    Parameters
    ----------
    md : dict, optional
        Additional metadata

    Yields
    ------
    Msg
        Bluesky messages for RunEngine
    """
    _md = {
        "plan_name": "kreios_quick_test",
        "measurement_type": "test",
    }
    _md.update(md or {})

    # Very short acquisition
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


# =============================================================================
# Plan Registry
# =============================================================================

KREIOS_PLANS = {
    "kreios_xps_spectrum": kreios_xps_spectrum,
    "kreios_survey": kreios_survey,
    "kreios_arpes_image": kreios_arpes_image,
    "kreios_depth_profile": kreios_depth_profile,
    "kreios_quick_test": kreios_quick_test,
}

print("  KREIOS plans loaded:")
for name in KREIOS_PLANS:
    print(f"    - {name}")
print()
