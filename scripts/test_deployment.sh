#!/bin/bash
#
# KREIOS IOC Deployment Verification Script
#
# Tests the full deployment stack:
#   1. systemd service status
#   2. procServ connectivity
#   3. EPICS PV accessibility (caget)
#   4. Prodigy connection through the IOC
#   5. Basic IOC functionality (parameter read/write)
#
# Usage:
#   ./scripts/test_deployment.sh [prefix]
#
# Arguments:
#   prefix - PV prefix (default: XF:29ID2-ES{Det:Kreios}:)
#
# Environment:
#   EPICS_CA_ADDR_LIST - CA address list (default: 127.0.0.1)
#   PRODIGY_HOST       - Prodigy host for direct protocol test (optional)
#   PRODIGY_PORT       - Prodigy port (default: 7010)

set -uo pipefail

# Configuration
PREFIX="${1:-XF:29ID2-ES{Det:Kreios}:}"
IOC_NAME="kreios-det1"
PROCSERV_PORT=4000
PRODIGY_HOST="${PRODIGY_HOST:-}"
PRODIGY_PORT="${PRODIGY_PORT:-7010}"
CAGET_TIMEOUT=5

export EPICS_CA_ADDR_LIST="${EPICS_CA_ADDR_LIST:-127.0.0.1}"
export EPICS_CA_AUTO_ADDR_LIST=NO
export PATH="/opt/epics/base/bin/linux-x86_64:$PATH"

# Counters
PASS=0
FAIL=0
SKIP=0

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

pass() { ((PASS++)); echo -e "  ${GREEN}PASS${NC} - $1"; }
fail() { ((FAIL++)); echo -e "  ${RED}FAIL${NC} - $1"; }
skip() { ((SKIP++)); echo -e "  ${YELLOW}SKIP${NC} - $1"; }
info() { echo -e "  ${CYAN}INFO${NC} - $1"; }

caget_test() {
    local pv="$1"
    local description="${2:-$pv}"
    local result
    result=$(caget -t -w "$CAGET_TIMEOUT" "$pv" 2>&1)
    if [[ $? -eq 0 ]]; then
        pass "$description = $result"
        echo "$result"
        return 0
    else
        fail "$description (timeout or not found)"
        return 1
    fi
}

caput_test() {
    local pv="$1"
    local value="$2"
    local description="${3:-caput $pv $value}"
    local result
    result=$(caput -t -w "$CAGET_TIMEOUT" "$pv" "$value" 2>&1)
    if [[ $? -eq 0 ]]; then
        pass "$description"
        return 0
    else
        fail "$description"
        return 1
    fi
}

echo ""
echo "========================================================"
echo "  KREIOS IOC Deployment Verification"
echo "========================================================"
echo "  Prefix:       $PREFIX"
echo "  IOC name:     $IOC_NAME"
echo "  CA addr list: $EPICS_CA_ADDR_LIST"
echo "  procServ:     localhost:$PROCSERV_PORT"
echo "========================================================"

# ==================================================================
# Section 1: Infrastructure checks
# ==================================================================
echo ""
echo "--- Section 1: Infrastructure ---"

# 1.1 IOC directory exists
if [[ -d "/epics/iocs/$IOC_NAME" ]]; then
    pass "IOC directory /epics/iocs/$IOC_NAME exists"
else
    fail "IOC directory /epics/iocs/$IOC_NAME not found"
fi

# 1.2 Startup script exists and is executable
if [[ -x "/epics/iocs/$IOC_NAME/st.cmd" ]]; then
    pass "st.cmd exists and is executable"
else
    fail "st.cmd missing or not executable"
fi

# 1.3 systemd service exists
if [[ -f "/etc/systemd/system/softioc-$IOC_NAME.service" ]]; then
    pass "systemd service file exists"
else
    fail "systemd service file not found"
fi

# 1.4 systemd service is running
SERVICE_STATUS=$(systemctl is-active "softioc-$IOC_NAME" 2>&1)
if [[ "$SERVICE_STATUS" == "active" ]]; then
    pass "systemd service is active"
