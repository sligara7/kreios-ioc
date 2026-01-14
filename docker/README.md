# Docker Setup for KREIOS-150 IOC

This directory contains Docker configurations for building and running the KREIOS-150 EPICS areaDetector IOC.

## Quick Start

### Run the Simulator Only (for protocol testing)

```bash
# Build and run the simulator
docker compose -f docker/docker-compose.yml up simulator

# In another terminal, test the connection
python3 scripts/test_connection.py localhost 7010
```

### Run Simulator + IOC (full testing)

```bash
# Build everything (this takes a while the first time - ~15-20 minutes)
docker compose -f docker/docker-compose.yml --profile full build

# Start simulator and IOC
docker compose -f docker/docker-compose.yml --profile full up
```

### Run Tests in Docker

```bash
# Build the test image
docker compose -f docker/docker-compose.yml --profile test build

# Run tests against the simulator
docker compose -f docker/docker-compose.yml up simulator -d
docker compose -f docker/docker-compose.yml --profile test run test

# Run all tests including EPICS IOC tests
docker compose -f docker/docker-compose.yml --profile full up -d
docker compose -f docker/docker-compose.yml --profile test run test pytest tests/ -v
```

## Docker Images

### `kreios-simulator` (Dockerfile.simulator)

Lightweight Python image that runs the Prodigy protocol simulator.

- **Base:** python:3.11-slim
- **Size:** ~150 MB
- **Ports:** 7010 (TCP)

```bash
docker build -t kreios-simulator -f docker/Dockerfile.simulator .
docker run -it --rm -p 7010:7010 kreios-simulator
```

### `kreios-ioc` (Dockerfile)

Full EPICS IOC with:
- EPICS Base 7.0.8
- asyn R4-44-2
- areaDetector ADCore R3-14 (commit d27d71fb)
- areaDetector ADSupport (commit 62b91c11)
- KREIOS driver

- **Base:** debian:bookworm-slim (multi-stage build)
- **Size:** ~1.07 GB
- **Ports:** 5064, 5065 (TCP/UDP for EPICS CA), 7010 (simulator)

```bash
docker build -t kreios-ioc -f docker/Dockerfile .
docker run -it --rm -p 5064:5064 -p 5065:5065 kreios-ioc
```

### `kreios-test` (Dockerfile.test)

Test runner with pytest and pyepics.

- **Base:** python:3.11-slim
- **Size:** ~200 MB

```bash
docker build -t kreios-test -f docker/Dockerfile.test .
docker run -it --rm kreios-test pytest tests/ -v
```

## Docker Compose Services

| Service | Description | Ports |
|---------|-------------|-------|
| `simulator` | Prodigy protocol simulator | 7010 |
| `ioc` | KREIOS EPICS IOC | 5064, 5065 |
| `test` | pytest test runner | - |

### Profiles

- `full` - Includes the IOC (slower to build)
- `test` - Includes the test runner

## Environment Variables

### Simulator/Test Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SIMULATOR_HOST` | localhost | Simulator hostname |
| `SIMULATOR_PORT` | 7010 | Simulator port |
| `USE_EXTERNAL_SIMULATOR` | 0 | Set to 1 to skip starting local simulator |

### EPICS Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EPICS_CA_ADDR_LIST` | localhost | Channel Access address list |
| `EPICS_CA_AUTO_ADDR_LIST` | NO | Auto-discover CA servers |
| `EPICS_CA_MAX_ARRAY_BYTES` | 10000000 | Max array size for CA |
| `EPICS_IOC_PREFIX` | KREIOS:cam1: | PV prefix for tests |
| `EPICS_IOC_AVAILABLE` | 0 | Set to 1 to enable IOC tests |

### IOC Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PRODIGY_HOST` | simulator | Prodigy server hostname |
| `PRODIGY_PORT` | 7010 | Prodigy server port |

## Building from Scratch

The full IOC build takes time because it compiles:
1. EPICS Base (~5 min)
2. asyn (~2 min)
3. ADSupport (~3 min)
4. ADCore (~5 min)
5. KREIOS driver (~1 min)

To speed up repeated builds, Docker caches intermediate layers.

### Build Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `EPICS_BASE_VERSION` | R7.0.8 | EPICS base version tag |
| `ASYN_VERSION` | R4-44-2 | asyn version tag |
| `ADCORE_VERSION` | R3-14 | ADCore version (uses commit hash d27d71fb) |
| `ADSUPPORT_VERSION` | R1-10 | ADSupport version (uses commit hash 62b91c11) |

**Note:** ADCore and ADSupport use specific commit hashes from the areaDetector R3-14
meta-repository rather than tags. See `docker/VERSION_NOTES.md` for details on version selection.

Example with custom versions:
```bash
docker build -t kreios-ioc \
  --build-arg EPICS_BASE_VERSION=R7.0.7 \
  --build-arg ADCORE_VERSION=R3-13 \
  -f docker/Dockerfile .
```

## Testing Workflow

### 1. Protocol Testing (no EPICS needed)

```bash
# Start simulator
docker compose -f docker/docker-compose.yml up simulator -d

# Run protocol tests
docker compose -f docker/docker-compose.yml --profile test run test \
  pytest tests/test_protocol.py tests/test_simulator.py tests/test_acquisition.py -v

# Stop
docker compose -f docker/docker-compose.yml down
```

### 2. Full IOC Testing

```bash
# Start everything
docker compose -f docker/docker-compose.yml --profile full up -d

# Wait for IOC to start (check logs)
docker compose -f docker/docker-compose.yml logs -f ioc

# Run all tests including EPICS tests
docker compose -f docker/docker-compose.yml --profile test run test \
  pytest tests/ -v --tb=short

# Stop
docker compose -f docker/docker-compose.yml --profile full down
```

### 3. Interactive Testing

```bash
# Start simulator
docker compose -f docker/docker-compose.yml up simulator -d

# Run interactive Python
docker run -it --rm --network kreios-ioc_kreios-net \
  -e SIMULATOR_HOST=simulator \
  kreios-test python3

>>> import socket
>>> s = socket.socket()
>>> s.connect(("simulator", 7010))
>>> s.send(b"?0001 Connect\n")
>>> print(s.recv(1024))
```

## Accessing EPICS PVs from Host

When the IOC is running in Docker, you can access PVs from the host:

```bash
# Set environment (adjust for your Docker setup)
export EPICS_CA_ADDR_LIST=localhost
export EPICS_CA_AUTO_ADDR_LIST=NO

# Use caget/caput (requires EPICS base installed on host)
caget KREIOS:cam1:Manufacturer_RBV
caput KREIOS:cam1:StartEnergy 400.0

# Or use Python with pyepics
pip install pyepics
python3 -c "import epics; print(epics.caget('KREIOS:cam1:Model_RBV'))"
```

## Troubleshooting

### Build fails with "out of memory"

Increase Docker memory limit (at least 4GB recommended).

### IOC can't connect to simulator

Check that both containers are on the same network:
```bash
docker network ls
docker network inspect kreios-ioc_kreios-net
```

### Channel Access not working

Ensure ports 5064 and 5065 are exposed and not blocked by firewall:
```bash
# Check ports
docker compose -f docker/docker-compose.yml ps
netstat -an | grep 5064
```

### Slow build times

Use Docker BuildKit for better caching:
```bash
DOCKER_BUILDKIT=1 docker build -t kreios-ioc -f docker/Dockerfile .
```
