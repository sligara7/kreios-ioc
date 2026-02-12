#!/bin/bash
#
# Build EPICS Stack for KREIOS-150 IOC (Native Deployment)
#
# This script builds the full EPICS stack to /opt/epics, mirroring the exact
# versions from docker/Dockerfile for a native (non-Docker) deployment on
# Ubuntu/Debian systems.
#
# Usage:
#   sudo ./scripts/build_epics_stack.sh
#
# Requirements:
#   - Must be run as root (or with sudo) for /opt/epics installation
#   - Debian/Ubuntu system with apt-get
#   - Internet access for git clones
#
# After running this script, build the KREIOS driver:
#   1. Create configure/RELEASE.local (see bottom of this script)
#   2. make -j$(nproc)

set -euo pipefail

# ============================================================================
# Configuration - versions match docker/Dockerfile exactly
# ============================================================================
EPICS_BASE_VERSION="R7.0.8"
ASYN_VERSION="R4-44-2"
SEQ_VERSION="R2-2-9"
SSCAN_VERSION="R2-11-6"
CALC_VERSION="R3-7-5"
AUTOSAVE_VERSION="R5-11"
IOCSTATS_VERSION="3.2.0"
BUSY_VERSION="R1-7-4"
ADSUPPORT_COMMIT="62b91c1154a74a1fb532d831a6ec029bb311b8f7"
ADCORE_COMMIT="d27d71fb73bd915bdd714c8c4c78c05e3f31b1ce"

EPICS_ROOT="/opt/epics"
EPICS_BASE="${EPICS_ROOT}/base"
SUPPORT="${EPICS_ROOT}/support"
EPICS_HOST_ARCH="linux-x86_64"
NPROC=$(nproc)

# ============================================================================
# Preflight checks
# ============================================================================
if [[ $EUID -ne 0 ]]; then
    echo "ERROR: This script must be run as root (sudo $0)"
    exit 1
fi

echo "============================================"
echo "KREIOS-150 EPICS Stack Builder"
echo "============================================"
echo "EPICS_ROOT:    ${EPICS_ROOT}"
echo "Parallel jobs: ${NPROC}"
echo "============================================"

# ============================================================================
# Install system dependencies
# ============================================================================
echo ""
echo "[1/12] Installing system dependencies..."
apt-get update
apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    git \
    libreadline-dev \
    libxml2-dev \
    libtiff-dev \
    libjpeg-dev \
    libz-dev \
    libhdf5-dev \
    libnetcdf-dev \
    libsz2 \
    libtirpc-dev \
    re2c \
    procserv

echo "System dependencies installed."

# ============================================================================
# Create EPICS directory structure
# ============================================================================
mkdir -p "${EPICS_ROOT}"
mkdir -p "${SUPPORT}"

# ============================================================================
# Build EPICS Base
# ============================================================================
if [[ -f "${EPICS_BASE}/bin/${EPICS_HOST_ARCH}/caget" ]]; then
    echo ""
    echo "[2/12] EPICS Base already built, skipping."
else
    echo ""
    echo "[2/12] Building EPICS Base ${EPICS_BASE_VERSION}..."
    cd "${EPICS_ROOT}"
    if [[ ! -d base ]]; then
        git clone --branch "${EPICS_BASE_VERSION}" --depth 1 \
            https://github.com/epics-base/epics-base.git base
    fi
    cd base
    make -j${NPROC}
    echo "EPICS Base built successfully."
fi

export PATH="${EPICS_BASE}/bin/${EPICS_HOST_ARCH}:${PATH}"

# ============================================================================
# Build asyn
# ============================================================================
if [[ -f "${SUPPORT}/asyn/lib/${EPICS_HOST_ARCH}/libasyn.so" ]]; then
    echo ""
    echo "[3/12] asyn already built, skipping."
else
    echo ""
    echo "[3/12] Building asyn ${ASYN_VERSION}..."
    cd "${SUPPORT}"
    if [[ ! -d asyn ]]; then
        git clone --branch "${ASYN_VERSION}" --depth 1 \
            https://github.com/epics-modules/asyn.git
    fi
    cd asyn
    echo "EPICS_BASE=${EPICS_BASE}" > configure/RELEASE.local
    echo "TIRPC=YES" >> configure/CONFIG_SITE.local
    make -j${NPROC}
    echo "asyn built successfully."
fi

# ============================================================================
# Build sequencer (SNCSEQ)
# ============================================================================
if [[ -f "${SUPPORT}/seq/lib/${EPICS_HOST_ARCH}/libseq.so" ]]; then
    echo ""
    echo "[4/12] sequencer already built, skipping."
