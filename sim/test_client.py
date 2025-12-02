#!/usr/bin/env python3
"""
Test client for SpecsLab Prodigy Remote In Protocol Simulator

This script tests the simulator by running through a typical acquisition workflow.
"""

import socket
import time
import sys


class ProdigyTestClient:
    """Simple test client for Prodigy Remote In protocol"""
    
    def __init__(self, host='localhost', port=7010):
        self.host = host
        self.port = port
        self.sock = None
        self.request_counter = 0
    
    def connect(self):
        """Connect to the server"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print(f"Connected to {self.host}:{self.port}")
    
    def disconnect(self):
        """Disconnect from server"""
        if self.sock:
            self.sock.close()
            self.sock = None
    
    def send_command(self, command, params=None):
        """
        Send a command and receive response.
        
        Args:
            command: Command name (e.g., "Connect", "Start")
            params: Dictionary of parameters (optional)
        
        Returns:
            Response string from server
        """
        # Generate request ID
        self.request_counter += 1
        req_id = f"{self.request_counter:04X}"
        
        # Build request string
        request = f"?{req_id} {command}"
        if params:
            param_str = ' '.join(f'{k}:{v}' for k, v in params.items())
            request += f" {param_str}"
        
        # Send request
        print(f"TX: {request}")
        self.sock.sendall((request + "\n").encode('utf-8'))
        
        # Receive response
        response = self.sock.recv(4096).decode('utf-8').strip()
        print(f"RX: {response}")
        
        return response
    
    def run_test_sequence(self):
        """Run a complete test acquisition sequence"""
        print("\n" + "=" * 70)
        print("Starting Prodigy Simulator Test Sequence")
        print("=" * 70 + "\n")
        
        # 1. Connect
        print("\n--- Test 1: Connect ---")
        resp = self.send_command("Connect")
        assert "OK:" in resp and "ProtocolVersion:1.2" in resp
        print("✓ Connect successful\n")
        
        # 2. Get parameter names
        print("--- Test 2: Get All Parameter Names ---")
        resp = self.send_command("GetAllAnalyzerParameterNames")
        assert "ParameterNames:" in resp
        print("✓ Parameter names retrieved\n")
        
        # 3. Get a specific parameter value
        print("--- Test 3: Get Parameter Value ---")
        resp = self.send_command("GetAnalyzerParameterValue", 
                                {"ParameterName": '"Detector Voltage"'})
        assert "OK:" in resp and "Value:" in resp
        print("✓ Parameter value retrieved\n")
        
        # 4. Define spectrum (FAT mode)
        print("--- Test 4: Define Spectrum (FAT) ---")
        spectrum_params = {
            "StartEnergy": "400.0",
            "EndEnergy": "410.0",
            "StepWidth": "0.5",
            "DwellTime": "0.1",
            "PassEnergy": "20.0",
            "LensMode": '"HighMagnification"',
            "ScanRange": '"MediumArea"'
        }
        resp = self.send_command("DefineSpectrumFAT", spectrum_params)
        assert "OK" in resp
        print("✓ Spectrum defined\n")
        
        # 5. Validate spectrum
        print("--- Test 5: Validate Spectrum ---")
        resp = self.send_command("ValidateSpectrum")
        assert "OK:" in resp and "Samples:" in resp
        print("✓ Spectrum validated\n")
        
        # 6. Start acquisition
        print("--- Test 6: Start Acquisition ---")
        resp = self.send_command("Start")
        assert "OK" in resp
        print("✓ Acquisition started\n")
        
        # 7. Poll status
        print("--- Test 7: Poll Acquisition Status ---")
        for i in range(5):
            time.sleep(0.5)
            resp = self.send_command("GetAcquisitionStatus")
            assert "ControllerState:" in resp
            print(f"  Poll {i+1}: {resp}")
        print("✓ Status polling works\n")
        
        # 8. Wait for completion (or timeout)
        print("--- Test 8: Wait for Completion ---")
        timeout = 30
        start_time = time.time()
        while time.time() - start_time < timeout:
            resp = self.send_command("GetAcquisitionStatus")
            if "completed" in resp:
                print("✓ Acquisition completed\n")
                break
            time.sleep(1)
        else:
            print("⚠ Acquisition still running after timeout\n")
        
        # 9. Get acquisition data
        print("--- Test 9: Get Acquisition Data ---")
        resp = self.send_command("GetAcquisitionData", 
                                {"FromIndex": "0", "ToIndex": "9"})
        assert "Data:[" in resp
        print("✓ Data retrieved successfully\n")
        
        # 10. Clear spectrum
        print("--- Test 10: Clear Spectrum ---")
        resp = self.send_command("ClearSpectrum")
        assert "OK" in resp
        print("✓ Spectrum cleared\n")
        
        # 11. Disconnect
        print("--- Test 11: Disconnect ---")
        resp = self.send_command("Disconnect")
        assert "OK" in resp
        print("✓ Disconnected\n")
        
        print("\n" + "=" * 70)
        print("All Tests Passed!")
        print("=" * 70 + "\n")


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = 'localhost'
    
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    else:
        port = 7010
    
    client = ProdigyTestClient(host, port)
    
    try:
        client.connect()
        client.run_test_sequence()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
