#!/usr/bin/env python3
"""
Test script to verify connectivity to the Prodigy simulator/server.

This script sends basic commands to test:
1. Connection establishment
2. Protocol version check
3. Device name query
4. Basic spectrum definition

Usage:
    python3 test_connection.py [host] [port]

Arguments:
    host - Prodigy server hostname (default: localhost)
    port - Prodigy server port (default: 7010)
"""

import socket
import sys
import time


def send_command(sock, req_id, command):
    """Send a command and receive response."""
    full_cmd = f"?{req_id:04X} {command}\n"
    print(f"TX: {full_cmd.strip()}")
    sock.sendall(full_cmd.encode('utf-8'))

    response = sock.recv(4096).decode('utf-8').strip()
    print(f"RX: {response}")
    return response


def test_connection(host='localhost', port=7010):
    """Test connection to Prodigy server."""
    print(f"\n{'='*50}")
    print(f"Testing connection to {host}:{port}")
    print(f"{'='*50}\n")

    req_id = 0

    try:
        # Create socket connection
        print("Connecting...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect((host, port))
        print(f"Connected!\n")

        # Test 1: Connect command
        print("Test 1: Connect")
        req_id += 1
        response = send_command(sock, req_id, "Connect")
        if "OK" not in response:
            print("  FAILED - Connect command rejected")
            return False
        print("  PASSED\n")

        # Test 2: Get visible name
        print("Test 2: GetAnalyzerVisibleName")
        req_id += 1
        response = send_command(sock, req_id, "GetAnalyzerVisibleName")
        if "OK" not in response:
            print("  FAILED - Could not get device name")
            return False
        print("  PASSED\n")

        # Test 3: Get parameter names
        print("Test 3: GetAllAnalyzerParameterNames")
        req_id += 1
        response = send_command(sock, req_id, "GetAllAnalyzerParameterNames")
        if "OK" not in response:
            print("  FAILED - Could not get parameter names")
            return False
        print("  PASSED\n")

        # Test 4: Define 1D spectrum (FAT mode)
        print("Test 4: DefineSpectrumFAT (1D)")
        req_id += 1
        response = send_command(sock, req_id,
            "DefineSpectrumFAT StartEnergy:82.0 EndEnergy:86.0 "
            "StepWidth:0.1 DwellTime:0.5 PassEnergy:10.0")
        if "OK" not in response:
            print("  FAILED - Could not define FAT spectrum")
            return False
        print("  PASSED\n")

        # Test 5: Validate spectrum
        print("Test 5: ValidateSpectrum")
        req_id += 1
        response = send_command(sock, req_id, "ValidateSpectrum")
        if "OK" not in response:
            print("  FAILED - Spectrum validation failed")
            return False
        print("  PASSED\n")

        # Test 6: Clear spectrum (clean up)
        print("Test 6: ClearSpectrum")
        req_id += 1
        response = send_command(sock, req_id, "ClearSpectrum")
        if "OK" not in response:
            print("  FAILED - Could not clear spectrum")
            return False
        print("  PASSED\n")

        # Test 7: Disconnect
        print("Test 7: Disconnect")
        req_id += 1
        response = send_command(sock, req_id, "Disconnect")
        print("  PASSED\n")

        sock.close()

        print(f"{'='*50}")
        print("All tests PASSED!")
        print(f"{'='*50}")
        return True

    except socket.timeout:
        print(f"\nERROR: Connection timeout to {host}:{port}")
        print("Make sure the simulator is running:")
        print("  cd sim && python3 ProdigySimServer.py")
        return False
    except ConnectionRefusedError:
        print(f"\nERROR: Connection refused to {host}:{port}")
        print("Make sure the simulator is running:")
        print("  cd sim && python3 ProdigySimServer.py")
        return False
    except Exception as e:
        print(f"\nERROR: {e}")
        return False


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else 'localhost'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 7010

    success = test_connection(host, port)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
