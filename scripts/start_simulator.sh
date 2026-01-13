#!/bin/bash
#
# Start the KREIOS-150 Prodigy Protocol Simulator
#
# Usage: ./start_simulator.sh [port]
#   port - TCP port number (default: 7010)
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIM_DIR="$SCRIPT_DIR/../sim"

PORT=${1:-7010}

echo "========================================"
echo "KREIOS-150 Prodigy Protocol Simulator"
echo "========================================"
echo "Port: $PORT"
echo "Simulator: $SIM_DIR/ProdigySimServer.py"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================"

cd "$SIM_DIR"
python3 ProdigySimServer.py --port $PORT