else
    echo ""
    echo "[4/12] Building sequencer ${SEQ_VERSION}..."
    cd "${SUPPORT}"
    if [[ ! -d seq ]]; then
        git clone --branch "${SEQ_VERSION}" --depth 1 \
            https://github.com/epics-modules/sequencer.git seq
    fi
    cd seq
    echo "EPICS_BASE=${EPICS_BASE}" > configure/RELEASE.local
    make -j${NPROC}
    echo "sequencer built successfully."
fi

# ============================================================================
# Build sscan
# ============================================================================
if [[ -f "${SUPPORT}/sscan/lib/${EPICS_HOST_ARCH}/libsscan.so" ]]; then
    echo ""
    echo "[5/12] sscan already built, skipping."
else
    echo ""
    echo "[5/12] Building sscan ${SSCAN_VERSION}..."
    cd "${SUPPORT}"
    if [[ ! -d sscan ]]; then
        git clone --branch "${SSCAN_VERSION}" --depth 1 \
            https://github.com/epics-modules/sscan.git
    fi
    cd sscan
    cat > configure/RELEASE.local <<EOF
EPICS_BASE=${EPICS_BASE}
SUPPORT=${SUPPORT}
SNCSEQ=${SUPPORT}/seq
EOF
    make -j${NPROC}
    echo "sscan built successfully."
fi

# ============================================================================
# Build calc
# ============================================================================
if [[ -f "${SUPPORT}/calc/lib/${EPICS_HOST_ARCH}/libcalc.so" ]]; then
    echo ""
    echo "[6/12] calc already built, skipping."
else
    echo ""
    echo "[6/12] Building calc ${CALC_VERSION}..."
    cd "${SUPPORT}"
    if [[ ! -d calc ]]; then
        git clone --branch "${CALC_VERSION}" --depth 1 \
            https://github.com/epics-modules/calc.git
    fi
    cd calc
    cat > configure/RELEASE.local <<EOF
EPICS_BASE=${EPICS_BASE}
SUPPORT=${SUPPORT}
SSCAN=${SUPPORT}/sscan
SNCSEQ=${SUPPORT}/seq
EOF
    make -j${NPROC}
    echo "calc built successfully."
fi

# ============================================================================
# Build autosave
# ============================================================================
if [[ -f "${SUPPORT}/autosave/lib/${EPICS_HOST_ARCH}/libautosave.so" ]]; then
    echo ""
    echo "[7/12] autosave already built, skipping."
else
    echo ""
    echo "[7/12] Building autosave ${AUTOSAVE_VERSION}..."
    cd "${SUPPORT}"
    if [[ ! -d autosave ]]; then
        git clone --branch "${AUTOSAVE_VERSION}" --depth 1 \
            https://github.com/epics-modules/autosave.git
    fi
    cd autosave
    echo "EPICS_BASE=${EPICS_BASE}" > configure/RELEASE.local
    make -j${NPROC}
    echo "autosave built successfully."
fi

# ============================================================================
# Build iocStats (devIocStats)
# ============================================================================
if [[ -f "${SUPPORT}/iocStats/lib/${EPICS_HOST_ARCH}/libdevIocStats.so" ]]; then
    echo ""
    echo "[8/12] iocStats already built, skipping."
else
    echo ""
    echo "[8/12] Building iocStats ${IOCSTATS_VERSION}..."
    cd "${SUPPORT}"
    if [[ ! -d iocStats ]]; then
        git clone --branch "${IOCSTATS_VERSION}" --depth 1 \
            https://github.com/epics-modules/iocStats.git
    fi
    cd iocStats
    echo "EPICS_BASE=${EPICS_BASE}" > configure/RELEASE.local
    make -j${NPROC}
    echo "iocStats built successfully."
fi

# ============================================================================
# Build busy
# ============================================================================
if [[ -f "${SUPPORT}/busy/lib/${EPICS_HOST_ARCH}/libbusy.so" ]]; then
    echo ""
    echo "[9/12] busy already built, skipping."
else
    echo ""
    echo "[9/12] Building busy ${BUSY_VERSION}..."
    cd "${SUPPORT}"
    if [[ ! -d busy ]]; then
        git clone --branch "${BUSY_VERSION}" --depth 1 \
            https://github.com/epics-modules/busy.git
    fi
    cd busy
    cat > configure/RELEASE.local <<EOF
EPICS_BASE=${EPICS_BASE}
SUPPORT=${SUPPORT}
BUSY=${SUPPORT}/busy
ASYN=${SUPPORT}/asyn
EOF
    # Remove test app that causes build issues
    sed -i '/testBusyAsyn/d' busyApp/src/Makefile
    make -j${NPROC}
    echo "busy built successfully."
fi

# ============================================================================
# Build ADSupport
# ============================================================================
if [[ -f "${SUPPORT}/ADSupport/lib/${EPICS_HOST_ARCH}/libxml2Src.so" ]]; then
    echo ""
    echo "[10/12] ADSupport already built, skipping."
