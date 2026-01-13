areaDetector Module Structure:

  kreios-ioc/
  ├── Makefile                     # Top-level build
  ├── configure/
  │   ├── CONFIG                   # Build config
  │   ├── CONFIG_SITE              # Site-specific config
  │   ├── RELEASE                  # EPICS path definitions (edit this)
  │   ├── RULES                    # Build rules
  │   ├── RULES_DIRS               # Directory rules
  │   └── RULES_TOP                # Top-level rules
  ├── kreiosApp/
  │   ├── Makefile
  │   ├── README.md                # Driver documentation
  │   ├── Db/
  │   │   ├── kreios.template      # EPICS database (includes ADBase.template)
  │   │   └── Makefile
  │   └── src/
  │       ├── kreios.h             # Driver header
  │       ├── kreios.cpp           # Driver implementation (~1900 lines)
  │       ├── kreiosSupport.dbd    # DBD registration
  │       └── Makefile
  ├── iocBoot/
  │   ├── Makefile
  │   └── iocKreios/
  │       ├── st.cmd               # IOC startup script
  │       ├── envPaths             # Environment paths (auto-generated)
  │       └── Makefile
  └── scripts/
      ├── start_simulator.sh       # Start Prodigy simulator
      └── test_connection.py       # Test protocol connectivity

  Key Features:
  - Protocol version: Prodigy Remote In v1.22 (September 2024)
  - Data dimensionality: 1D, 2D, and 3D support
  - Run modes: FAT, SFAT, FRR, FE, LVS
  - Operating modes: Spectroscopy, Momentum, PEEM
  - Extends ADDriver with KREIOS-specific parameters

  To test with simulator:
  # Terminal 1: Start simulator
  cd sim && python3 ProdigySimServer.py

  # Terminal 2: Test connection
  python3 scripts/test_connection.py localhost 7010
  
    kreios-ioc/
  ├── Makefile                          # Top-level build
  ├── configure/                        # EPICS build configuration
  │   ├── CONFIG, CONFIG_SITE, RELEASE
  │   └── RULES, RULES_DIRS, RULES_TOP
  ├── kreiosApp/                        # C++ areaDetector driver
  │   ├── src/
  │   │   ├── kreios.h                  # Driver header
  │   │   ├── kreios.cpp                # Driver implementation
  │   │   ├── kreiosSupport.dbd
  │   │   └── Makefile
  │   ├── Db/
  │   │   ├── kreios.template           # EPICS database
  │   │   └── Makefile
  │   └── README.md
  ├── iocBoot/iocKreios/                # IOC startup
  │   ├── st.cmd
  │   └── Makefile
  ├── sim/                              # Prodigy protocol simulator
  │   ├── ProdigySimServer.py
  │   ├── test_client.py
  │   ├── parameters.dat
  │   └── *.md (documentation)
  ├── scripts/                          # Utility scripts
  │   ├── start_simulator.sh
  │   └── test_connection.py
  ├── tests/                            # Test suite
  │   ├── conftest.py
  │   └── test_*.py
  ├── Documentation/                    # Protocol docs
  │   ├── SpecsLab_Prodigy_RemoteIn.md
  │   └── SpecsLabProdigy_RemoteIn.pdf
  └── pytest.ini




