# KREIOS Profile Collection

Profile collection providing ophyd devices and bluesky plans for the
KREIOS-150 photoelectron spectrometer IOC.

## Overview

This profile collection provides ophyd devices and bluesky plans for the KREIOS-150
momentum microscope / photoelectron spectrometer. It's designed to work with the
Docker-based KREIOS IOC from `/home/asligar/git_projects/systems/kreios_ioc`.

## PV Naming Convention

The KREIOS IOC uses areaDetector naming conventions:
- **Prefix**: `KREIOS:cam1:`
- **Examples**:
  - `KREIOS:cam1:Acquire` - Start acquisition
  - `KREIOS:cam1:StartEnergy` - Start energy (eV)
  - `KREIOS:cam1:EndEnergy` - End energy (eV)
  - `KREIOS:cam1:Connected_RBV` - Connection status

## Directory Structure

```
kreios-profile-collection/
├── README.md
├── startup/
│   ├── 00-environment.py      # Environment setup
│   ├── 10-devices.py          # KREIOS ophyd device definitions
│   ├── 20-bluesky.py          # RunEngine setup
│   ├── 90-plans.py            # KREIOS-specific plans
│   └── existing_plans_and_devices.yaml
└── pixi.toml                  # Dependencies (optional)
```

## Prerequisites

Start the KREIOS IOC Docker containers:

```bash
cd /home/asligar/git_projects/systems/kreios_ioc/docker
docker compose --profile full up -d
```

Verify the IOC is running:
```bash
docker compose logs ioc
```

## Environment Variables

- `KREIOS_PREFIX` - PV prefix (default: `KREIOS:cam1:`)
- `EPICS_CA_ADDR_LIST` - CA server address (default: `localhost`)

## Devices

| Device | Description | Key PVs |
|--------|-------------|---------|
| `kreios` | Main spectrometer control | Acquire, StartEnergy, EndEnergy, PassEnergy |
| `kreios_spectrum` | 1D spectrum readout | Spectrum array |
| `kreios_image` | 2D image readout | Image array |

## Plans

| Plan | Description |
|------|-------------|
| `kreios_xps_spectrum()` | Acquire XPS spectrum |
| `kreios_survey()` | Wide-range survey scan |
| `kreios_arpes_image()` | Angle-resolved imaging |

## Usage

```python
# Load the profile
%run -i startup/00-environment.py
%run -i startup/10-devices.py
%run -i startup/20-bluesky.py
%run -i startup/90-plans.py

# Configure and acquire spectrum
RE(kreios_xps_spectrum(start_e=280, end_e=300, step=0.1, pass_energy=20))
```

## Integration with Configuration Services

This profile can be loaded by configuration services to provide
KREIOS devices and plans for remote experiment execution.
