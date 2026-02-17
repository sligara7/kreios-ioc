# Makefile at top of ADKreios areaDetector module tree
#
# ADKreios - KREIOS-150 Momentum Microscope areaDetector Driver
# Interfaces with SPECS KREIOS-150 via SpecsLab Prodigy Remote In protocol

TOP = .
include $(TOP)/configure/CONFIG

DIRS := $(DIRS) $(filter-out $(DIRS), configure)
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard *App))
DIRS := $(DIRS) $(filter-out $(DIRS), $(wildcard iocs))

define DIR_template
 $(1)_DEPEND_DIRS = configure
endef
$(foreach dir, $(filter-out configure,$(DIRS)),$(eval $(call DIR_template,$(dir))))

iocs_DEPEND_DIRS += kreiosApp

include $(TOP)/configure/RULES_TOP
