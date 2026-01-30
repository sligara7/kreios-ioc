"""
KREIOS-150 Ophyd-Async Device Definitions.

This module loads ophyd-async device classes from the main kreios package
and instantiates them for use in IPython/Bluesky sessions.

For implementation details, see: src/kreios/devices/_async.py

Device Classes:
- KreiosDetectorAsync: Full spectrometer control and readout
- KreiosSpectrumAsync: 1D spectrum-only device
- KreiosImageAsync: 2D image-only device
"""
print(f"Loading file {__file__!r} ...")

import os

from kreios.devices import (
    KreiosDetectorAsync,
    KreiosImageAsync,
    KreiosSpectrumAsync,
    OperatingMode,
    RunMode,
)

# Get PV prefix from environment
KREIOS_PREFIX = os.environ.get("KREIOS_PREFIX", "KREIOS:cam1:")

print(f"  Creating KREIOS async devices with prefix: {KREIOS_PREFIX}")

# Async device instances (must be connected with: await kreios_async.connect())
kreios_async = KreiosDetectorAsync(KREIOS_PREFIX, name="kreios_async")
kreios_spectrum_async = KreiosSpectrumAsync(KREIOS_PREFIX, name="kreios_spectrum_async")
kreios_image_async = KreiosImageAsync(KREIOS_PREFIX, name="kreios_image_async")

print("  Note: Async devices require connection via: await kreios_async.connect()")
print()
