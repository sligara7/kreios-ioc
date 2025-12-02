#!/usr/bin/env python3
"""
SpecsLab Prodigy Remote In Protocol Simulator

Simulates the SpecsLab Prodigy Remote In interface (v1.2) for KREIOS-150 detector.
Based on the protocol specification from SpecsLabProdigy_RemoteIn.md

Protocol Summary:
- TCP server on port 7010
- ASCII text-based request/reply protocol
- Request format: ?<id> Command [Params]
- Response format: !<id> OK[:OutParams] or !<id> Error:<code> <message>
- Single client connection only
- Commands terminated with newline \\n

Author: Updated for Python 3 and SpecsLab Prodigy v4.x compatibility
Date: December 2025
"""

import socketserver
import sys
import time
import json
import threading
import math
from datetime import datetime
from enum import Enum


class AcquisitionState(Enum):
    """Acquisition state machine states"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"


class ProdigySimHandler(socketserver.StreamRequestHandler):
    """
    TCP handler for SpecsLab Prodigy Remote In protocol.
    Instantiated once per client connection.
    """
    
    def __init__(self, request, client_address, server):
        # Initialize spectrum and acquisition state before calling parent
        self.spectrum_defined = False
        self.spectrum_validated = False
        self.acquisition_state = AcquisitionState.IDLE
        self.acquisition_start_time = None
        self.acquisition_thread = None
        self.acquired_data = []
        self.acquisition_progress = 0
        self.total_samples = 0
        
        # Spectrum parameters (for DefineSpectrumFAT)
        self.start_energy = 0.0
        self.end_energy = 0.0
        self.step_width = 0.0
        self.dwell_time = 0.0
        self.pass_energy = 0.0
        self.lens_mode = ""
        self.scan_range = ""
        self.num_scans = 1
        self.num_slices = 1
        self.values_per_sample = 1
        
        # Detector dimensions (for 2D/3D data)
        # 1D: ValuesPerSample=1
        # 2D: ValuesPerSample=N (energy channels × detector pixels)
        # 3D: NumberOfSlices>1 (adds depth dimension)
        self.num_energy_channels = 1
        self.num_detector_pixels = 1
        
        # Fixed acquisition mode parameters
        self.fixed_energies = []
        self.fixed_transmission_values = []
        
        # Device parameters loaded from file
        self.device_parameters = {}
        
        super().__init__(request, client_address, server)
    
    def setup(self):
        """Called before handle() to initialize the connection"""
        super().setup()
        self.load_device_parameters()
        self.client_connected = False
        print(f"[{datetime.now()}] Client connected from {self.client_address}")
    
    def load_device_parameters(self):
        """Load device parameters from parameters.dat file"""
        try:
            with open('parameters.dat', 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(',')
                    if len(parts) >= 3:
                        name = parts[0]
                        param_type = parts[1]
                        value = parts[2]
                        self.device_parameters[name] = {
                            'type': param_type,
                            'value': value
                        }
            print(f"[{datetime.now()}] Loaded {len(self.device_parameters)} device parameters")
        except FileNotFoundError:
            print(f"[{datetime.now()}] Warning: parameters.dat not found, using empty parameter set")
            self.device_parameters = {}
    
    def handle(self):
        """Main connection loop - receives and processes commands"""
        while True:
            try:
                # Read one line (command terminated by \n)
                raw_line = self.rfile.readline()
                if not raw_line:
                    # Connection closed by client
                    break
                
                command_line = raw_line.decode('utf-8').strip()
                if not command_line:
                    continue
                
                print(f"[{datetime.now()}] RX: {command_line}")
                
                # Parse and execute command
                response = self.parse_command(command_line)
                
                if response:
                    print(f"[{datetime.now()}] TX: {response}")
                    self.wfile.write((response + "\n").encode('utf-8'))
                    self.wfile.flush()
            
            except ConnectionResetError:
                print(f"[{datetime.now()}] Connection reset by client")
                break
            except Exception as e:
                print(f"[{datetime.now()}] Error handling request: {e}")
                import traceback
                traceback.print_exc()
                break
        
        print(f"[{datetime.now()}] Client disconnected")
    
    def parse_command(self, command_line):
        """
        Parse incoming command and generate response.
        
        Command format: ?<id> Command [Params]
        Response format: !<id> OK[:OutParams] or !<id> Error:<code> <message>
        """
        if not command_line:
            return None
        
        # Check for proper request format (starts with ?)
        if command_line[0] != '?':
            if not self.client_connected:
                return "!FFFF Error: 4 Unknown message format."
            return None
        
        # Extract request ID (4 hex digits)
        if len(command_line) < 5:
            return "!FFFF Error: 4 Unknown message format."
        
        req_id = command_line[1:5]
        
        # Extract command and parameters
        if len(command_line) < 7:
            return f"!{req_id} Error: 4 Unknown message format."
        
        command_part = command_line[6:]  # Skip "?<id> "
        
        # Parse command name and parameters
        tokens = command_part.split()
        if not tokens:
            return f"!{req_id} Error: 4 Unknown message format."
        
        command_name = tokens[0]
        params = self.parse_parameters(tokens[1:]) if len(tokens) > 1 else {}
        
        # Route to appropriate handler
        return self.execute_command(req_id, command_name, params)
    
    def parse_parameters(self, param_tokens):
        """
        Parse key:value parameters from command tokens.
        Returns dict of {key: value}
        
        Handles quoted values that may contain spaces:
        ParameterName:"Detector Voltage" -> {"ParameterName": "Detector Voltage"}
        """
        params = {}
        i = 0
        while i < len(param_tokens):
            token = param_tokens[i]
            
            if ':' not in token:
                i += 1
                continue
            
            # Split on first colon only
            key, value = token.split(':', 1)
            
            # If value starts with quote but doesn't end with quote,
            # it was split by spaces - reassemble
            if value.startswith('"') and not value.endswith('"'):
                # Collect tokens until we find the closing quote
                value_parts = [value]
                i += 1
                while i < len(param_tokens):
                    value_parts.append(param_tokens[i])
                    if param_tokens[i].endswith('"'):
                        break
                    i += 1
                value = ' '.join(value_parts)
            
            # Remove quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            
            params[key] = value
            i += 1
        
        return params
    
    def execute_command(self, req_id, command, params):
        """Execute the requested command and return formatted response"""
        
        # Connection management commands
        if command == "Connect":
            return self.cmd_connect(req_id)
        elif command == "Disconnect":
            return self.cmd_disconnect(req_id)
        
        # Spectrum definition commands
        elif command == "DefineSpectrumFAT":
            return self.cmd_define_spectrum_fat(req_id, params)
        elif command == "DefineSpectrumFFR":
            return self.cmd_define_spectrum_ffr(req_id, params)
        elif command == "DefineSpectrumFE":
            return self.cmd_define_spectrum_fe(req_id, params)
        elif command == "ValidateSpectrum":
            return self.cmd_validate_spectrum(req_id)
        elif command == "ClearSpectrum":
            return self.cmd_clear_spectrum(req_id)
        
        # Acquisition control commands
        elif command == "Start":
            return self.cmd_start(req_id, params)
        elif command == "Pause":
            return self.cmd_pause(req_id)
        elif command == "Resume":
            return self.cmd_resume(req_id)
        elif command == "Abort":
            return self.cmd_abort(req_id)
        elif command == "GetAcquisitionStatus":
            return self.cmd_get_acquisition_status(req_id)
        elif command == "GetAcquisitionData":
            return self.cmd_get_acquisition_data(req_id, params)
        
        # Device parameter commands
        elif command == "GetAllAnalyzerParameterNames":
            return self.cmd_get_all_parameter_names(req_id)
        elif command == "GetAnalyzerParameterInfo":
            return self.cmd_get_parameter_info(req_id, params)
        elif command == "GetAnalyzerParameterValue":
            return self.cmd_get_parameter_value(req_id, params)
        elif command == "SetAnalyzerParameterValue":
            return self.cmd_set_parameter_value(req_id, params)
        
        else:
            return f"!{req_id} Error: 101 Unknown command: {command}"
    
    # ========== Connection Commands ==========
    
    def cmd_connect(self, req_id):
        """Handle Connect command"""
        if self.client_connected:
            return f"!{req_id} Error: 2 Already connected to a TCP client."
        
        self.client_connected = True
        return f'!{req_id} OK: ServerName:"SpecsLab Prodigy Simulator" ProtocolVersion:1.2'
    
    def cmd_disconnect(self, req_id):
        """Handle Disconnect command"""
        if not self.client_connected:
            return f"!{req_id} Error: 3 You are not connected."
        
        # Clean up any running acquisition
        if self.acquisition_state == AcquisitionState.RUNNING:
            self.acquisition_state = AcquisitionState.ABORTED
        
        self.client_connected = False
        return f"!{req_id} OK"
    
    # ========== Spectrum Definition Commands ==========
    
    def cmd_define_spectrum_fat(self, req_id, params):
        """
        Define spectrum in Fixed Analyzer Transmission (FAT) mode.
        
        Required params: StartEnergy, EndEnergy, StepWidth, DwellTime, PassEnergy
        Optional: LensMode, ScanRange, NumberOfScans, NumberOfSlices, ValuesPerSample
        
        Data dimensionality:
        - 1D: ValuesPerSample=1 (simple spectrum)
        - 2D: ValuesPerSample=N (N energy channels × M detector pixels)
        - 3D: NumberOfSlices>1 (adds spatial/angular dimension)
        """
        try:
            self.start_energy = float(params.get('StartEnergy', 0))
            self.end_energy = float(params.get('EndEnergy', 0))
            self.step_width = float(params.get('StepWidth', 1))
            self.dwell_time = float(params.get('DwellTime', 0.1))
            self.pass_energy = float(params.get('PassEnergy', 20))
            self.lens_mode = params.get('LensMode', 'HighMagnification')
            self.scan_range = params.get('ScanRange', 'MediumArea')
            self.num_scans = int(params.get('NumberOfScans', 1))
            self.num_slices = int(params.get('NumberOfSlices', 1))
            self.values_per_sample = int(params.get('ValuesPerSample', 1))
            
            # Parse detector dimensions if provided
            self.num_energy_channels = int(params.get('NumberOfEnergyChannels', 1))
            self.num_detector_pixels = int(params.get('NumberOfNonEnergyChannels', 1))
            
            # Calculate number of samples (energy steps)
            self.total_samples = int((self.end_energy - self.start_energy) / self.step_width + 1)
            
            self.spectrum_defined = True
            self.spectrum_validated = False
            
            # Determine dimensionality
            dimension_info = "1D"
            if self.num_slices > 1:
                dimension_info = f"3D ({self.total_samples}×{self.values_per_sample}×{self.num_slices})"
            elif self.values_per_sample > 1:
                dimension_info = f"2D ({self.total_samples}×{self.values_per_sample})"
            
            print(f"  Spectrum defined: {self.total_samples} samples, "
                  f"{self.start_energy}-{self.end_energy} eV, "
                  f"step={self.step_width} eV, {dimension_info}")
            
            return f"!{req_id} OK"
        
        except (ValueError, KeyError) as e:
            return f"!{req_id} Error: 201 Invalid spectrum parameters: {e}"
    
    def cmd_define_spectrum_ffr(self, req_id, params):
        """Define spectrum in Fixed Retard Ratio (FRR) mode - stub"""
        # For simulation, just acknowledge
        self.spectrum_defined = True
        self.spectrum_validated = False
        return f"!{req_id} OK"
    
    def cmd_define_spectrum_fe(self, req_id, params):
        """
        Define spectrum in Fixed Energies mode.
        
        Params: Energies (array), TransmissionValues (array), DwellTime
        """
        try:
            # Parse energy array: Energies:[1.0,2.0,3.0,...]
            energies_str = params.get('Energies', '[]')
            if energies_str.startswith('[') and energies_str.endswith(']'):
                self.fixed_energies = [float(x) for x in energies_str[1:-1].split(',') if x.strip()]
            
            # Parse transmission array (optional)
            trans_str = params.get('TransmissionValues', '[]')
            if trans_str.startswith('[') and trans_str.endswith(']'):
                self.fixed_transmission_values = [float(x) for x in trans_str[1:-1].split(',') if x.strip()]
            
            self.dwell_time = float(params.get('DwellTime', 0.1))
            self.total_samples = len(self.fixed_energies)
            
            self.spectrum_defined = True
            self.spectrum_validated = False
            
            return f"!{req_id} OK"
        
        except (ValueError, KeyError) as e:
            return f"!{req_id} Error: 201 Invalid spectrum parameters: {e}"
    
    def cmd_validate_spectrum(self, req_id):
        """Validate the defined spectrum"""
        if not self.spectrum_defined:
            return f"!{req_id} Error: 202 No spectrum defined."
        
        # Return spectrum parameters
        response = (
            f"!{req_id} OK: "
            f"StartEnergy:{self.start_energy} "
            f"EndEnergy:{self.end_energy} "
            f"StepWidth:{self.step_width} "
            f"Samples:{self.total_samples} "
            f"DwellTime:{self.dwell_time} "
            f"PassEnergy:{self.pass_energy} "
            f'LensMode:"{self.lens_mode}" '
            f'ScanRange:"{self.scan_range}"'
        )
        
        self.spectrum_validated = True
        return response
    
    def cmd_clear_spectrum(self, req_id):
        """Clear the defined spectrum"""
        self.spectrum_defined = False
        self.spectrum_validated = False
        self.acquired_data = []
        return f"!{req_id} OK"
    
    # ========== Acquisition Control Commands ==========
    
    def cmd_start(self, req_id, params):
        """Start data acquisition"""
        if not self.spectrum_validated:
            return f"!{req_id} Error: 203 Spectrum not validated."
        
        if self.acquisition_state == AcquisitionState.RUNNING:
            return f"!{req_id} Error: 204 Acquisition already running."
        
        # Parse optional parameters
        set_safe_state = params.get('SetSafeStateAfter', 'false').lower() == 'true'
        
        # Start acquisition in background thread
        self.acquisition_state = AcquisitionState.RUNNING
        self.acquisition_start_time = time.time()
        self.acquisition_progress = 0
        self.acquired_data = []
        
        # Start simulation thread
        self.acquisition_thread = threading.Thread(target=self._simulate_acquisition)
        self.acquisition_thread.daemon = True
        self.acquisition_thread.start()
        
        return f"!{req_id} OK"
    
    def cmd_pause(self, req_id):
        """Pause running acquisition"""
        if self.acquisition_state != AcquisitionState.RUNNING:
            return f"!{req_id} Error: 205 No acquisition running."
        
        self.acquisition_state = AcquisitionState.PAUSED
        return f"!{req_id} OK"
    
    def cmd_resume(self, req_id):
        """Resume paused acquisition"""
        if self.acquisition_state != AcquisitionState.PAUSED:
            return f"!{req_id} Error: 206 Acquisition not paused."
        
        self.acquisition_state = AcquisitionState.RUNNING
        return f"!{req_id} OK"
    
    def cmd_abort(self, req_id):
        """Abort running or paused acquisition"""
        if self.acquisition_state not in [AcquisitionState.RUNNING, AcquisitionState.PAUSED]:
            return f"!{req_id} Error: 207 No acquisition to abort."
        
        self.acquisition_state = AcquisitionState.ABORTED
        return f"!{req_id} OK"
    
    def cmd_get_acquisition_status(self, req_id):
        """Get current acquisition status"""
        elapsed_time = 0
        if self.acquisition_start_time:
            elapsed_time = time.time() - self.acquisition_start_time
        
        # Build status response
        response = (
            f"!{req_id} OK: "
            f'ControllerStatus:"{self.acquisition_state.value}" '
            f"NumberOfAcquiredPoints:{self.acquisition_progress} "
            f"ElapsedTime:{elapsed_time:.2f} "
            f"CurrentIteration:1"
        )
        
        return response
    
    def cmd_get_acquisition_data(self, req_id, params):
        """
        Get acquired data.
        
        Params: FromIndex, ToIndex (optional, defaults to all data)
        """
        from_index = int(params.get('FromIndex', 0))
        to_index = int(params.get('ToIndex', len(self.acquired_data) - 1))
        
        # Validate indices
        if from_index < 0 or to_index >= len(self.acquired_data):
            return f"!{req_id} Error: 208 Invalid data range."
        
        if from_index > to_index:
            return f"!{req_id} Error: 208 Invalid data range (from > to)."
        
        # Extract data slice
        data_slice = self.acquired_data[from_index:to_index + 1]
        
        # Format data array as [value1,value2,...]
        data_str = '[' + ','.join(f'{v:.6f}' for v in data_slice) + ']'
        
        response = (
            f"!{req_id} OK: "
            f"FromIndex:{from_index} "
            f"ToIndex:{to_index} "
            f"Data:{data_str}"
        )
        
        return response
    
    # ========== Device Parameter Commands ==========
    
    def cmd_get_all_parameter_names(self, req_id):
        """Get list of all analyzer parameter names"""
        names = ','.join(f'"{name}"' for name in self.device_parameters.keys())
        return f"!{req_id} OK: ParameterNames:[{names}]"
    
    def cmd_get_parameter_info(self, req_id, params):
        """Get information about a specific parameter"""
        param_name = params.get('ParameterName', '')
        
        if param_name not in self.device_parameters:
            return f'!{req_id} Error: 301 Parameter "{param_name}" not found.'
        
        param_info = self.device_parameters[param_name]
        value_type = param_info['type']
        
        return f"!{req_id} OK: ValueType:{value_type}"
    
    def cmd_get_parameter_value(self, req_id, params):
        """Get current value of a parameter"""
        param_name = params.get('ParameterName', '')
        
        if param_name not in self.device_parameters:
            return f'!{req_id} Error: 301 Parameter "{param_name}" not found.'
        
        param_info = self.device_parameters[param_name]
        value = param_info['value']
        
        return f'!{req_id} OK: Name:"{param_name}" Value:{value}'
    
    def cmd_set_parameter_value(self, req_id, params):
        """Set value of a parameter (if allowed in remote experiment)"""
        param_name = params.get('ParameterName', '')
        new_value = params.get('Value', '')
        
        if param_name not in self.device_parameters:
            return f'!{req_id} Error: 301 Parameter "{param_name}" not found.'
        
        # Update the parameter
        self.device_parameters[param_name]['value'] = new_value
        
        return f"!{req_id} OK"
    
    # ========== Acquisition Simulation ==========
    
    def _simulate_acquisition(self):
        """
        Background thread that simulates data acquisition.
        Generates synthetic spectrum data based on defined parameters.
        
        Data is stored as a flattened 1D array following Prodigy's format:
        - 1D: [intensity0, intensity1, ...]
        - 2D: [sample0_val0, sample0_val1, ..., sample1_val0, sample1_val1, ...]
        - 3D: [slice0_sample0_val0, slice0_sample0_val1, ..., slice1_sample0_val0, ...]
        
        Client (IOC) must reshape based on ValuesPerSample and NumberOfSlices.
        """
        print(f"[{datetime.now()}] Starting acquisition simulation...")
        
        total_points = self.total_samples * self.values_per_sample * self.num_slices
        point_index = 0
        
        for slice_idx in range(self.num_slices):
            for sample_idx in range(self.total_samples):
                # Check if paused
                while self.acquisition_state == AcquisitionState.PAUSED:
                    time.sleep(0.1)
                
                # Check if aborted
                if self.acquisition_state == AcquisitionState.ABORTED:
                    print(f"[{datetime.now()}] Acquisition aborted at {point_index}/{total_points}")
                    return
                
                # Calculate energy for this sample
                energy = self.start_energy + sample_idx * self.step_width
                center_energy = (self.start_energy + self.end_energy) / 2
                sigma = (self.end_energy - self.start_energy) / 6
                
                # Generate multi-dimensional data for this energy step
                for val_idx in range(self.values_per_sample):
                    # For 2D/3D: add spatial/angular variation
                    # Simulate detector pixel or slice variation
                    spatial_offset = (val_idx - self.values_per_sample / 2) * 0.2
                    slice_offset = (slice_idx - self.num_slices / 2) * 0.1
                    
                    # Gaussian peak with spatial/slice variations
                    effective_energy = energy + spatial_offset + slice_offset
                    intensity = 1000 * math.exp(-((effective_energy - center_energy) ** 2) / (2 * sigma ** 2))
                    
                    # Add realistic noise
                    noise = intensity * 0.1 * (hash(str(time.time() + val_idx)) % 100 - 50) / 50
                    intensity += noise
                    intensity = max(0, intensity)  # No negative counts
                    
                    # Add to flattened data array
                    self.acquired_data.append(intensity)
                    point_index += 1
                
                # Update progress (in terms of energy samples, not individual values)
                self.acquisition_progress = (slice_idx * self.total_samples) + sample_idx + 1
                
                # Simulate dwell time (per energy step, not per pixel)
                time.sleep(self.dwell_time / 10)  # Speed up for simulation (10x faster)
        
        # Mark as completed
        if self.acquisition_state == AcquisitionState.RUNNING:
            self.acquisition_state = AcquisitionState.COMPLETED
            shape_info = f"{self.total_samples}"
            if self.values_per_sample > 1:
                shape_info += f"×{self.values_per_sample}"
            if self.num_slices > 1:
                shape_info += f"×{self.num_slices}"
            print(f"[{datetime.now()}] Acquisition completed: {total_points} total points ({shape_info})")


class ProdigySimServer(socketserver.TCPServer):
    """
    TCP server that enforces single-client connection policy.
    """
    # Allow socket reuse to avoid "Address already in use" errors
    allow_reuse_address = True
    
    def __init__(self, server_address, RequestHandlerClass):
        super().__init__(server_address, RequestHandlerClass)
        self.client_connected = False
    
    def verify_request(self, request, client_address):
        """Override to enforce single-client policy"""
        if self.client_connected:
            print(f"[{datetime.now()}] Rejected connection from {client_address} - "
                  f"server already has a connected client")
            return False
        
        self.client_connected = True
        return True
    
    def shutdown_request(self, request):
        """Override to track disconnection"""
        self.client_connected = False
        super().shutdown_request(request)


def main():
    """Main entry point"""
    HOST = "localhost"
    PORT = 7010
    
    print("=" * 70)
    print("SpecsLab Prodigy Remote In Protocol Simulator")
    print("=" * 70)
    print(f"Protocol Version: 1.2")
    print(f"Listening on: {HOST}:{PORT}")
    print(f"Single client connection enforced")
    print(f"Press Ctrl+C to stop")
    print("=" * 70)
    
    try:
        with ProdigySimServer((HOST, PORT), ProdigySimHandler) as server:
            print(f"[{datetime.now()}] Server started successfully")
            server.serve_forever()
    
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"[{datetime.now()}] Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
