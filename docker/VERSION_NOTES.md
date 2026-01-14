# areaDetector Version Selection Notes

## Version Compatibility Matrix

| Component | Version/Tag | Commit Hash | Notes |
|-----------|-------------|-------------|-------|
| EPICS Base | R7.0.8 | (uses tag) | Stable release |
| asyn | R4-44-2 | (uses tag) | Latest stable |
| ADCore | R3-14 (meta-repo) | d27d71fb | From areaDetector R3-14 submodule |
| ADSupport | N/A | 62b91c11 | From areaDetector R3-14 submodule |

**Important:** We use specific commit hashes from the areaDetector meta-repository,
NOT the R3-14 tags from individual component repositories. See "Why We Use Commit
Hashes Instead of Tags" section below for details.

## ADSupport Version Selection Explained

### The Problem: Different Versioning Schemes

ADCore and ADSupport use **different version numbering schemes**:
- **ADCore**: R3-x series (e.g., R3-12-1, R3-13, R3-14)
- **ADSupport**: R1-x series (e.g., R1-9, R1-10)

This creates confusion when trying to find compatible versions.

### The areaDetector Meta-Repository Solution

The main [areaDetector repository](https://github.com/areaDetector/areaDetector) is a
meta-repository that uses git submodules to coordinate compatible versions of all
areaDetector components.

When the areaDetector project releases version R3-14, the meta-repository tag specifies
the exact commit hash for each submodule (ADCore, ADSupport, etc.) that are known to
work together.

### How We Determined the Correct Versions

The areaDetector meta-repository coordinates all component versions. Here's how we
determined the correct versions for our build:

1. Cloned the areaDetector meta-repository:
   ```bash
   git clone https://github.com/areaDetector/areaDetector.git
   cd areaDetector
   ```

2. Checked available releases to find the latest stable version:
   ```bash
   git tag | grep -E "^R3" | sort -V | tail -5
   # Shows: R3-10, R3-11, R3-12-1, R3-13, R3-14
   ```

3. Checked out the desired release (R3-14 being the latest):
   ```bash
   git checkout R3-14
   ```

4. Identified the **ADCore** commit for R3-14:
   ```bash
   git ls-tree R3-14 ADCore
   # Output: 160000 commit <hash>	ADCore
   ```

   Since ADCore has a matching R3-14 tag, we can use the tag directly in the Dockerfile.

5. Identified the **ADSupport** commit for R3-14:
   ```bash
   git ls-tree R3-14 ADSupport
   # Output: 160000 commit 62b91c1154a74a1fb532d831a6ec029bb311b8f7	ADSupport
   ```

6. These exact commits are what were tested together and are guaranteed to be compatible.

### Why We Use Commit Hashes Instead of Tags

In the Dockerfile, we use specific commit hashes for both ADCore and ADSupport:

```dockerfile
# ADSupport
RUN git clone https://github.com/areaDetector/ADSupport.git \
    && cd ADSupport \
    && git checkout 62b91c1154a74a1fb532d831a6ec029bb311b8f7

# ADCore
RUN git clone https://github.com/areaDetector/ADCore.git \
    && cd ADCore \
    && git checkout d27d71fb73bd915bdd714c8c4c78c05e3f31b1ce
```

**Critical Issue: Tag Mismatch Between Repositories**

We discovered that the R3-14 tags in individual component repositories **do not match**
the commits specified by the areaDetector meta-repository:

| Component | Individual Repo R3-14 Tag | Meta-Repo R3-14 Submodule | Match? |
|-----------|---------------------------|---------------------------|--------|
| ADCore | 908cdb7a | d27d71fb | ❌ NO |
| ADSupport | N/A (uses R1-x tags) | 62b91c11 | N/A |

**Why This Matters:**

1. The ADCore R3-14 tag (908cdb7a) still contains the XML2 dependency issue
2. The meta-repository submodule commit (d27d71fb) has the XML2 fix applied
3. Using `git clone --branch R3-14` gives you the wrong code!

**Why We Must Use Commit Hashes:**

1. **ADSupport**: Doesn't have R3-x tags (only R1-x versioning)
2. **ADCore**: The R3-14 tag points to a different commit than the meta-repo specifies
3. **Compatibility**: Only the meta-repo commits are tested together
4. **Reproducibility**: Exact commits ensure consistent builds

## How to Update Versions in the Future

### Updating to a New ADCore Release

When a new ADCore version is released (e.g., R3-15):

1. Check the areaDetector meta-repository for the new release:
   ```bash
   cd /path/to/areaDetector
   git fetch --tags
   git checkout R3-15  # or whatever the new version is
   ```

2. Get the compatible ADSupport commit:
   ```bash
   git ls-tree R3-15 ADSupport
   ```

3. Update the Dockerfile with:
   - New `ADCORE_VERSION` (e.g., R3-15)
   - New ADSupport commit hash from step 2

4. Optionally check ADCore release notes for any other dependency changes:
   ```bash
   git log R3-14..R3-15 --oneline
   ```

### Verifying Version Compatibility

Before updating, check:
- [ADCore releases](https://github.com/areaDetector/ADCore/releases)
- [ADSupport releases](https://github.com/areaDetector/ADSupport/releases)
- [areaDetector meta-repo releases](https://github.com/areaDetector/areaDetector/releases)

## Why We Upgraded from R3-12-1 to R3-14

### Issue with R3-12-1
The original build used ADCore R3-12-1 (June 2023) which had XML2 dependency issues:
- `asynNDArrayDriver.cpp` included `libxml/parser.h`
- This caused build failures with `WITH_XML2=NO` flag
- Multiple workarounds were attempted (include paths, Makefile edits) but all failed

### XML2 Dependency in R3-14
**Important Discovery**: Even after upgrading to R3-14, the `libxml/parser.h` include still exists
in `asynNDArrayDriver.cpp` at commit d27d71fb (the commit specified by areaDetector R3-14 meta-repo).

**Solution**: Instead of fighting the XML2 dependency, we enable XML2 support:
- Set `WITH_XML2=YES` in both ADSupport and ADCore
- Set `XML2_EXTERNAL=YES` to use the system libxml2
- The Dockerfile already installs `libxml2-dev`, so this is straightforward
- This is a pragmatic solution that avoids build issues while keeping dependencies clear

## References

- areaDetector Documentation: https://areadetector.github.io/
- ADCore Releases: https://github.com/areaDetector/ADCore/releases
- ADSupport Releases: https://github.com/areaDetector/ADSupport/releases
- EPICS Base: https://epics-controls.org/

## Build Configuration Requirements

### External Library Path Configuration

areaDetector requires explicit paths to external libraries when building in Docker. The EPICS
build system needs both `<LIB>_INCLUDE` and `<LIB>_LIB` variables defined for each external library.

**Critical Configuration Issue:**

ADSupport and ADCore do NOT include `CONFIG_SITE.local` by default. You must add this include
to their `configure/CONFIG_SITE` files:

```dockerfile
# Add to both ADSupport and ADCore configure/CONFIG_SITE
RUN echo "" >> configure/CONFIG_SITE \
    && echo "# Include local site configuration" >> configure/CONFIG_SITE \
    && echo "-include \$(TOP)/configure/CONFIG_SITE.local" >> configure/CONFIG_SITE
```

**Required External Library Paths:**

All external libraries must be configured in `configure/CONFIG_SITE.local` for both ADSupport and ADCore:

```dockerfile
# XML2 (Required)
WITH_XML2=YES
XML2_EXTERNAL=YES
XML2_INCLUDE=/usr/include/libxml2
XML2_LIB=/usr/lib/x86_64-linux-gnu

# HDF5 (Required for HDF5 plugin)
WITH_HDF5=YES
HDF5_EXTERNAL=YES
HDF5_INCLUDE=/usr/include/hdf5/serial
HDF5_LIB=/usr/lib/x86_64-linux-gnu/hdf5/serial

# NETCDF (Required for NetCDF plugin)
WITH_NETCDF=YES
NETCDF_EXTERNAL=YES
NETCDF_INCLUDE=/usr/include
NETCDF_LIB=/usr/lib/x86_64-linux-gnu

# SZIP, ZLIB, JPEG, TIFF (Required for various plugins)
WITH_SZIP=YES
SZIP_EXTERNAL=YES
SZIP_INCLUDE=/usr/include
SZIP_LIB=/usr/lib/x86_64-linux-gnu

WITH_ZLIB=YES
ZLIB_EXTERNAL=YES
ZLIB_INCLUDE=/usr/include
ZLIB_LIB=/usr/lib/x86_64-linux-gnu

WITH_JPEG=YES
JPEG_EXTERNAL=YES
JPEG_INCLUDE=/usr/include
JPEG_LIB=/usr/lib/x86_64-linux-gnu

WITH_TIFF=YES
TIFF_EXTERNAL=YES
TIFF_INCLUDE=/usr/include /usr/include/x86_64-linux-gnu
TIFF_LIB=/usr/lib/x86_64-linux-gnu
```

**Why This Is Required:**

- Without these paths, the compiler cannot find headers like `libxml/parser.h`, `hdf5.h`, etc.
- Setting only `XML2_EXTERNAL=YES` is not sufficient - you must also set the `_INCLUDE` and `_LIB` paths
- The CONFIG_SITE.local file is where these are defined, but it won't be read unless explicitly included

### Required EPICS Build System Files

The KREIOS IOC requires two additional files in the `configure/` directory that are not included
by default when creating a new EPICS IOC application:

#### 1. configure/Makefile

This file provides the `install` target required by the EPICS build system:

```makefile
# Makefile for configure directory
# Just provides install target - no compilation needed

TOP = ..
include $(TOP)/configure/CONFIG

# Targets needed by RULES_DIRS
DIRS =

include $(TOP)/configure/RULES_DIRS
```

**Without this file, the build fails with:**
```
make[1]: *** No rule to make target 'install'.  Stop.
make: *** [configure.install] Error 2
```

#### 2. configure/RULES.ioc

This file provides build rules for IOC boot directories:

```makefile
# RULES.ioc - Build rules for IOC boot directories

include $(EPICS_BASE)/configure/RULES.ioc
```

**Without this file, the build fails with:**
```
Makefile:6: ../../configure/RULES.ioc: No such file or directory
make[2]: *** No rule to make target '../../configure/RULES.ioc'.  Stop.
```

**Why These Are Needed:**

Standard EPICS IOC applications created with `makeBaseApp.pl` include these files automatically.
However, when building an IOC from scratch or converting from another framework (like caproto),
these files must be created manually.

## Troubleshooting Guide

### Common Build Errors and Solutions

#### Error: `fatal error: libxml/parser.h: No such file or directory`

**Cause:** XML2 include path not configured

**Solution:**
1. Ensure `libxml2-dev` is installed in the builder image
2. Add CONFIG_SITE.local include to configure/CONFIG_SITE
3. Set XML2_INCLUDE=/usr/include/libxml2 in configure/CONFIG_SITE.local

#### Error: `fatal error: hdf5.h: No such file or directory`

**Cause:** HDF5 include path not configured

**Solution:**
1. Ensure `libhdf5-dev` is installed in the builder image
2. Set HDF5_INCLUDE=/usr/include/hdf5/serial in configure/CONFIG_SITE.local
3. Set HDF5_LIB=/usr/lib/x86_64-linux-gnu/hdf5/serial

**Note:** HDF5 headers are in a `serial` subdirectory on Debian/Ubuntu systems

#### Error: `make[1]: *** No rule to make target 'install'.  Stop.`

**Cause:** Missing configure/Makefile

**Solution:** Create `configure/Makefile` (see "Required EPICS Build System Files" above)

#### Error: `No rule to make target '../../configure/RULES.ioc'`

**Cause:** Missing configure/RULES.ioc

**Solution:** Create `configure/RULES.ioc` (see "Required EPICS Build System Files" above)

#### Error: Variables in CONFIG_SITE.local are ignored

**Cause:** CONFIG_SITE doesn't include CONFIG_SITE.local

**Solution:** Add the include directive to configure/CONFIG_SITE:
```bash
echo "-include \$(TOP)/configure/CONFIG_SITE.local" >> configure/CONFIG_SITE
```

### Verifying External Library Configuration

To verify that external libraries are correctly configured, check the Makefile output during build:

```bash
# Look for these in the build output
grep -i "xml2" /tmp/docker_build.log
grep -i "hdf5" /tmp/docker_build.log

# Should see include paths like:
# -I/usr/include/libxml2
# -I/usr/include/hdf5/serial
```

### Finding Library Paths on Debian/Ubuntu

If library paths change in future OS versions, use these commands to find them:

```bash
# Find header file locations
dpkg -L libxml2-dev | grep "\.h$" | head -1 | xargs dirname
dpkg -L libhdf5-dev | grep "\.h$" | head -1 | xargs dirname
dpkg -L libnetcdf-dev | grep "\.h$" | head -1 | xargs dirname

# Find library file locations
dpkg -L libxml2 | grep "\.so$" | head -1 | xargs dirname
dpkg -L libhdf5-103-1 | grep "\.so$" | head -1 | xargs dirname
```

## Step-by-Step Upgrade Process

When upgrading to a new areaDetector version, follow these steps:

### Step 1: Determine New Version Commit Hashes

```bash
# Clone or update the areaDetector meta-repository
git clone https://github.com/areaDetector/areaDetector.git /tmp/areaDetector
cd /tmp/areaDetector

# List available versions
git tag | grep -E "^R3" | sort -V | tail -5

# Checkout the new version (e.g., R3-15)
git checkout R3-15

# Get ADCore commit hash
git ls-tree R3-15 ADCore
# Output: 160000 commit <ADCORE_HASH>	ADCore

# Get ADSupport commit hash
git ls-tree R3-15 ADSupport
# Output: 160000 commit <ADSUPPORT_HASH>	ADSupport
```

### Step 2: Update Dockerfile

Update the version and commit hashes:

```dockerfile
ARG ADCORE_VERSION=R3-15
# ... later in the file ...

# ADSupport
RUN git clone https://github.com/areaDetector/ADSupport.git \
    && cd ADSupport \
    && git checkout <ADSUPPORT_HASH>

# ADCore
RUN git clone https://github.com/areaDetector/ADCore.git \
    && cd ADCore \
    && git checkout <ADCORE_HASH>
```

### Step 3: Update VERSION_NOTES.md

Update the compatibility matrix and build status sections.

### Step 4: Test Build

```bash
cd docker
docker compose build --no-cache ioc 2>&1 | tee /tmp/build.log
```

### Step 5: Check for New Issues

Review the build log for:
- New header file errors (may indicate new library dependencies)
- Makefile changes (check release notes)
- Configuration changes (compare CONFIG_SITE examples)

### Step 6: Commit Changes

```bash
git add docker/Dockerfile docker/VERSION_NOTES.md
git commit -m "Upgrade areaDetector to R3-15"
git push
```

## Build Status

Last successful build: 2026-01-14
- ADCore: R3-14 (commit d27d71fb73bd915bdd714c8c4c78c05e3f31b1ce)
- ADSupport: commit 62b91c1154a74a1fb532d831a6ec029bb311b8f7
- Built with XML2 support enabled (XML2_EXTERNAL=YES)
- All external libraries configured with explicit paths
- Required EPICS build system files: configure/Makefile, configure/RULES.ioc
