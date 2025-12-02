#!/usr/bin/env python3
"""
Real-time Data Collection Example for Prodigy Remote In Protocol

Demonstrates:
1. How to poll and collect data in real-time during acquisition
2. How to reshape multi-dimensional data (1D, 2D, 3D)
3. How to save to HDF5 format (non-proprietary)
4. How to visualize data as it arrives

This is the pattern your IOC should follow.
"""

import socket
import time
import numpy as np
import h5py
import json
from datetime import datetime


class ProdigyRealtimeClient:
    """Client that collects data in real-time from Prodigy"""
    
    def __init__(self, host='localhost', port=7010):
        self.host = host
        self.port = port
        self.sock = None
        self.request_counter = 0
        
        # Acquisition metadata
        self.start_energy = 0
        self.end_energy = 0
        self.step_width = 0
        self.num_samples = 0
        self.values_per_sample = 1
        self.num_slices = 1
        
        # Data buffer
        self.data_buffer = []
        self.last_read_index = -1
    
    def connect(self):
        """Connect to Prodigy simulator"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        resp = self.send_command("Connect")
        print(f"Connected: {resp}")
    
    def disconnect(self):
        """Disconnect from Prodigy"""
        if self.sock:
            self.send_command("Disconnect")
            self.sock.close()
            self.sock = None
    
    def send_command(self, command, params=None):
        """Send command and receive response"""
        self.request_counter += 1
        req_id = f"{self.request_counter:04X}"
        
        request = f"?{req_id} {command}"
        if params:
            param_str = ' '.join(f'{k}:{v}' for k, v in params.items())
            request += f" {param_str}"
        
        self.sock.sendall((request + "\n").encode('utf-8'))
        response = self.sock.recv(65536).decode('utf-8').strip()
        
        return response
    
    def parse_response(self, response):
        """Parse response and extract parameters"""
        if "Error:" in response:
            raise RuntimeError(f"Prodigy error: {response}")
        
        params = {}
        if "OK:" in response:
            parts = response.split("OK:", 1)[1].strip().split()
            for part in parts:
                if ':' in part:
                    key, value = part.split(':', 1)
                    # Remove quotes
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    params[key] = value
        
        return params
    
    def define_spectrum_1d(self, start, end, step, dwell, pass_energy):
        """Define 1D spectrum (simple XPS/UPS)"""
        print("\n=== Defining 1D Spectrum ===")
        params = {
            "StartEnergy": str(start),
            "EndEnergy": str(end),
            "StepWidth": str(step),
            "DwellTime": str(dwell),
            "PassEnergy": str(pass_energy),
            "ValuesPerSample": "1",
            "NumberOfSlices": "1"
        }
        resp = self.send_command("DefineSpectrumFAT", params)
        print(f"  {resp}")
        
        self.start_energy = start
        self.end_energy = end
        self.step_width = step
        self.values_per_sample = 1
        self.num_slices = 1
        self.num_samples = int((end - start) / step + 1)
    
    def define_spectrum_2d(self, start, end, step, dwell, pass_energy, detector_pixels):
        """Define 2D spectrum (imaging detector or angular resolved)"""
        print("\n=== Defining 2D Spectrum ===")
        values_per_sample = detector_pixels
        params = {
            "StartEnergy": str(start),
            "EndEnergy": str(end),
            "StepWidth": str(step),
            "DwellTime": str(dwell),
            "PassEnergy": str(pass_energy),
            "ValuesPerSample": str(values_per_sample),
            "NumberOfSlices": "1"
        }
        resp = self.send_command("DefineSpectrumFAT", params)
        print(f"  {resp}")
        print(f"  Data shape will be: ({int((end-start)/step+1)}, {detector_pixels})")
        
        self.start_energy = start
        self.end_energy = end
        self.step_width = step
        self.values_per_sample = values_per_sample
        self.num_slices = 1
        self.num_samples = int((end - start) / step + 1)
    
    def define_spectrum_3d(self, start, end, step, dwell, pass_energy, detector_pixels, num_slices):
        """Define 3D spectrum (depth profiling, angle-resolved with spatial)"""
        print("\n=== Defining 3D Spectrum ===")
        values_per_sample = detector_pixels
        params = {
            "StartEnergy": str(start),
            "EndEnergy": str(end),
            "StepWidth": str(step),
            "DwellTime": str(dwell),
            "PassEnergy": str(pass_energy),
            "ValuesPerSample": str(values_per_sample),
            "NumberOfSlices": str(num_slices)
        }
        resp = self.send_command("DefineSpectrumFAT", params)
        print(f"  {resp}")
        print(f"  Data shape will be: ({num_slices}, {int((end-start)/step+1)}, {detector_pixels})")
        
        self.start_energy = start
        self.end_energy = end
        self.step_width = step
        self.values_per_sample = values_per_sample
        self.num_slices = num_slices
        self.num_samples = int((end - start) / step + 1)
    
    def validate_and_start(self):
        """Validate spectrum and start acquisition"""
        resp = self.send_command("ValidateSpectrum")
        print(f"\nValidation: {resp}")
        
        resp = self.send_command("Start")
        print(f"Start: {resp}")
        
        self.data_buffer = []
        self.last_read_index = -1
    
    def get_status(self):
        """Get current acquisition status"""
        resp = self.send_command("GetAcquisitionStatus")
        params = self.parse_response(resp)
        return {
            'status': params.get('ControllerStatus', '').strip('"'),
            'points': int(params.get('NumberOfAcquiredPoints', 0)),
            'elapsed': float(params.get('ElapsedTime', 0))
        }
    
    def read_new_data(self):
        """
        Read newly acquired data since last read.
        This is the key real-time polling method.
        """
        status = self.get_status()
        
        # Calculate total data points available
        # Each "sample" (energy step) has values_per_sample data points
        total_values_available = status['points'] * self.values_per_sample
        
        if total_values_available <= self.last_read_index + 1:
            return None  # No new data
        
        # Read from last position to current
        from_index = self.last_read_index + 1
        to_index = total_values_available - 1
        
        if to_index < from_index:
            return None
        
        resp = self.send_command("GetAcquisitionData", {
            "FromIndex": str(from_index),
            "ToIndex": str(to_index)
        })
        
        params = self.parse_response(resp)
        data_str = params.get('Data', '[]')
        
        # Parse data array
        if data_str.startswith('[') and data_str.endswith(']'):
            data_values = [float(x) for x in data_str[1:-1].split(',') if x.strip()]
            self.data_buffer.extend(data_values)
            self.last_read_index = to_index
            return data_values
        
        return None
    
    def reshape_data(self):
        """
        Reshape flattened data buffer to proper dimensions.
        
        Returns numpy array with shape:
        - 1D: (num_samples,)
        - 2D: (num_samples, values_per_sample)
        - 3D: (num_slices, num_samples, values_per_sample)
        """
        data = np.array(self.data_buffer)
        
        if self.num_slices > 1:
            # 3D data
            expected_size = self.num_slices * self.num_samples * self.values_per_sample
            if len(data) < expected_size:
                # Pad with zeros if acquisition not complete
                data = np.pad(data, (0, expected_size - len(data)), 'constant')
            shape = (self.num_slices, self.num_samples, self.values_per_sample)
            return data[:expected_size].reshape(shape)
        
        elif self.values_per_sample > 1:
            # 2D data
            expected_size = self.num_samples * self.values_per_sample
            if len(data) < expected_size:
                data = np.pad(data, (0, expected_size - len(data)), 'constant')
            shape = (self.num_samples, self.values_per_sample)
            return data[:expected_size].reshape(shape)
        
        else:
            # 1D data
            return data[:self.num_samples]
    
    def save_to_hdf5(self, filename):
        """
        Save data to HDF5 format (non-proprietary).
        This is what your IOC should do.
        """
        data = self.reshape_data()
        
        with h5py.File(filename, 'w') as f:
            # Create dataset
            f.create_dataset('intensity', data=data)
            
            # Add metadata as attributes
            f.attrs['start_energy'] = self.start_energy
            f.attrs['end_energy'] = self.end_energy
            f.attrs['step_width'] = self.step_width
            f.attrs['num_samples'] = self.num_samples
            f.attrs['values_per_sample'] = self.values_per_sample
            f.attrs['num_slices'] = self.num_slices
            f.attrs['timestamp'] = datetime.now().isoformat()
            
            # Create energy axis
            energy_axis = np.linspace(self.start_energy, self.end_energy, self.num_samples)
            f.create_dataset('energy', data=energy_axis)
            
            # Add dimension labels
            if data.ndim == 1:
                f.attrs['dimensions'] = '1D: [energy]'
            elif data.ndim == 2:
                f.attrs['dimensions'] = '2D: [energy, detector_pixel]'
            elif data.ndim == 3:
                f.attrs['dimensions'] = '3D: [slice, energy, detector_pixel]'
        
        print(f"\nSaved to HDF5: {filename}")
        print(f"  Shape: {data.shape}")
        print(f"  Size: {data.nbytes / 1024:.1f} KB")


def demo_1d_realtime():
    """Demo 1: Real-time collection of 1D spectrum"""
    print("\n" + "="*70)
    print("DEMO 1: Real-time 1D Spectrum Collection")
    print("="*70)
    
    client = ProdigyRealtimeClient()
    client.connect()
    
    # Define 1D spectrum: 400-410 eV, 0.5 eV steps
    client.define_spectrum_1d(
        start=400.0,
        end=410.0,
        step=0.5,
        dwell=0.1,
        pass_energy=20.0
    )
    
    client.validate_and_start()
    
    # Poll for data in real-time
    print("\nCollecting data in real-time...")
    while True:
        new_data = client.read_new_data()
        if new_data:
            status = client.get_status()
            print(f"  [{status['elapsed']:.1f}s] Got {len(new_data)} new points, "
                  f"total: {len(client.data_buffer)}, status: {status['status']}")
        
        status = client.get_status()
        if status['status'] == 'completed':
            print("\n✓ Acquisition completed!")
            break
        
        time.sleep(0.2)
    
    # Save to HDF5
    client.save_to_hdf5('demo_1d_spectrum.h5')
    
    # Show sample data
    data = client.reshape_data()
    print(f"\nSample data (first 5 points):")
    for i in range(min(5, len(data))):
        energy = client.start_energy + i * client.step_width
        print(f"  {energy:.1f} eV: {data[i]:.1f} counts")
    
    client.disconnect()


def demo_2d_realtime():
    """Demo 2: Real-time collection of 2D spectrum (imaging detector)"""
    print("\n" + "="*70)
    print("DEMO 2: Real-time 2D Spectrum Collection (Imaging)")
    print("="*70)
    
    client = ProdigyRealtimeClient()
    client.connect()
    
    # Define 2D spectrum: 400-410 eV with 16 detector pixels
    client.define_spectrum_2d(
        start=400.0,
        end=410.0,
        step=1.0,
        dwell=0.05,
        pass_energy=20.0,
        detector_pixels=16
    )
    
    client.validate_and_start()
    
    # Poll for data
    print("\nCollecting 2D data in real-time...")
    while True:
        new_data = client.read_new_data()
        if new_data:
            status = client.get_status()
            print(f"  [{status['elapsed']:.1f}s] Got {len(new_data)} new values, "
                  f"total: {len(client.data_buffer)}, status: {status['status']}")
        
        status = client.get_status()
        if status['status'] == 'completed':
            print("\n✓ Acquisition completed!")
            break
        
        time.sleep(0.1)
    
    # Save to HDF5
    client.save_to_hdf5('demo_2d_spectrum.h5')
    
    # Show structure
    data = client.reshape_data()
    print(f"\n2D Data structure:")
    print(f"  Shape: {data.shape} (energy × detector_pixels)")
    print(f"  Energy range: {client.start_energy} - {client.end_energy} eV")
    print(f"  Detector pixels: {client.values_per_sample}")
    
    client.disconnect()


def demo_3d_realtime():
    """Demo 3: Real-time collection of 3D spectrum"""
    print("\n" + "="*70)
    print("DEMO 3: Real-time 3D Spectrum Collection")
    print("="*70)
    
    client = ProdigyRealtimeClient()
    client.connect()
    
    # Define 3D spectrum: 4 slices × 11 energies × 8 detector pixels
    client.define_spectrum_3d(
        start=400.0,
        end=410.0,
        step=1.0,
        dwell=0.05,
        pass_energy=20.0,
        detector_pixels=8,
        num_slices=4
    )
    
    client.validate_and_start()
    
    # Poll for data
    print("\nCollecting 3D data in real-time...")
    while True:
        new_data = client.read_new_data()
        if new_data:
            status = client.get_status()
            print(f"  [{status['elapsed']:.1f}s] Got {len(new_data)} new values, "
                  f"total: {len(client.data_buffer)}, status: {status['status']}")
        
        status = client.get_status()
        if status['status'] == 'completed':
            print("\n✓ Acquisition completed!")
            break
        
        time.sleep(0.1)
    
    # Save to HDF5
    client.save_to_hdf5('demo_3d_spectrum.h5')
    
    # Show structure
    data = client.reshape_data()
    print(f"\n3D Data structure:")
    print(f"  Shape: {data.shape} (slices × energy × detector_pixels)")
    print(f"  Total data points: {data.size}")
    
    client.disconnect()


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*70)
    print("Prodigy Real-time Data Collection Examples")
    print("="*70)
    print("\nThis demonstrates how to:")
    print("  1. Poll for new data during acquisition")
    print("  2. Handle 1D, 2D, and 3D datasets")
    print("  3. Reshape flattened data to proper dimensions")
    print("  4. Save to HDF5 (non-proprietary format)")
    print("\nNOTE: Start ProdigySimServer.py in another terminal first!")
    print("="*70)
    
    if len(sys.argv) > 1:
        demo = sys.argv[1]
        if demo == "1d":
            demo_1d_realtime()
        elif demo == "2d":
            demo_2d_realtime()
        elif demo == "3d":
            demo_3d_realtime()
        else:
            print(f"\nUsage: {sys.argv[0]} [1d|2d|3d]")
    else:
        # Run all demos
        try:
            demo_1d_realtime()
            time.sleep(1)
            demo_2d_realtime()
            time.sleep(1)
            demo_3d_realtime()
        except Exception as e:
            print(f"\n✗ Error: {e}")
            import traceback
            traceback.print_exc()
