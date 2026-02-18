"""
Shared helpers for pyepics-based IOC integration tests.

Provides PV prefix, caget/caput wrappers, and connection check
used by test_ioc_integration.py and test_ioc_new_commands.py.
"""

import os

# PV prefix for the deployed IOC
IOC_PREFIX = os.environ.get("EPICS_IOC_PREFIX", "XF:29ID2-ES{Det:Kreios}:cam1:")


def pv(name):
    """Build full PV name from suffix."""
    return f"{IOC_PREFIX}{name}"


def caget(name, **kwargs):
    """Get a PV value with default timeout. Requires pyepics."""
    import epics
    return epics.caget(pv(name), timeout=5.0, **kwargs)


def caput(name, value, **kwargs):
    """Put a PV value with default timeout, waiting for completion. Requires pyepics."""
    import epics
    return epics.caput(pv(name), value, wait=True, timeout=5.0, **kwargs)


def ioc_connected():
    """Check if IOC is running and connected to Prodigy."""
    val = caget("Connected_RBV")
    return val is not None and val == 1
