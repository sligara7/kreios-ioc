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
kreios_DBD += asyn.dbd
kreios_DBD += ADSupport.dbd
kreios_DBD += NDPluginSupport.dbd
kreios_DBD += kreiosSupport.dbd

# Add all the support libraries needed by this IOC
kreios_LIBS += kreios
kreios_LIBS += NDPlugin ADBase
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
