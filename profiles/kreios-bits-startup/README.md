# KREIOS BITS Startup

BITS-format (Bluesky Instrument Template System) profile for the
KREIOS-150 photoelectron spectrometer IOC.

## Overview

This profile uses the BITS configuration pattern for defining
devices and plans via YAML configuration files.

## Directory Structure

```
kreios-bits-startup/
├── README.md
├── configs/
│   ├── iconfig.yml          # Instrument configuration
│   └── devices.yml          # Device definitions (YAML)
├── devices/
│   ├── __init__.py          # Device exports
│   └── kreios_devices.py    # KREIOS ophyd device classes
├── plans/
│   ├── __init__.py          # Plan exports
│   └── kreios_plans.py      # KREIOS measurement plans
└── startup/
    └── existing_plans_and_devices.yaml
```

## Configuration

The instrument is configured via `configs/iconfig.yml` and devices
are defined in `configs/devices.yml`.

## Prerequisites

Start the KREIOS IOC Docker containers:

```bash
cd /home/asligar/git_projects/systems/kreios_ioc/docker
docker compose --profile full up -d
```

## Usage

```python
# Import devices
from devices import kreios

# Import plans
from plans import kreios_xps_spectrum, kreios_survey

# Run a measurement
RE(kreios_xps_spectrum(start_e=280, end_e=300))
```
