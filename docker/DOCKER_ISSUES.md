# KREIOS IOC Docker Build Issues

**Date**: 2025-01-28
**Status**: All issues resolved - IOC fully operational

## Summary

Testing the KREIOS IOC Docker setup revealed several issues that prevented the EPICS IOC from running correctly. All issues have been identified and fixed. The IOC now starts successfully and all PVs are accessible.

---

## What Works

| Component | Status | Notes |
|-----------|--------|-------|
| Prodigy Simulator | ✅ Working | 35/35 protocol tests pass |
| Docker image builds | ✅ Working | Both simulator and IOC images build |
| Protocol communication | ✅ Working | Full SpecsLab Remote In v1.22 support |
| EPICS IOC | ✅ Working | All PVs accessible via Channel Access |

---

## Issues Found and Fixed

### 1. Obsolete `version` field in docker-compose.yml

**File**: `docker/docker-compose.yml`

**Problem**: Docker Compose V2 shows warning about obsolete `version` field.

**Fix Applied**: Removed `version: "3.8"` line.

---

### 2. Path mismatch in envPaths

**File**: `docker/Dockerfile` (runtime stage)

**Problem**: The `envPaths` file generated during build references `/build/kreios-ioc`, but the runtime stage copies files to `/opt/kreios-ioc`. This causes the IOC to fail loading databases.

**Fix Applied**: Added sed command to update paths and define KREIOS variable:

```dockerfile
# Fix paths in envPaths file (build paths -> runtime paths)
RUN sed -i 's|/build/kreios-ioc|/opt/kreios-ioc|g' /opt/kreios-ioc/iocBoot/iocKreios/envPaths \
    && echo 'epicsEnvSet("KREIOS","/opt/kreios-ioc")' >> /opt/kreios-ioc/iocBoot/iocKreios/envPaths
```

---

### 3. IOC process exits immediately

**File**: `docker/Dockerfile`

**Problem**: The EPICS IOC shell (iocsh) exits after processing `st.cmd` because there's no terminal/stdin. This causes the container to exit.

**Fix Applied**: Modified CMD to pipe `sleep infinity` to keep stdin open:

```dockerfile
CMD ["sh", "-c", "cd /opt/kreios-ioc/iocBoot/iocKreios && sleep infinity | ../../bin/${EPICS_HOST_ARCH}/kreios st.cmd"]
```

---

### 4. asyn Driver Not Registered

**Problem**: The IOC was failing to start with:
```
ERROR st.cmd line 40: Command drvAsynIPPortConfigure not found.
```

**Root Cause**: The `iocApp/src/Makefile` included `asyn.dbd` but was missing the explicit driver DBD files needed to register `drvAsynIPPortConfigure`.

**Fix Applied**: Added explicit driver DBD includes in `iocApp/src/Makefile`:
```makefile
kreios_DBD += drvAsynIPPort.dbd
kreios_DBD += drvAsynSerialPort.dbd
```

---

### 5. Missing busy Record Type

**Problem**: After fixing the asyn driver issue, the IOC failed with:
```
Record "KREIOS:cam1:AcquireBusy" is of unknown type "busy"
ERROR at or before ')' in path "/opt/epics/support/ADCore/db" file "NDArrayBase.template" line 119
```

**Root Cause**: The areaDetector `ADBase.template` uses the `busy` record type from the synApps `busy` module, which was not being built.

**Fix Applied**:

1. Added `busy` module build to `docker/Dockerfile`:
```dockerfile
RUN git clone --branch R1-7-4 --depth 1 \
    https://github.com/epics-modules/busy.git \
    && cd busy \
    && echo "EPICS_BASE=${EPICS_BASE}" > configure/RELEASE.local \
    && echo "SUPPORT=${EPICS_ROOT}/support" >> configure/RELEASE.local \
    && echo "BUSY=${EPICS_ROOT}/support/busy" >> configure/RELEASE.local \
    && echo "ASYN=${EPICS_ROOT}/support/asyn" >> configure/RELEASE.local \
    && sed -i '/testBusyAsyn/d' busyApp/src/Makefile \
    && make -j$(nproc)
```

2. Added BUSY to ADCore's RELEASE.local in Dockerfile

3. Added BUSY to KREIOS IOC's RELEASE.local in Dockerfile

4. Added `busySupport.dbd` and `busy` library to `iocApp/src/Makefile`:
```makefile
kreios_DBD += busySupport.dbd
kreios_LIBS += busy
```

---

### 6. ADCore iocBoot Directory Build Failure

**Problem**: ADCore's Makefile tries to build example IOCs in iocBoot which have additional dependencies.

**Fix Applied**: Skip iocBoot directory during ADCore build:
```dockerfile
&& sed -i '/iocBoot/d' Makefile \
```

---

## Testing Commands

### Test Simulator Only
```bash
cd docker
docker compose up -d simulator
docker compose --profile test run --rm test pytest tests/test_protocol.py -v
docker compose down
```

### Test Full Stack
```bash
cd docker
docker compose --profile full up -d
docker compose logs ioc  # Check for errors
docker compose exec ioc caget KREIOS:cam1:Connected_RBV
docker compose --profile full down
```

