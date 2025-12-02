# Data Dimensionality Quick Reference

## Prodigy Remote In Protocol - Data Format Guide

### Overview

The Prodigy Remote In protocol returns data as **flattened ASCII arrays** via TCP/IP. The client (your IOC) must reshape the data based on the spectrum parameters.

---

## 1D Spectrum (Simple XPS/UPS)

**Definition:**
```
DefineSpectrumFAT StartEnergy:400 EndEnergy:410 StepWidth:0.5
                   DwellTime:0.1 PassEnergy:20
                   ValuesPerSample:1 NumberOfSlices:1
```

**Shape:** `(21,)` - One intensity per energy

**Protocol Response:**
```
GetAcquisitionData FromIndex:0 ToIndex:20
!0102 OK: Data:[123.4,234.5,345.6,456.7,567.8,678.9,...]
```

**IOC Processing:**
```python
data = [123.4, 234.5, 345.6, ...]  # 21 values
energy = np.linspace(400, 410, 21)
# Plot: intensity vs energy
```

---

## 2D Spectrum (Imaging Detector / ARPES)

**Definition:**
```
DefineSpectrumFAT StartEnergy:400 EndEnergy:410 StepWidth:1.0
                   DwellTime:0.1 PassEnergy:20
                   ValuesPerSample:128 NumberOfSlices:1
```

**Shape:** `(11, 128)` - Energy × Detector Pixels

**Protocol Response:**
```
GetAcquisitionData FromIndex:0 ToIndex:1407
!0102 OK: Data:[E0_P0, E0_P1, E0_P2, ..., E0_P127,
                E1_P0, E1_P1, E1_P2, ..., E1_P127,
                ...]
```

**IOC Processing:**
```python
flat_data = [...]  # 11 × 128 = 1408 values
data_2d = np.array(flat_data).reshape(11, 128)
# Axis 0: Energy (11 steps)
# Axis 1: Detector pixel (128 channels)
# Plot: 2D image or angle-resolved dispersion
```

**Storage (HDF5):**
```python
with h5py.File('arpes.h5', 'w') as f:
    f.create_dataset('intensity', data=data_2d)
    f.create_dataset('energy', data=np.linspace(400, 410, 11))
    f.create_dataset('angle', data=np.linspace(-15, 15, 128))
```

---

## 3D Spectrum (Depth Profiling / Multi-slice)

**Definition:**
```
DefineSpectrumFAT StartEnergy:400 EndEnergy:410 StepWidth:1.0
                   DwellTime:0.1 PassEnergy:20
                   ValuesPerSample:128 NumberOfSlices:5
```

**Shape:** `(5, 11, 128)` - Slices × Energy × Detector Pixels

**Protocol Response:**
```
GetAcquisitionData FromIndex:0 ToIndex:7039
!0102 OK: Data:[S0_E0_P0, S0_E0_P1, ..., S0_E0_P127,
                S0_E1_P0, S0_E1_P1, ..., S0_E1_P127,
                ...
                S0_E10_P0, ..., S0_E10_P127,
                S1_E0_P0, S1_E0_P1, ...]
```

**IOC Processing:**
```python
flat_data = [...]  # 5 × 11 × 128 = 7040 values
data_3d = np.array(flat_data).reshape(5, 11, 128)
# Axis 0: Slice/depth (5 steps)
# Axis 1: Energy (11 steps)
# Axis 2: Detector pixel (128 channels)
# Visualize: Volume rendering or slice-by-slice 2D images
```

**Use Cases:**
- Depth profiling (with sputtering between slices)
- Time-resolved measurements (slices = time points)
- Multi-region scanning (slices = spatial positions)

---

## Real-time Polling Pattern

### Problem
You want to collect data **as it arrives** during a long acquisition, not wait for completion.

### Solution
Poll `GetAcquisitionData` with incremental indices:

```python
# After Start command
last_index = -1
data_buffer = []

while True:
    # Check progress
    status = GetAcquisitionStatus()
    num_samples = status['NumberOfAcquiredPoints']  # Energy steps completed
    total_values = num_samples * ValuesPerSample
    
    # Prodigy returns total_values in the flattened buffer
    # Example: If 3 energy steps done with 128 pixels each → 384 values
    
    if total_values > last_index + 1:
        # Read new chunk
        new_data = GetAcquisitionData(FromIndex=last_index+1, 
                                      ToIndex=total_values-1)
        data_buffer.extend(new_data)
        last_index = total_values - 1
        
        # Update live display PV
        update_pv("LIVE_DATA", data_buffer)
    
    if status['ControllerStatus'] == 'completed':
        break
    
    time.sleep(0.5)  # Poll every 500ms

# Final reshape
data_nd = np.array(data_buffer).reshape(NumSlices, NumSamples, ValuesPerSample)
```

