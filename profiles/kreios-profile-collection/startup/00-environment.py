"""
Environment setup for KREIOS IOC connection.

Sets up EPICS Channel Access environment variables for connecting
to the KREIOS-150 areaDetector IOC.
"""
print(f"Loading file {__file__!r} ...")

import os

# EPICS Channel Access configuration
# For Docker: use 'localhost' if IOC ports are mapped to host
# For Docker network: use container name or IP
os.environ.setdefault("EPICS_CA_ADDR_LIST", "localhost")
os.environ.setdefault("EPICS_CA_AUTO_ADDR_LIST", "NO")
os.environ.setdefault("EPICS_CA_MAX_ARRAY_BYTES", "10000000")

# KREIOS PV prefix (areaDetector convention)
KREIOS_PREFIX = os.environ.get("KREIOS_PREFIX", "KREIOS:cam1:")

print(f"  KREIOS_PREFIX: {KREIOS_PREFIX}")
print(f"  EPICS_CA_ADDR_LIST: {os.environ.get('EPICS_CA_ADDR_LIST')}")
