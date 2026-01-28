# Makefile at top of KREIOS-150 areaDetector module tree
#
# KREIOS-150 Momentum Microscope areaDetector Driver
# Interfaces with SPECS KREIOS-150 via SpecsLab Prodigy Remote In protocol
#
# Data dimensionality support:
#   1D - Integrated spectrum (energy axis only)
#   2D - Image (energy x detector pixels)
#   3D - Volume (slices x energy x pixels)

TOP = .
include $(TOP)/configure/CONFIG

DIRS := $(DIRS) $(filter-out $(DIRS), configure)
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard *App))
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard iocBoot))

define DIR_template
 $(1)_DEPEND_DIRS = configure
endef
$(foreach dir, $(filter-out configure,$(DIRS)),$(eval $(call DIR_template,$(dir))))

iocApp_DEPEND_DIRS += kreiosApp
iocBoot_DEPEND_DIRS += $(filter-out iocBoot,$(DIRS))

include $(TOP)/configure/RULES_TOP
