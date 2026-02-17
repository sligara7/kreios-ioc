# ADKreios

EPICS areaDetector driver for the SPECS KREIOS-150 momentum microscope.

## Overview

ADKreios interfaces with the KREIOS-150 via the SpecsLab Prodigy Remote In
protocol (v1.22, TCP port 7010). It supports 1D (spectrum), 2D (image), and
3D (volume) data acquisition across all operating modes: Spectroscopy,
Momentum Microscopy, and PEEM.

This driver replaces the older specsAnalyser driver (1D-only, circa 2017) with
full 2D/3D support and all 27 Prodigy protocol commands.

## KREIOS-150 Specifications

| Parameter | Value |
|-----------|-------|
| Detector | 2D CMOS, 1285 x 730 channels |
| Kinetic energy range | 0-1500 eV |
| Pass energies | 1-200 eV (continuously adjustable) |
| Acceptance angle | +/-90 degrees full cone |
| Energy resolution | <25 meV (momentum), <10 meV (spectroscopy) |
| Angular resolution | <0.1 degrees |
| Momentum resolution | 0.005-0.008 A^-1 |
| Lateral resolution | 35-50 nm |

## Supported Features

- **Acquisition modes**: FAT, SFAT, FRR, FE, LVS
- **Operating modes**: Spectroscopy, Momentum Microscopy, PEEM
- **Data dimensionality**: 1D spectrum, 2D image, 3D volume
- **Full protocol support**: All 27 Prodigy Remote In commands
- **Spectrum validation**: CheckSpectrum with server-side parameter validation
- **Direct voltage control**: SetAnalyzerParameterValueDirectly
- **Device management**: GetAllDevices, device parameter query interface
- **Live parameters**: Real-time parameter readback

## Building

### Prerequisites

- EPICS Base R7.0.8+
- areaDetector ADCore R3.12+
- synApps: asyn, calc, sscan, autosave, busy, devIocStats, seq

### Standalone build

Create `configure/RELEASE.local` with paths to your EPICS installation:

```makefile
EPICS_BASE=/opt/epics/base
SUPPORT=/opt/epics/support
ASYN=$(SUPPORT)/asyn
SNCSEQ=$(SUPPORT)/seq
SSCAN=$(SUPPORT)/sscan
CALC=$(SUPPORT)/calc
AUTOSAVE=$(SUPPORT)/autosave
DEVIOCSTATS=$(SUPPORT)/iocStats
BUSY=$(SUPPORT)/busy
AREA_DETECTOR=$(SUPPORT)
ADCORE=$(SUPPORT)/ADCore
ADSUPPORT=$(SUPPORT)/ADSupport
```

Then build:

```bash
make
```

### areaDetector umbrella build

Place ADKreios alongside other areaDetector modules. The `configure/RELEASE`
include chain will pick up paths from the umbrella `RELEASE_LIBS_INCLUDE`.

### Building the example IOC

```bash
cd iocs/kreiosIOC
# Create configure/RELEASE.local if not using umbrella build
make
```

## Running the IOC

```bash
cd iocs/kreiosIOC/iocBoot/iocKreios
# Set Prodigy server address:
export PRODIGY_HOST=10.67.228.10
export PRODIGY_PORT=7010
../../bin/linux-x86_64/kreios st.cmd
```

## Configuration

Key environment variables in `st.cmd`:

| Variable | Default | Description |
|----------|---------|-------------|
| PREFIX | KREIOS: | PV name prefix |
| PORT | KREIOS1 | Asyn port name |
| PRODIGY_HOST | localhost | Prodigy server IP address |
| PRODIGY_PORT | 7010 | Prodigy server TCP port |
| XSIZE | 1285 | Detector X pixels |
| YSIZE | 730 | Detector Y pixels |

## Protocol

Communication uses the SpecsLab Prodigy Remote In protocol:

- Request: `?<4-hex-id> Command [key:value ...]`
- Response: `!<id> OK[: key:value ...]` or `!<id> Error: <code> "message"`

## Comparison to specsAnalyser

| Feature | specsAnalyser | ADKreios |
|---------|--------------|----------|
| Data dimensions | 1D only | 1D, 2D, 3D |
| Protocol commands | ~10 | All 27 |
| Operating modes | Spectroscopy | Spectroscopy, Momentum, PEEM |
| Device query | None | Full query interface |
| Direct voltage | None | Supported |
