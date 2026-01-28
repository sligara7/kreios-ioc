TOP=../..

include $(TOP)/configure/CONFIG
#----------------------------------------
#  ADD MACRO DEFINITIONS AFTER THIS LINE
#=============================

#=============================
# Build the IOC application

PROD_IOC = kreios
# kreios.dbd will be created and installed
DBD += kreios.dbd

# kreios.dbd will be made up from these files:
kreios_DBD += base.dbd

# Include dbd files from all support applications:
# asyn - communication layer
kreios_DBD += asyn.dbd
kreios_DBD += drvAsynIPPort.dbd
kreios_DBD += drvAsynSerialPort.dbd

# synApps modules for production IOC
kreios_DBD += calcSupport.dbd
kreios_DBD += sscanSupport.dbd
kreios_DBD += asSupport.dbd
kreios_DBD += devIocStats.dbd
kreios_DBD += busySupport.dbd

# areaDetector
kreios_DBD += ADSupport.dbd
kreios_DBD += NDPluginSupport.dbd

# areaDetector file plugins (required for commonPlugins.cmd)
kreios_DBD += NDFileHDF5.dbd
kreios_DBD += NDFileTIFF.dbd
kreios_DBD += NDFileJPEG.dbd
kreios_DBD += NDFileNetCDF.dbd
# Note: NDFileNexus requires additional dependencies, disabled for now
# kreios_DBD += NDFileNexus.dbd

# KREIOS driver
kreios_DBD += kreiosSupport.dbd

# Add all the support libraries needed by this IOC
# Order matters for linking - dependencies must come after dependents
kreios_LIBS += kreios
kreios_LIBS += NDPlugin ADBase
kreios_LIBS += calc
kreios_LIBS += sscan
kreios_LIBS += autosave
kreios_LIBS += devIocStats
kreios_LIBS += busy
kreios_LIBS += seq
kreios_LIBS += asyn
kreios_LIBS += $(EPICS_BASE_IOC_LIBS)

# kreios_registerRecordDeviceDriver.cpp derives from kreios.dbd
kreios_SRCS += kreios_registerRecordDeviceDriver.cpp

# Build the main IOC entry point on workstation OSs.
kreios_SRCS_DEFAULT += kreiosMain.cpp
kreios_SRCS_vxWorks += -nil-

#===========================

include $(TOP)/configure/RULES
#----------------------------------------
#  ADD RULES AFTER THIS LINE
