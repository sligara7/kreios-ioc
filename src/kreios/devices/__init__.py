"""
KREIOS Ophyd Device Classes.

This module provides ophyd device classes for the KREIOS-150 Momentum
Microscope photoelectron spectrometer.

Synchronous Devices (ophyd):
    - KreiosDetector: Full spectrometer control
    - KreiosSpectrum: Simplified 1D spectrum device
    - KreiosImage: Simplified 2D image device

Asynchronous Devices (ophyd-async):
    - KreiosDetectorAsync: Full spectrometer control (async)
    - KreiosSpectrumAsync: Simplified 1D spectrum device (async)
    - KreiosImageAsync: Simplified 2D image device (async)

Usage:
    # Synchronous (ophyd)
    from kreios.devices import KreiosDetector
    kreios = KreiosDetector("KREIOS:cam1:", name="kreios")
    kreios.wait_for_connection()

    # Asynchronous (ophyd-async)
    from kreios.devices import KreiosDetectorAsync
    kreios = KreiosDetectorAsync("KREIOS:cam1:", name="kreios")
    await kreios.connect()
"""

# Lazy imports to avoid requiring ophyd/ophyd-async when not needed


def __getattr__(name):
    """Lazy import of device classes."""
    # Synchronous ophyd devices
    sync_devices = {"KreiosDetector", "KreiosSpectrum", "KreiosImage"}
    if name in sync_devices:
        try:
            from ._sync import KreiosDetector, KreiosImage, KreiosSpectrum

            return {"KreiosDetector": KreiosDetector, "KreiosSpectrum": KreiosSpectrum, "KreiosImage": KreiosImage}[name]
        except ImportError as e:
            raise ImportError(
                f"Cannot import {name}: ophyd is required. "
                "Install with: pip install kreios-ioc[ophyd]"
            ) from e

    # Asynchronous ophyd-async devices
    async_devices = {
        "KreiosDetectorAsync",
        "KreiosSpectrumAsync",
        "KreiosImageAsync",
        "RunMode",
        "OperatingMode",
    }
    if name in async_devices:
        try:
            from ._async import (
                KreiosDetectorAsync,
                KreiosImageAsync,
                KreiosSpectrumAsync,
                OperatingMode,
                RunMode,
            )

            return {
                "KreiosDetectorAsync": KreiosDetectorAsync,
                "KreiosSpectrumAsync": KreiosSpectrumAsync,
                "KreiosImageAsync": KreiosImageAsync,
                "RunMode": RunMode,
                "OperatingMode": OperatingMode,
            }[name]
        except ImportError as e:
            raise ImportError(
                f"Cannot import {name}: ophyd-async is required. "
                "Install with: pip install kreios-ioc[ophyd-async]"
            ) from e

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Synchronous (ophyd)
    "KreiosDetector",
    "KreiosSpectrum",
    "KreiosImage",
    # Asynchronous (ophyd-async)
    "KreiosDetectorAsync",
    "KreiosSpectrumAsync",
    "KreiosImageAsync",
    "RunMode",
    "OperatingMode",
]