### Debug IOC Interactively
```bash
docker compose up -d simulator
docker run -it --rm --network docker_kreios-net \
  -e PRODIGY_HOST=docker-simulator-1 \
  -e PRODIGY_PORT=7010 \
  docker-ioc /bin/bash

# Inside container:
cd /opt/kreios-ioc/iocBoot/iocKreios
cat envPaths  # Verify paths
../../bin/linux-x86_64/kreios st.cmd  # Run IOC manually
```

---

## Files Modified

| File | Change |
|------|--------|
| `docker/docker-compose.yml` | Removed obsolete `version: "3.8"` |
| `docker/Dockerfile` | Added full synApps module stack, envPaths fix, autosave directory |
| `iocApp/src/Makefile` | Added all synApps DBDs and libraries for production IOC |
| `iocBoot/iocKreios/st.cmd` | Production startup with commonPlugins, autosave, iocStats |
| `iocBoot/iocKreios/auto_settings.req` | Autosave request file |
| `iocBoot/iocKreios/kreios_settings.req` | KREIOS-specific autosave settings |
| `configure/RELEASE` | Updated with all required module paths |

---

## Production synApps Modules

The following synApps modules are now built into the Docker image:

| Module | Version | Purpose |
|--------|---------|---------|
| asyn | R4-44-2 | Communication layer |
| seq | R2-2-9 | State notation compiler/sequencer |
| sscan | R2-11-6 | Scan support |
| calc | R3-7-5 | Calculation records |
| autosave | R5-11 | PV value persistence |
| iocStats | 3.2.0 | IOC health monitoring |
| busy | R1-7-4 | Busy record support |

---

## Production Features

The IOC now includes:

1. **Autosave** - PV settings are saved every 30 seconds and restored on IOC restart
2. **iocStats** - IOC health monitoring PVs (CPU, memory, heartbeat)
3. **NDStdArrays** - Image plugin for live display in Phoebus/CSS
4. **commonPlugins** - Standard areaDetector plugin chain (Stats, ROI, Process, etc.)
5. **Network Configuration** - Proper EPICS CA/PVA settings for production networks

---

## Production Test Results

**Test Date**: 2026-01-28
**Status**: All tests passed ✓

### Test Summary

| Category | Status | Details |
|----------|--------|---------|
| KREIOS Driver | ✓ Pass | Connected to simulator, all detector settings accessible |
| Detector ID | ✓ Pass | SPECS GmbH KREIOS-150, FAT mode |
| Analyzer Settings | ✓ Pass | Pass Energy: 10 eV, Kinetic Energy: 300 eV |
| Image Plugins | ✓ Pass | 10 plugins loaded and operational |
| File Plugins | ✓ Pass | TIFF, JPEG, HDF5, NetCDF available |
| iocStats | ✓ Pass | Health monitoring active (7624 records) |
| Autosave | ✓ Pass | Auto-rotating save files every 30 seconds |
| Network Config | ✓ Pass | CA configured for production |

### areaDetector Plugins Verified

```
image1:  NDPluginStdArrays
Stats1:  NDPluginStats
ROI1:    NDPluginROI
Trans1:  NDPluginTransform
Proc1:   NDPluginProcess
Over1:   NDPluginOverlay
CC1:     NDPluginColorConvert
CB1:     NDPluginCircularBuff
Attr1:   NDPluginAttribute
FFT1:    NDPluginFFT
```

### File Plugins Verified

```
TIFF1:    NDFileTIFF
JPEG1:    NDFileJPEG
HDF1:     NDFileHDF5 ver1.10.8
netCDF1:  NDFileNetCDF
```

### iocStats Health Monitoring

```
KREIOS:ioc:HEARTBEAT      302
KREIOS:ioc:STARTTOD       01/28/2026 16:28:47
KREIOS:ioc:SYS_CPU_LOAD   1.90801%
KREIOS:ioc:MEM_USED       6.7584e+07 bytes
KREIOS:ioc:RECORD_CNT     7624
KREIOS:ioc:UPTIME         00:05:02
```

### Autosave Verification

```
$ ls /opt/kreios-ioc/iocBoot/iocKreios/autosave/
auto_settings.sav
auto_settings.sav0
auto_settings.sav1
auto_settings.sav2
auto_settings.savB
```

### Core KREIOS PVs

```
KREIOS:cam1:Connected_RBV      Connected
KREIOS:cam1:Manufacturer_RBV   SPECS GmbH
KREIOS:cam1:Model_RBV          KREIOS-150
KREIOS:cam1:RunMode_RBV        FAT
KREIOS:cam1:PassEnergy_RBV     10
KREIOS:cam1:KineticEnergy_RBV  300
KREIOS:cam1:AcquireTime        1
KREIOS:cam1:NumImages          1
KREIOS:cam1:ImageMode          Continuous
```

---

## Related Files

- `iocApp/src/Makefile` - IOC build configuration
- `kreiosApp/src/Makefile` - Driver library build
- `configure/RELEASE` - Dependency paths
- `iocBoot/iocKreios/st.cmd` - IOC startup script
- `iocBoot/iocKreios/envPaths` - Environment paths (auto-generated)
