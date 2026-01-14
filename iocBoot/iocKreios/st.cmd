#!/bin/bash
#!../../bin/linux-x86_64/kreiosIOC

#- KREIOS-150 Momentum Microscope IOC Startup Script
#-
#- This IOC interfaces with the SPECS KREIOS-150 momentum microscope
#- via the SpecsLab Prodigy Remote In protocol.
#-
#- Data dimensionality support:
#-   1D - Integrated spectrum (energy axis only)
#-   2D - Image (energy x detector pixels)
#-   3D - Volume (slices x energy x pixels)

< envPaths

#- Environment Variables
epicsEnvSet("PREFIX", "KREIOS:")
epicsEnvSet("PORT", "KREIOS1")
epicsEnvSet("QSIZE", "20")
epicsEnvSet("XSIZE", "1285")
epicsEnvSet("YSIZE", "730")
epicsEnvSet("NCHANS", "100000")
epicsEnvSet("CBUFFS", "500")
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
dbLoadDatabase "dbd/kreiosIOC.dbd"
kreiosIOC_registerRecordDeviceDriver pdbbase

#- Create asyn port for Prodigy communication
drvAsynIPPortConfigure("PRODIGY", "$(PRODIGY_HOST):$(PRODIGY_PORT)", 0, 0, 0)

#- Optional: set asyn trace for debugging
#asynSetTraceIOMask("PRODIGY", 0, 2)
#asynSetTraceMask("PRODIGY", 0, 9)

#- Create the KREIOS driver
#- kreiosConfig(portName, driverPort, maxBuffers, maxMemory, priority, stackSize)
kreiosConfig("$(PORT)", "PRODIGY", 0, 0, 0, 0)

#- Load KREIOS database
dbLoadRecords("$(KREIOS)/db/kreios.template", "P=$(PREFIX),R=cam1:,PORT=$(PORT),ADDR=0,TIMEOUT=1")

#- Load standard areaDetector databases
dbLoadRecords("$(ADCORE)/db/NDFile.template", "P=$(PREFIX),R=cam1:,PORT=$(PORT),ADDR=0,TIMEOUT=1")

#- Optionally load HDF5 plugin for data saving
#NDFileHDF5Configure("FileHDF1", "$(QSIZE)", 0, "$(PORT)", 0, 0, 0)
#dbLoadRecords("$(ADCORE)/db/NDFileHDF5.template", "P=$(PREFIX),R=HDF1:,PORT=FileHDF1,ADDR=0,TIMEOUT=1,NDARRAY_PORT=$(PORT)")

#- Optionally load image plugin for live display
#NDStdArraysConfigure("Image1", "$(QSIZE)", 0, "$(PORT)", 0, 0, 0)
#dbLoadRecords("$(ADCORE)/db/NDStdArrays.template", "P=$(PREFIX),R=image1:,PORT=Image1,ADDR=0,TIMEOUT=1,NDARRAY_PORT=$(PORT),TYPE=Float64,FTVL=DOUBLE,NELEMENTS=$(NCHANS)")

#- Optionally load stats plugin
#NDStatsConfigure("Stats1", "$(QSIZE)", 0, "$(PORT)", 0, 0, 0)
#dbLoadRecords("$(ADCORE)/db/NDStats.template", "P=$(PREFIX),R=Stats1:,PORT=Stats1,ADDR=0,TIMEOUT=1,NDARRAY_PORT=$(PORT)")

#- Set array size for image plugin if used
#dbLoadRecords("$(ADCORE)/db/NDArrayBase.template", "P=$(PREFIX),R=cam1:,PORT=$(PORT),ADDR=0,TIMEOUT=1")

#- Initialize IOC
cd "${TOP}/iocBoot/${IOC}"
iocInit

#- Print startup message
echo "========================================"
echo "KREIOS-150 IOC Started"
echo "PREFIX: $(PREFIX)"
echo "PORT: $(PORT)"
echo "Prodigy Server: $(PRODIGY_HOST):$(PRODIGY_PORT)"
echo "========================================"

#- Optional: start autosave
#create_monitor_set("auto_settings.req", 30, "P=$(PREFIX)")

#- Start any sequence programs here
#seq &sequencer, "P=$(PREFIX)"