---

## Index Calculation

**Given:**
- `NumSamples` (S) = number of energy steps
- `ValuesPerSample` (V) = detector pixels or channels
- `NumberOfSlices` (N) = depth/time slices

**Total data points:** `T = N × S × V`

**To access slice `n`, sample `s`, pixel `p`:**
```
index = n × (S × V) + s × V + p
```

**Example:** 5 slices × 11 energies × 128 pixels
- First point: `index = 0`
- Last point of first slice: `index = 11 × 128 - 1 = 1407`
- First point of second slice: `index = 1408`
- Last point overall: `index = 5 × 11 × 128 - 1 = 7039`

---

## Common Detector Configurations

### KREIOS-150 (from specs)
- **Type:** Delay-line detector (DLD)
- **Pixels:** Typically 128-512 spatial channels
- **Slices:** 1 (for single spectrum) or multiple (depth profiling)
- **Typical 2D:** 100 energies × 300 pixels = 30,000 values

### Phoibos HSA
- **1D mode:** Single channel, ValuesPerSample=1
- **2D mode:** 1D DLD or CCD, ValuesPerSample=128-2048

### General Imaging Detectors
- **1D:** Linear detector (e.g., 128 channels)
- **2D:** Area detector (e.g., 512×512 flattened to 262,144 values per energy)

---

## HDF5 Storage Best Practices

```python
import h5py
import numpy as np

# After acquisition complete and data reshaped
with h5py.File('spectrum.h5', 'w') as f:
    # Main data
    dset = f.create_dataset('intensity', data=data_nd, 
                            compression='gzip', compression_opts=4)
    
    # Axes
    f.create_dataset('energy', data=np.linspace(start, end, num_samples))
    if data_nd.ndim >= 2:
        f.create_dataset('detector_channel', data=np.arange(values_per_sample))
    if data_nd.ndim == 3:
        f.create_dataset('slice_index', data=np.arange(num_slices))
    
    # Metadata
    f.attrs['start_energy'] = start_energy
    f.attrs['end_energy'] = end_energy
    f.attrs['step_width'] = step_width
    f.attrs['pass_energy'] = pass_energy
    f.attrs['dwell_time'] = dwell_time
    f.attrs['acquisition_time'] = datetime.now().isoformat()
    f.attrs['instrument'] = 'KREIOS-150'
    
    # Prodigy metadata
    f.attrs['lens_mode'] = lens_mode
    f.attrs['scan_range'] = scan_range
    f.attrs['values_per_sample'] = values_per_sample
    f.attrs['number_of_slices'] = num_slices
```

---

## Testing with Simulator

```bash
# Terminal 1: Start simulator
python3 ProdigySimServer.py

# Terminal 2: Test 1D
python3 realtime_data_example.py 1d

# Terminal 2: Test 2D
python3 realtime_data_example.py 2d

# Terminal 2: Test 3D
python3 realtime_data_example.py 3d
```

Each demo:
1. Defines spectrum with appropriate dimensions
2. Starts acquisition
3. Polls for data in real-time
4. Reshapes flattened array to N-D
5. Saves to HDF5 with metadata

Inspect the HDF5 files:
```bash
h5dump -H demo_2d_spectrum.h5
h5ls -r demo_3d_spectrum.h5
```

Or in Python:
```python
import h5py
with h5py.File('demo_2d_spectrum.h5', 'r') as f:
    print(f.keys())
    print(f['intensity'].shape)
    print(dict(f.attrs))
```

---

## Summary

| Dimension | ValuesPerSample | NumberOfSlices | Total Points | Use Case |
|-----------|----------------|----------------|--------------|----------|
| 1D | 1 | 1 | N | Standard XPS/UPS |
| 2D | M | 1 | N × M | ARPES, spatial imaging |
| 3D | M | L | N × M × L | Depth profiling, 3D imaging |

**Key Takeaway:** Prodigy returns a **flat ASCII array** via TCP/IP. Your IOC must:
1. Poll during acquisition to get real-time data
2. Parse ASCII response into float array
3. Reshape based on `ValuesPerSample` and `NumberOfSlices`
4. Save to HDF5 or any format you choose

**The protocol does NOT write files** - you have complete control over storage format!
