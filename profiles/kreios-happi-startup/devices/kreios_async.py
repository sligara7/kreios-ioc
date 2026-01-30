"""
KREIOS-150 Ophyd-Async Device Definitions.

This module re-exports the ophyd-async device classes from the main kreios package.
For implementation details, see: src/kreios/devices/_async.py

Device Classes:
- KreiosDetectorAsync: Full spectrometer control and readout
- KreiosSpectrumAsync: 1D spectrum-only device
- KreiosImageAsync: 2D image-only device

Example:
    >>> from devices.kreios_async import KreiosDetectorAsync
    >>> kreios = KreiosDetectorAsync("KREIOS:cam1:", name="kreios")
    >>> await kreios.connect()
"""

from kreios.devices import (
    KreiosDetectorAsync,
    KreiosImageAsync,
    KreiosSpectrumAsync,
    OperatingMode,
    RunMode,
)

__all__ = [
    "KreiosDetectorAsync",
    "KreiosSpectrumAsync",
    "KreiosImageAsync",
    "RunMode",
    "OperatingMode",
]
