"""
KREIOS-150 Ophyd-Async Device Definitions (Primary).

This module loads ophyd-async device classes from the main kreios package
and instantiates them for use in IPython/Bluesky sessions.

For implementation details, see: src/kreios/devices/_async.py

Device Classes:
- KreiosDetectorAsync: Full spectrometer control and readout
- KreiosSpectrumAsync: 1D spectrum-only device
- KreiosImageAsync: 2D image-only device
"""
print(f"Loading file {__file__!r} ...")

import asyncio
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

print(f"  Creating KREIOS devices with prefix: {KREIOS_PREFIX}")

# Device instances (names match what 90-plans.py expects)
kreios = KreiosDetectorAsync(KREIOS_PREFIX, name="kreios")
kreios_spectrum = KreiosSpectrumAsync(KREIOS_PREFIX, name="kreios_spectrum")
kreios_image = KreiosImageAsync(KREIOS_PREFIX, name="kreios_image")

# Connect devices
print("  Connecting to KREIOS IOC...")
try:
    loop = asyncio.get_event_loop()
    loop.run_until_complete(kreios.connect(timeout=10))
    loop.run_until_complete(kreios_spectrum.connect(timeout=5))
    loop.run_until_complete(kreios_image.connect(timeout=5))

    print(f"    kreios connected: {KREIOS_PREFIX}")
    try:
        mfr = loop.run_until_complete(kreios.manufacturer.get_value())
        model = loop.run_until_complete(kreios.model.get_value())
        conn = loop.run_until_complete(kreios.connected.get_value())
        print(f"    Manufacturer: {mfr}")
        print(f"    Model: {model}")
        print(f"    Connected to Prodigy: {conn}")
    except Exception as e:
        print(f"    Could not read device info: {e}")
except Exception as e:
    print(f"    WARNING: KREIOS IOC not available: {e}")
    print("    Start the IOC and retry connection with:")
    print("      await kreios.connect()")

print()