else
    echo ""
    echo "[10/12] Building ADSupport (commit ${ADSUPPORT_COMMIT:0:8})..."
    cd "${SUPPORT}"
    if [[ ! -d ADSupport ]]; then
        git clone https://github.com/areaDetector/ADSupport.git
        cd ADSupport
        git checkout "${ADSUPPORT_COMMIT}"
    else
        cd ADSupport
    fi

    echo "EPICS_BASE=${EPICS_BASE}" > configure/RELEASE.local
    echo "SUPPORT=${SUPPORT}" >> configure/RELEASE.local

    # Ensure CONFIG_SITE includes local overrides
    if ! grep -q 'CONFIG_SITE.local' configure/CONFIG_SITE; then
        echo "" >> configure/CONFIG_SITE
        echo "# Include local site configuration" >> configure/CONFIG_SITE
        echo '-include $(TOP)/configure/CONFIG_SITE.local' >> configure/CONFIG_SITE
    fi

    # Use system libraries (same config as Dockerfile)
    cat > configure/CONFIG_SITE.local <<EOF
WITH_BOOST=NO
WITH_BLOSC=NO
WITH_BITSHUFFLE=NO
WITH_XML2=YES
XML2_EXTERNAL=YES
XML2_INCLUDE=/usr/include/libxml2
XML2_LIB=/usr/lib/x86_64-linux-gnu
HDF5_EXTERNAL=YES
HDF5_INCLUDE=/usr/include/hdf5/serial
HDF5_LIB=/usr/lib/x86_64-linux-gnu/hdf5/serial
NETCDF_EXTERNAL=YES
NETCDF_INCLUDE=/usr/include
NETCDF_LIB=/usr/lib/x86_64-linux-gnu
SZIP_EXTERNAL=YES
SZIP_INCLUDE=/usr/include
SZIP_LIB=/usr/lib/x86_64-linux-gnu
ZLIB_EXTERNAL=YES
ZLIB_INCLUDE=/usr/include
ZLIB_LIB=/usr/lib/x86_64-linux-gnu
JPEG_EXTERNAL=YES
JPEG_INCLUDE=/usr/include
JPEG_LIB=/usr/lib/x86_64-linux-gnu
TIFF_EXTERNAL=YES
TIFF_INCLUDE=/usr/include /usr/include/x86_64-linux-gnu
TIFF_LIB=/usr/lib/x86_64-linux-gnu
EOF
    make -j${NPROC}
    echo "ADSupport built successfully."
fi

# ============================================================================
# Build ADCore
# ============================================================================
if [[ -f "${SUPPORT}/ADCore/lib/${EPICS_HOST_ARCH}/libADBase.so" ]]; then
    echo ""
    echo "[11/12] ADCore already built, skipping."
else
    echo ""
    echo "[11/12] Building ADCore (commit ${ADCORE_COMMIT:0:8})..."
    cd "${SUPPORT}"
    if [[ ! -d ADCore ]]; then
        git clone https://github.com/areaDetector/ADCore.git
        cd ADCore
        git checkout "${ADCORE_COMMIT}"
    else
        cd ADCore
    fi

    cat > configure/RELEASE.local <<EOF
EPICS_BASE=${EPICS_BASE}
SUPPORT=${SUPPORT}
ASYN=${SUPPORT}/asyn
BUSY=${SUPPORT}/busy
CALC=${SUPPORT}/calc
SSCAN=${SUPPORT}/sscan
SNCSEQ=${SUPPORT}/seq
AUTOSAVE=${SUPPORT}/autosave
DEVIOCSTATS=${SUPPORT}/iocStats
ADSUPPORT=${SUPPORT}/ADSupport
EOF

    # Ensure CONFIG_SITE includes local overrides
    if ! grep -q 'CONFIG_SITE.local' configure/CONFIG_SITE; then
        echo "" >> configure/CONFIG_SITE
        echo "# Include local site configuration" >> configure/CONFIG_SITE
        echo '-include $(TOP)/configure/CONFIG_SITE.local' >> configure/CONFIG_SITE
    fi

    # Use system libraries (same config as Dockerfile)
    cat > configure/CONFIG_SITE.local <<EOF
