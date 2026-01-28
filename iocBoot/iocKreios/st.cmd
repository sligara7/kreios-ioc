#!../../bin/linux-x86_64/kreios

#- KREIOS-150 Momentum Microscope IOC Startup Script
#-
#- This IOC interfaces with the SPECS KREIOS-150 momentum microscope
#- via the SpecsLab Prodigy Remote In protocol.
#-
#- Data dimensionality support:
#-   1D - Integrated spectrum (energy axis only)
#-   2D - Image (energy x detector pixels)
#-   3D - Volume (slices x energy x pixels)

#- Initialize error logging with scrollback buffer
errlogInit(20000)

#- Network configuration for Channel Access
#- These settings prevent broadcast storms on large networks
#- For Docker: uses localhost only
#- For production: adjust EPICS_CA_ADDR_LIST to include IOC subnet
epicsEnvSet("EPICS_CA_AUTO_ADDR_LIST",          "NO")
epicsEnvSet("EPICS_CA_ADDR_LIST",               "127.0.0.1")
epicsEnvSet("EPICS_CAS_AUTO_BEACON_ADDR_LIST",  "NO")
epicsEnvSet("EPICS_CAS_BEACON_ADDR_LIST",       "127.0.0.1")
epicsEnvSet("EPICS_CAS_INTF_ADDR_LIST",         "127.0.0.1")

#- PVAccess network configuration
epicsEnvSet("EPICS_PVA_AUTO_ADDR_LIST",         "NO")
epicsEnvSet("EPICS_PVA_ADDR_LIST",              "127.0.0.1")
epicsEnvSet("EPICS_PVAS_AUTO_BEACON_ADDR_LIST", "NO")
epicsEnvSet("EPICS_PVAS_BEACON_ADDR_LIST",      "127.0.0.1")
epicsEnvSet("EPICS_PVAS_INTF_ADDR_LIST",        "127.0.0.1")

< envPaths

#- IOC identification
epicsEnvSet("ENGINEER", "")
epicsEnvSet("LOCATION", "")
epicsEnvSet("IOCNAME",  "iocKreios")

#- Environment Variables
epicsEnvSet("PREFIX", "KREIOS:")
epicsEnvSet("PORT", "KREIOS1")
epicsEnvSet("QSIZE", "20")
epicsEnvSet("XSIZE", "1285")
epicsEnvSet("YSIZE", "730")
epicsEnvSet("NCHANS", "100000")
epicsEnvSet("CBUFFS", "500")
epicsEnvSet("MAX_THREADS", "5")
epicsEnvSet("EPICS_DB_INCLUDE_PATH", "$(ADCORE)/db:$(KREIOS)/db")

#- Prodigy server connection parameters
#- Reads from environment variables PRODIGY_HOST and PRODIGY_PORT
#- Default: localhost:7010 (simulator)
#- Production: Set PRODIGY_HOST=<prodigy_server_ip> in environment
#- Docker: Set via docker-compose environment section
epicsEnvSet("PRODIGY_HOST", "${PRODIGY_HOST=localhost}")
epicsEnvSet("PRODIGY_PORT", "${PRODIGY_PORT=7010}")

cd "${TOP}"

#- Register all support components
dbLoadDatabase "dbd/kreios.dbd"
kreios_registerRecordDeviceDriver pdbbase

#- Create asyn port for Prodigy communication
drvAsynIPPortConfigure("PRODIGY", "$(PRODIGY_HOST):$(PRODIGY_PORT)", 0, 0, 0)

#- Optional: set asyn trace for debugging
#asynSetTraceIOMask("PRODIGY", 0, 2)
#asynSetTraceMask("PRODIGY", 0, 9)

#- Create the KREIOS driver
#- kreiosConfig(portName, driverPort, maxBuffers, maxMemory, priority, stackSize)
kreiosConfig("$(PORT)", "PRODIGY", 0, 0, 0, 0)
epicsThreadSleep(2)

#- Load KREIOS database
dbLoadRecords("$(KREIOS)/db/kreios.template", "P=$(PREFIX),R=cam1:,PORT=$(PORT),ADDR=0,TIMEOUT=1")

#- ===========================================================================
#- Standard areaDetector plugins
#- ===========================================================================

#- NDStdArrays plugin for image viewing in Phoebus/CSS/ImageJ
NDStdArraysConfigure("Image1", $(QSIZE), 0, "$(PORT)", 0, 0, 0, 0, 0, $(MAX_THREADS))
dbLoadRecords("$(ADCORE)/db/NDStdArrays.template", "P=$(PREFIX),R=image1:,PORT=Image1,ADDR=0,TIMEOUT=1,NDARRAY_PORT=$(PORT),TYPE=Float64,FTVL=DOUBLE,NELEMENTS=$(NCHANS)")

#- Load all standard areaDetector plugins from ADCore
#- This includes: Stats, ROI, Process, Overlay, FFT, etc.
< $(ADCORE)/iocBoot/commonPlugins.cmd

#- ===========================================================================
#- IOC Statistics (devIocStats)
#- ===========================================================================
#- Provides PVs for monitoring IOC health: CPU usage, memory, heartbeat, etc.
dbLoadRecords("$(DEVIOCSTATS)/db/iocAdminSoft.db", "IOC=$(PREFIX)ioc")

#- ===========================================================================
#- Autosave configuration
#- ===========================================================================
#- Set paths for autosave request files and save files
set_requestfile_path("$(KREIOS)/iocBoot/$(IOC)")
set_requestfile_path("$(ADCORE)/iocBoot")
set_requestfile_path("$(ADCORE)/ADApp/Db")
set_requestfile_path("$(CALC)/calcApp/Db")
set_requestfile_path("$(SSCAN)/sscanApp/Db")

set_savefile_path("$(KREIOS)/iocBoot/$(IOC)/autosave")

#- Note: autosave directory is created by Dockerfile
#- For non-Docker deployments, create manually: mkdir -p iocBoot/iocKreios/autosave

#- Autosave settings: restore on boot, periodic save
set_pass0_restoreFile("auto_settings.sav")
set_pass1_restoreFile("auto_settings.sav")

#- Initialize IOC
cd "${TOP}/iocBoot/${IOC}"
iocInit

#- Start autosave - save settings every 30 seconds
create_monitor_set("auto_settings.req", 30, "P=$(PREFIX)")

#- Print startup message
echo "========================================"
echo "KREIOS-150 IOC Started"
echo "PREFIX: $(PREFIX)"
echo "PORT: $(PORT)"
echo "Prodigy Server: $(PRODIGY_HOST):$(PRODIGY_PORT)"
echo "========================================"

#- Start any sequence programs here
#seq &sequencer, "P=$(PREFIX)"
