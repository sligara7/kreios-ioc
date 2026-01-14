# KREIOS-150 areaDetector IOC Docker Image
#
# Builds EPICS base, asyn, areaDetector, and the KREIOS driver
# in a multi-stage build for a smaller final image.
#
# Usage:
#   docker build -t kreios-ioc -f docker/Dockerfile .
#   docker run -it --rm -p 5064:5064 -p 5065:5065 kreios-ioc
#
# Build args:
#   EPICS_BASE_VERSION - EPICS base version (default: R7.0.8)
#   ASYN_VERSION - asyn version (default: R4-44-2)
#   ADCORE_VERSION - ADCore version (default: R3-12-1)
#   ADSUPPORT_VERSION - ADSupport version (default: R1-10)

FROM debian:bookworm-slim AS builder

# Build arguments for version control
ARG EPICS_BASE_VERSION=R7.0.8
ARG ASYN_VERSION=R4-44-2
ARG ADCORE_VERSION=R3-12-1
ARG ADSUPPORT_VERSION=R1-10

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    && rm -rf /var/lib/apt/lists/*

# Set up EPICS environment
ENV EPICS_ROOT=/opt/epics
ENV EPICS_BASE=${EPICS_ROOT}/base
ENV EPICS_HOST_ARCH=linux-x86_64
ENV PATH=${EPICS_BASE}/bin/${EPICS_HOST_ARCH}:${PATH}

# ============================================================================
# Build EPICS Base
# ============================================================================
WORKDIR ${EPICS_ROOT}

RUN git clone --branch ${EPICS_BASE_VERSION} --depth 1 \
    https://github.com/epics-base/epics-base.git base \
    && cd base \
    && make -j$(nproc)

# ============================================================================
# Build asyn
# ============================================================================
WORKDIR ${EPICS_ROOT}/support

RUN git clone --branch ${ASYN_VERSION} --depth 1 \
    https://github.com/epics-modules/asyn.git \
    && cd asyn \
    && echo "EPICS_BASE=${EPICS_BASE}" > configure/RELEASE.local \
    && echo "TIRPC=YES" >> configure/CONFIG_SITE.local \
    && make -j$(nproc)

# ============================================================================
# Build areaDetector ADSupport
# ============================================================================
RUN git clone --branch ${ADSUPPORT_VERSION} --depth 1 \
    https://github.com/areaDetector/ADSupport.git \
    && cd ADSupport \
    && echo "EPICS_BASE=${EPICS_BASE}" > configure/RELEASE.local \
    && echo "SUPPORT=${EPICS_ROOT}/support" >> configure/RELEASE.local \
    && echo "WITH_BOOST=NO" > configure/CONFIG_SITE.local \
    && echo "WITH_BLOSC=NO" >> configure/CONFIG_SITE.local \
    && echo "WITH_BITSHUFFLE=NO" >> configure/CONFIG_SITE.local \
    && echo "WITH_XML2=NO" >> configure/CONFIG_SITE.local \
    && echo "ZLIB_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && echo "JPEG_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && echo "TIFF_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && echo "HDF5_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && echo "SZIP_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && echo "NETCDF_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && make -j$(nproc)

# ============================================================================
# Build areaDetector ADCore
# ============================================================================
RUN git clone --branch ${ADCORE_VERSION} --depth 1 \
    https://github.com/areaDetector/ADCore.git \
    && cd ADCore \
    && echo "EPICS_BASE=${EPICS_BASE}" > configure/RELEASE.local \
    && echo "SUPPORT=${EPICS_ROOT}/support" >> configure/RELEASE.local \
    && echo "ASYN=${EPICS_ROOT}/support/asyn" >> configure/RELEASE.local \
    && echo "ADSUPPORT=${EPICS_ROOT}/support/ADSupport" >> configure/RELEASE.local \
    && echo "WITH_BOOST=NO" > configure/CONFIG_SITE.local \
    && echo "WITH_GRAPHICSMAGICK=NO" >> configure/CONFIG_SITE.local \
    && echo "WITH_HDF5=YES" >> configure/CONFIG_SITE.local \
    && echo "WITH_NETCDF=YES" >> configure/CONFIG_SITE.local \
    && echo "WITH_NEXUS=NO" >> configure/CONFIG_SITE.local \
    && echo "WITH_TIFF=YES" >> configure/CONFIG_SITE.local \
    && echo "WITH_JPEG=YES" >> configure/CONFIG_SITE.local \
    && echo "WITH_SZIP=YES" >> configure/CONFIG_SITE.local \
    && echo "WITH_ZLIB=YES" >> configure/CONFIG_SITE.local \
    && echo "WITH_XML2=NO" >> configure/CONFIG_SITE.local \
    && echo "HDF5_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && echo "NETCDF_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && echo "SZIP_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && echo "ZLIB_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && echo "JPEG_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && echo "TIFF_EXTERNAL=YES" >> configure/CONFIG_SITE.local \
    && make -j$(nproc)

# ============================================================================
# Build KREIOS Driver
# ============================================================================
WORKDIR /build
COPY . /build/kreios-ioc

WORKDIR /build/kreios-ioc

# Create RELEASE.local for Docker build
RUN echo "EPICS_BASE=${EPICS_BASE}" > configure/RELEASE.local \
    && echo "SUPPORT=${EPICS_ROOT}/support" >> configure/RELEASE.local \
    && echo "ASYN=${EPICS_ROOT}/support/asyn" >> configure/RELEASE.local \
    && echo "AREA_DETECTOR=${EPICS_ROOT}/support" >> configure/RELEASE.local \
    && echo "ADCORE=${EPICS_ROOT}/support/ADCore" >> configure/RELEASE.local \
    && echo "ADSUPPORT=${EPICS_ROOT}/support/ADSupport" >> configure/RELEASE.local

RUN make -j$(nproc)

# ============================================================================
# Runtime Image
# ============================================================================
FROM debian:bookworm-slim AS runtime

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreadline8 \
    libxml2 \
    libtiff6 \
    libjpeg62-turbo \
    libhdf5-103-1 \
    libnetcdf19 \
    libsz2 \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set up EPICS environment
ENV EPICS_ROOT=/opt/epics
ENV EPICS_BASE=${EPICS_ROOT}/base
ENV EPICS_HOST_ARCH=linux-x86_64
ENV PATH=${EPICS_BASE}/bin/${EPICS_HOST_ARCH}:${PATH}

# EPICS Channel Access settings
ENV EPICS_CA_ADDR_LIST=localhost
ENV EPICS_CA_AUTO_ADDR_LIST=NO
ENV EPICS_CA_MAX_ARRAY_BYTES=10000000

# Copy built EPICS installation
COPY --from=builder ${EPICS_ROOT} ${EPICS_ROOT}

# Copy KREIOS IOC
COPY --from=builder /build/kreios-ioc /opt/kreios-ioc

# Copy simulator for integrated testing
COPY sim /opt/kreios-ioc/sim
COPY scripts /opt/kreios-ioc/scripts

WORKDIR /opt/kreios-ioc

# Expose EPICS CA ports
EXPOSE 5064/tcp 5064/udp 5065/tcp 5065/udp
# Expose simulator port
EXPOSE 7010/tcp

# Default command: run the IOC
CMD ["sh", "-c", "cd /opt/kreios-ioc/iocBoot/iocKreios && ../../bin/${EPICS_HOST_ARCH}/kreios st.cmd"]
