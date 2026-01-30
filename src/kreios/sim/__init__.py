"""
KREIOS Prodigy Protocol Simulator.

This module provides a TCP server that simulates the SpecsLab Prodigy
Remote In protocol (v1.2) for KREIOS-150 detector testing.

Usage:
    # As a CLI command (after installing the package):
    kreios-simulator

    # Or programmatically:
    from kreios.sim import ProdigySimServer, ProdigySimHandler, main
    main()

The simulator supports:
- FAT (Fixed Analyzer Transmission) mode
- SFAT (Snapshot FAT) mode
- FRR (Fixed Retarding Ratio) mode
- FE (Fixed Energies) mode
- LVS (Logical Voltage Scan) mode
- 1D/2D/3D data acquisition simulation
"""

import os
import sys

# Add the legacy sim directory to path for imports
_sim_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "sim")
if os.path.isdir(_sim_dir) and _sim_dir not in sys.path:
    sys.path.insert(0, _sim_dir)

try:
    from ProdigySimServer import (
        AcquisitionState,
        ProdigySimHandler,
        ProdigySimServer,
        main,
    )
except ImportError:
    # Fallback: define stubs if sim directory is not available
    # This allows the package to be imported even without the simulator
    import warnings
    warnings.warn(
        "Simulator code not found. Install from source to use the simulator.",
        ImportWarning,
    )

    class AcquisitionState:
        pass

    class ProdigySimHandler:
        pass

    class ProdigySimServer:
        pass

    def main():
        raise NotImplementedError("Simulator not available")


__all__ = [
    "AcquisitionState",
    "ProdigySimHandler",
    "ProdigySimServer",
    "main",
]
