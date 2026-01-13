# KREIOS-150 areaDetector Driver

EPICS areaDetector driver for the SPECS KREIOS-150 Momentum Microscope.

## Overview

This driver interfaces with the SPECS KREIOS-150 via the SpecsLab Prodigy Remote In protocol (v1.2). It extends the standard ADDriver class to provide full areaDetector compatibility while supporting the unique data dimensionality of the KREIOS detector.

## Data Dimensionality

The KREIOS-150 supports three data modes:

| Mode | Dimensions | Parameters | Use Case |
|------|------------|------------|----------|
| 1D | (samples,) | ValuesPerSample=1, NumSlices=1 | Standard XPS/UPS spectroscopy |
| 2D | (samples, pixels) | ValuesPerSample>1, NumSlices=1 | Angle-resolved, imaging |
| 3D | (slices, samples, pixels) | ValuesPerSample>1, NumSlices>1 | Depth profiling, multi-region |

## KREIOS-150 Specifications

- **Detector**: 2D CMOS (1285 x 730 channels)
- **Energy Range**: 0-1500 eV kinetic energy
- **Pass Energies**: 1-200 eV (continuously adjustable)
- **Energy Resolution**: <25 meV (momentum), <10 meV (spectroscopy)
- **Angular Resolution**: <0.1 degrees
- **Momentum Resolution**: 0.005-0.008 A^-1

## Run Modes

| Mode | Description |
|------|-------------|
| FAT | Fixed Analyzer Transmission - standard energy scan |
| SFAT | Snapshot FAT - fast parallel acquisition |
| FRR | Fixed Retard Ratio - constant relative resolution |
| FE | Fixed Energies - multiple discrete energies |
| LVS | Logical Voltage Scan - custom voltage sweeps |

## Operating Modes

| Mode | Description |
|------|-------------|
| Spectroscopy | Energy-resolved measurements |
| Momentum | k-space mapping (ARPES) |
| PEEM | Photoemission electron microscopy |

## Building

### Requirements

- EPICS base 7.0+
- areaDetector (ADCore, ADSupport)
- asyn driver

### Configuration

Edit `configure/RELEASE` to set paths:

```makefile
EPICS_BASE = /path/to/epics/base
SUPPORT = /path/to/epics/support
ASYN = $(SUPPORT)/asyn
AREA_DETECTOR = /path/to/areaDetector
ADCORE = $(AREA_DETECTOR)/ADCore
ADSUPPORT = $(AREA_DETECTOR)/ADSupport
```

### Build

```bash
make clean
make
```

## IOC Configuration

### st.cmd Example

```bash
# Configure Prodigy connection
drvAsynIPPortConfigure("PRODIGY", "localhost:7010", 0, 0, 0)

# Create KREIOS driver
kreiosConfig("KREIOS1", "PRODIGY", 0, 0, 0, 0)

# Load database
dbLoadRecords("kreios.template", "P=KREIOS:,R=cam1:,PORT=KREIOS1")
```

## Key PVs

### Connection
- `$(P)$(R)Connect` - Force connection to Prodigy
- `$(P)$(R)Connected_RBV` - Connection status

### Acquisition Mode
- `$(P)$(R)RunMode` - FAT/SFAT/FRR/FE/LVS
- `$(P)$(R)OperatingMode` - Spectroscopy/Momentum/PEEM

### Energy Parameters
- `$(P)$(R)StartEnergy` - Start energy (eV)
- `$(P)$(R)EndEnergy` - End energy (eV)
- `$(P)$(R)StepWidth` - Energy step (eV)
- `$(P)$(R)PassEnergy` - Pass energy (eV)

### Dimension Parameters
- `$(P)$(R)ValuesPerSample` - Pixels per energy point (1=1D, >1=2D/3D)
- `$(P)$(R)NumSlices` - Number of slices (1=1D/2D, >1=3D)

### Data Arrays
- `$(P)$(R)Spectrum` - 1D integrated spectrum
- `$(P)$(R)Image` - 2D image data
- `$(P)$(R)Volume` - 3D volume data

### Progress
- `$(P)$(R)Progress_RBV` - Overall progress (%)
- `$(P)$(R)CurrentSample_RBV` - Current sample number

## Files

```
kreiosApp/
├── src/
│   ├── kreios.h          # Driver header
│   ├── kreios.cpp        # Driver implementation
│   ├── kreiosSupport.dbd # DBD registration
│   └── Makefile
├── Db/
│   ├── kreios.template   # EPICS database
│   └── Makefile
└── Makefile
```

## Protocol Commands

The driver implements the Prodigy Remote In protocol:

| Command | Description |
|---------|-------------|
| Connect | Establish connection |
| Disconnect | Close connection |
| DefineSpectrumFAT | Define FAT spectrum |
| DefineSpectrumSFAT | Define snapshot spectrum |
| ValidateSpectrum | Validate spectrum parameters |
| Start | Start acquisition |
| Pause/Resume | Pause/resume acquisition |
| Abort | Abort acquisition |
| GetAcquisitionStatus | Poll status |
| GetAcquisitionData | Read data |

## Testing

Use the included simulator:

```bash
# Start simulator
cd sim
python3 ProdigySimServer.py

# Test connection
python3 scripts/test_connection.py localhost 7010
```

## Author

NSLS-II / SPECS Integration
January 2026