else
    fail "systemd service is $SERVICE_STATUS"
    echo ""
    echo "  Start with: sudo systemctl start softioc-$IOC_NAME"
    echo "  Check logs: journalctl -u softioc-$IOC_NAME --no-pager -n 50"
    echo ""
fi

# 1.5 procServ port is listening
if ss -tlnp 2>/dev/null | grep -q ":$PROCSERV_PORT " || \
   netstat -tlnp 2>/dev/null | grep -q ":$PROCSERV_PORT "; then
    pass "procServ listening on port $PROCSERV_PORT"
else
    fail "procServ not listening on port $PROCSERV_PORT"
fi

# 1.6 EPICS CA tools available
if command -v caget &>/dev/null; then
    pass "caget available: $(which caget)"
else
    fail "caget not found in PATH"
    echo "  Add to PATH: export PATH=/opt/epics/base/bin/linux-x86_64:\$PATH"
    echo ""
    echo "Cannot continue PV tests without caget."
    echo "========================================================"
    echo "Results: $PASS passed, $FAIL failed, $SKIP skipped"
    echo "========================================================"
    exit 1
fi

# ==================================================================
# Section 2: Basic PV accessibility
# ==================================================================
echo ""
echo "--- Section 2: Basic PV Accessibility ---"

# 2.1 Core areaDetector PVs
caget_test "${PREFIX}cam1:Manufacturer_RBV" "Manufacturer" >/dev/null
caget_test "${PREFIX}cam1:Model_RBV" "Model" >/dev/null

# 2.2 Connection status
CONNECTED=$(caget_test "${PREFIX}cam1:Connected_RBV" "Connection status")

# 2.3 Server name (only meaningful if connected)
caget_test "${PREFIX}cam1:ServerName_RBV" "Server name" >/dev/null

# 2.4 IOC heartbeat (devIocStats)
caget_test "${PREFIX}ioc:HEARTBEAT" "IOC heartbeat" >/dev/null

# ==================================================================
# Section 3: IOC configuration PVs
# ==================================================================
echo ""
echo "--- Section 3: Configuration PVs ---"

caget_test "${PREFIX}cam1:RunMode_RBV" "Run mode" >/dev/null
caget_test "${PREFIX}cam1:OperatingMode_RBV" "Operating mode" >/dev/null
caget_test "${PREFIX}cam1:StartEnergy_RBV" "Start energy" >/dev/null
caget_test "${PREFIX}cam1:EndEnergy_RBV" "End energy" >/dev/null
caget_test "${PREFIX}cam1:StepWidth_RBV" "Step width" >/dev/null
caget_test "${PREFIX}cam1:PassEnergy_RBV" "Pass energy" >/dev/null
caget_test "${PREFIX}cam1:ValuesPerSample_RBV" "Values per sample (1=1D)" >/dev/null
caget_test "${PREFIX}cam1:NumSlices_RBV" "Num slices (1=no 3D)" >/dev/null

# ==================================================================
# Section 4: Prodigy connection test
# ==================================================================
echo ""
echo "--- Section 4: Prodigy Connection ---"

if [[ "$CONNECTED" == "Connected" ]] || [[ "$CONNECTED" == "1" ]]; then
    pass "IOC reports connected to Prodigy"

    # Test reading values that require Prodigy connection
    caget_test "${PREFIX}cam1:LensMode_RBV" "Lens mode (from Prodigy)" >/dev/null
    caget_test "${PREFIX}cam1:ScanRange_RBV" "Scan range (from Prodigy)" >/dev/null

    # Test spectrum validation workflow
    echo ""
    echo "  Testing spectrum workflow..."
    caget_test "${PREFIX}cam1:SpectrumValid_RBV" "Spectrum valid status" >/dev/null