WITH_BOOST=NO
WITH_GRAPHICSMAGICK=NO
WITH_HDF5=YES
WITH_NETCDF=YES
WITH_NEXUS=NO
WITH_TIFF=YES
WITH_JPEG=YES
WITH_SZIP=YES
WITH_ZLIB=YES
WITH_XML2=YES
XML2_EXTERNAL=YES
XML2_INCLUDE=/usr/include/libxml2
XML2_LIB=/usr/lib/x86_64-linux-gnu
HDF5_EXTERNAL=YES
HDF5_INCLUDE=/usr/include/hdf5/serial
HDF5_LIB=/usr/lib/x86_64-linux-gnu/hdf5/serial
NETCDF_EXTERNAL=YES
NETCDF_INCLUDE=/usr/include
NETCDF_LIB=/usr/lib/x86_64-linux-gnu
SZIP_EXTERNAL=YES
SZIP_INCLUDE=/usr/include
SZIP_LIB=/usr/lib/x86_64-linux-gnu
ZLIB_EXTERNAL=YES
ZLIB_INCLUDE=/usr/include
ZLIB_LIB=/usr/lib/x86_64-linux-gnu
JPEG_EXTERNAL=YES
JPEG_INCLUDE=/usr/include
JPEG_LIB=/usr/lib/x86_64-linux-gnu
TIFF_EXTERNAL=YES
TIFF_INCLUDE=/usr/include /usr/include/x86_64-linux-gnu
TIFF_LIB=/usr/lib/x86_64-linux-gnu
EOF

    # Skip building iocBoot example IOCs
    sed -i '/iocBoot/d' Makefile

    # ADCore make may return non-zero even when libraries build successfully
    # due to parallel job issues, so we verify essential libraries exist
    (make -j${NPROC} || true)
    if [[ ! -f "lib/${EPICS_HOST_ARCH}/libADBase.so" ]] || \
       [[ ! -f "lib/${EPICS_HOST_ARCH}/libNDPlugin.so" ]]; then
        echo "ERROR: ADCore build failed - essential libraries not found"
        exit 1
    fi
    echo "ADCore built successfully."
fi

# ============================================================================
# Copy EXAMPLE commonPlugins files (required for commonPlugins.cmd)
# ============================================================================
echo ""
echo "[12/12] Setting up commonPlugins files..."
cd "${SUPPORT}/ADCore/iocBoot"
if [[ ! -f commonPlugins.cmd ]]; then
    cp EXAMPLE_commonPlugins.cmd commonPlugins.cmd
fi
if [[ ! -f commonPlugin_settings.req ]]; then
    cp EXAMPLE_commonPlugin_settings.req commonPlugin_settings.req
fi
echo "commonPlugins files ready."

# ============================================================================
# Set ownership so the build user can compile the KREIOS driver
# ============================================================================
REAL_USER="${SUDO_USER:-$(whoami)}"
if [[ "${REAL_USER}" != "root" ]]; then
    echo ""
    echo "Setting ownership of ${EPICS_ROOT} to ${REAL_USER}..."
    chown -R "${REAL_USER}:${REAL_USER}" "${EPICS_ROOT}"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "============================================"
echo "EPICS stack build complete!"
echo "============================================"
echo ""
echo "Installed to: ${EPICS_ROOT}"
echo "  base:       ${EPICS_BASE}"
echo "  asyn:       ${SUPPORT}/asyn"
echo "  seq:        ${SUPPORT}/seq"
echo "  sscan:      ${SUPPORT}/sscan"
echo "  calc:       ${SUPPORT}/calc"
echo "  autosave:   ${SUPPORT}/autosave"
echo "  iocStats:   ${SUPPORT}/iocStats"
echo "  busy:       ${SUPPORT}/busy"
echo "  ADSupport:  ${SUPPORT}/ADSupport"
echo "  ADCore:     ${SUPPORT}/ADCore"
echo ""
echo "Next steps:"
echo "  1. Build the KREIOS driver:"
echo "     cd $(dirname "$(readlink -f "$0")")/.."
echo "     make -j\$(nproc)"
echo ""
echo "  2. The RELEASE.local file will be created automatically"
echo "     at configure/RELEASE.local pointing to ${EPICS_ROOT}"
echo ""

# ============================================================================
# Create RELEASE.local for the KREIOS driver build
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KREIOS_TOP="$(cd "${SCRIPT_DIR}/.." && pwd)"

cat > "${KREIOS_TOP}/configure/RELEASE.local" <<EOF
# Auto-generated by build_epics_stack.sh
# Points to native EPICS stack at ${EPICS_ROOT}

EPICS_BASE=${EPICS_BASE}
SUPPORT=${SUPPORT}
ASYN=${SUPPORT}/asyn
SNCSEQ=${SUPPORT}/seq
SSCAN=${SUPPORT}/sscan
CALC=${SUPPORT}/calc
AUTOSAVE=${SUPPORT}/autosave
DEVIOCSTATS=${SUPPORT}/iocStats
BUSY=${SUPPORT}/busy
AREA_DETECTOR=${SUPPORT}
ADCORE=${SUPPORT}/ADCore
ADSUPPORT=${SUPPORT}/ADSupport
EOF

echo "Created ${KREIOS_TOP}/configure/RELEASE.local"
echo ""
echo "Build the KREIOS driver with: make -j\$(nproc)"
