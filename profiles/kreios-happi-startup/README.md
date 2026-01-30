# KREIOS Happi Startup

Happi-format device database for the KREIOS-150 photoelectron spectrometer IOC.

## Overview

This profile uses the Happi device database format for device discovery
and instantiation. Happi provides a structured way to store device
metadata and instantiate ophyd devices.

## Directory Structure

```
kreios-happi-startup/
├── README.md
├── happi.cfg                    # Happi backend configuration
├── happi_db.json                # Device database (JSON)
├── plans/
│   ├── __init__.py
│   └── kreios_plans.py
└── startup/
    └── existing_plans_and_devices.yaml
```

## Prerequisites

Start the KREIOS IOC Docker containers:

```bash
cd /home/asligar/git_projects/systems/kreios_ioc/docker
docker compose --profile full up -d
```

## Configuration

Set the `HAPPI_CFG` environment variable to point to the config file:

```bash
export HAPPI_CFG=/path/to/kreios-happi-startup/happi.cfg
```

## Usage

```python
from happi import Client

# Load client from configuration
client = Client.from_config()

# Search for KREIOS devices
kreios_devices = client.search(beamline="KREIOS-150")

# Load a specific device
kreios = client.load_device(name="kreios")

# Use the device
kreios.wait_for_connection()
print(kreios.connected.get())
```

## Device Entries

| Name | Type | Description |
|------|------|-------------|
| kreios | KreiosDetector | Full spectrometer control |
| kreios_spectrum | KreiosSpectrum | Simplified 1D device |
| kreios_image | KreiosImage | Simplified 2D device |

## Metadata Fields

Each device entry includes:
- `beamline`: "KREIOS-150"
- `location_group`: Physical location
- `functional_group`: Device category
- `active`: Whether device is active
- `documentation`: Device description