else
    info "IOC not connected to Prodigy - skipping Prodigy-dependent tests"
    skip "Lens mode (requires Prodigy connection)"
    skip "Scan range (requires Prodigy connection)"
    skip "Spectrum validation (requires Prodigy connection)"

    if [[ -n "$PRODIGY_HOST" ]]; then
        echo ""
        echo "  Testing direct TCP to Prodigy at $PRODIGY_HOST:$PRODIGY_PORT..."
        if timeout 5 bash -c "echo -n '' > /dev/tcp/$PRODIGY_HOST/$PRODIGY_PORT" 2>/dev/null; then
            pass "TCP connection to $PRODIGY_HOST:$PRODIGY_PORT succeeded"
            info "Prodigy is reachable but IOC isn't connected - check IOC logs"
        else
            fail "TCP connection to $PRODIGY_HOST:$PRODIGY_PORT failed"
            info "Check network: ping $PRODIGY_HOST"
            info "Check firewall: Windows may be blocking port $PRODIGY_PORT"
            info "Check Prodigy: Remote Control must be enabled in SpecsLab"
        fi
    else
        info "Set PRODIGY_HOST=<ip> to test direct TCP connectivity"
    fi
fi

# ==================================================================
# Section 5: areaDetector plugin PVs
# ==================================================================
echo ""
echo "--- Section 5: areaDetector Plugins ---"

caget_test "${PREFIX}image1:EnableCallbacks_RBV" "Image plugin enabled" >/dev/null
caget_test "${PREFIX}image1:ArraySize0_RBV" "Image array dim 0" >/dev/null

# ==================================================================
# Section 6: Write test (parameter set/readback)
# ==================================================================
echo ""
echo "--- Section 6: Parameter Write/Readback ---"

# Save original value
ORIG_START=$(caget -t -w "$CAGET_TIMEOUT" "${PREFIX}cam1:StartEnergy_RBV" 2>/dev/null)
if [[ -n "$ORIG_START" ]]; then
    # Write a test value
    caput_test "${PREFIX}cam1:StartEnergy" 100.0 "Set StartEnergy to 100.0"
    sleep 0.5
    NEW_START=$(caget -t -w "$CAGET_TIMEOUT" "${PREFIX}cam1:StartEnergy_RBV" 2>/dev/null)
    if [[ "$NEW_START" == "100" ]] || [[ "$NEW_START" == "100.0" ]] || [[ "$NEW_START" == "100.000"* ]]; then
        pass "StartEnergy readback matches (${NEW_START})"
    else
        fail "StartEnergy readback mismatch (expected 100.0, got ${NEW_START})"
    fi
    # Restore original
    caput -t -w "$CAGET_TIMEOUT" "${PREFIX}cam1:StartEnergy" "$ORIG_START" 2>/dev/null
    info "Restored StartEnergy to $ORIG_START"
else
    skip "Parameter write/readback (StartEnergy not readable)"
fi

# ==================================================================
# Section 7: Direct protocol test (if host specified)
# ==================================================================
echo ""
echo "--- Section 7: Direct Protocol Test ---"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -n "$PRODIGY_HOST" ]] && [[ -f "$SCRIPT_DIR/test_connection.py" ]]; then
    echo "  Running test_connection.py against $PRODIGY_HOST:$PRODIGY_PORT..."
    if python3 "$SCRIPT_DIR/test_connection.py" "$PRODIGY_HOST" "$PRODIGY_PORT"; then
        pass "Direct protocol test passed"
    else
        fail "Direct protocol test failed"
    fi
elif [[ -z "$PRODIGY_HOST" ]]; then
    skip "Direct protocol test (set PRODIGY_HOST to enable)"
else
    skip "Direct protocol test (test_connection.py not found)"
fi

# ==================================================================
# Summary
# ==================================================================
echo ""
echo "========================================================"
echo "  Results: ${GREEN}$PASS passed${NC}, ${RED}$FAIL failed${NC}, ${YELLOW}$SKIP skipped${NC}"
echo "========================================================"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo "Troubleshooting:"
    echo "  IOC logs:    journalctl -u softioc-$IOC_NAME --no-pager -n 50"
    echo "  procServ:    telnet localhost $PROCSERV_PORT"
    echo "  IOC console: Type commands directly in procServ session"
    echo ""
    exit 1
else
    if [[ "$CONNECTED" == "Connected" ]] || [[ "$CONNECTED" == "1" ]]; then
        echo "IOC is deployed and connected to Prodigy."
    else
        echo "IOC is deployed and running. Connect Prodigy to complete setup."
    fi
    echo ""
    exit 0
fi
