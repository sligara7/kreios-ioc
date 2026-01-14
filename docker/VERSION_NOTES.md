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

## Build Status

Last successful build: 2026-01-14
- ADCore: R3-14 (commit d27d71fb73bd915bdd714c8c4c78c05e3f31b1ce)
- ADSupport: commit 62b91c1154a74a1fb532d831a6ec029bb311b8f7
- Built with XML2 support enabled (XML2_EXTERNAL=YES)
