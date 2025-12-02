# SpecsLab Prodigy Remote In Protocol Simulator

## Overview

This simulator implements the SpecsLab Prodigy Remote In protocol (version 1.2) for testing IOC development without requiring the actual Windows machine or KREIOS-150 hardware.

The simulator is based on the official protocol specification from `SpecsLabProdigy_RemoteIn.md` (VERSION 1.22, September 12, 2024).

## Files

- **ProdigySimServer.py** - Main simulator server implementing the Remote In protocol
- **test_client.py** - Test client that runs through a complete acquisition workflow
- **realtime_data_example.py** - Demonstrates real-time data collection and HDF5 export
- **parameters.dat** - Device parameters (detector voltage, bias voltages, etc.)

## What's New

This updated simulator (ProdigySimServer.py) includes:

✅ **Python 3 compatibility** - Modern async-capable code  
✅ **Complete protocol implementation** - All major commands from spec v1.2  
✅ **Realistic acquisition simulation** - Background thread with Gaussian peak data  
✅ **Proper state machine** - Tracks idle/running/paused/completed/aborted states  
✅ **Single-client enforcement** - Matches Prodigy's single-connection limitation  
✅ **Comprehensive error handling** - Proper error codes and messages  
✅ **Detailed logging** - Timestamped request/response logs for debugging  

## Protocol Implementation Status

### ✅ Fully Implemented Commands

#### Connection Management
- `Connect` - Establish connection, returns server name and protocol version
- `Disconnect` - Close connection and clean up

#### Spectrum Definition
- `DefineSpectrumFAT` - Fixed Analyzer Transmission mode
- `DefineSpectrumFFR` - Fixed Retard Ratio mode (stub)
- `DefineSpectrumFE` - Fixed Energies mode
- `ValidateSpectrum` - Validate defined spectrum parameters
- `ClearSpectrum` - Clear spectrum definition

#### Acquisition Control
- `Start` - Start data acquisition
- `Pause` - Pause running acquisition
- `Resume` - Resume paused acquisition
- `Abort` - Abort acquisition
- `GetAcquisitionStatus` - Get current status (state, progress, time)
- `GetAcquisitionData` - Retrieve acquired data (supports slicing)

#### Device Parameters
- `GetAllAnalyzerParameterNames` - List all available parameters
- `GetAnalyzerParameterInfo` - Get parameter type information
- `GetAnalyzerParameterValue` - Read parameter value
- `SetAnalyzerParameterValue` - Write parameter value

### ⚠️ Not Implemented (not needed for basic IOC development)
- `GetAllAvailableExperiments`
- `LoadExperiment`
- `SaveExperiment`
- `GetAllDeviceNames`
- Advanced detector region commands
- Sputtering/depth profile commands

## Quick Start

### 1. Start the Simulator

```bash
cd /home/asligar/git_projects/systems/kreios_ioc/sim
python3 ProdigySimServer.py
```

Expected output:
```
======================================================================
SpecsLab Prodigy Remote In Protocol Simulator
======================================================================
Protocol Version: 1.2
Listening on: localhost:7010
Single client connection enforced
Press Ctrl+C to stop
======================================================================
[2025-12-02 ...] Loaded 12 device parameters
[2025-12-02 ...] Server started successfully
```

### 2. Run Test Client (in another terminal)

```bash
cd /home/asligar/git_projects/systems/kreios_ioc/sim
python3 test_client.py
```

This will run through a complete test sequence:
1. Connect to simulator
2. Query device parameters
3. Define a spectrum (FAT mode, 400-410 eV)
4. Validate spectrum
5. Start acquisition
6. Poll status during acquisition
7. Retrieve acquired data
8. Clean up and disconnect

### 3. Real-time Data Collection Demo

```bash
# Run all demos (1D, 2D, 3D)
python3 realtime_data_example.py

# Or run specific demo
python3 realtime_data_example.py 1d   # Simple 1D spectrum
python3 realtime_data_example.py 2d   # 2D imaging detector
python3 realtime_data_example.py 3d   # 3D depth/angular profiling
```

This demonstrates:
- Real-time polling during acquisition
- Multi-dimensional data handling (1D, 2D, 3D)
- Data reshaping from Prodigy's flattened format
- Saving to HDF5 (non-proprietary format)

### 3. Manual Testing with telnet/nc

```bash
# Connect
telnet localhost 7010

# Send commands (type these manually)
?0001 Connect
?0002 GetAllAnalyzerParameterNames
?0003 DefineSpectrumFAT StartEnergy:400.0 EndEnergy:410.0 StepWidth:0.5 DwellTime:0.1 PassEnergy:20.0
?0004 ValidateSpectrum
?0005 Start
?0006 GetAcquisitionStatus
?0007 GetAcquisitionData FromIndex:0 ToIndex:9
?0008 Disconnect
```

## Protocol Format

### Request Format
```
?<id> Command [Param1:Value1 Param2:Value2 ...]
```

- `<id>` = 4-digit hexadecimal request ID (e.g., `0001`, `AB3F`)
- Command = case-sensitive command name
- Parameters = space-separated `key:value` pairs

### Response Format

Success:
```
!<id> OK
!<id> OK: Param1:Value1 Param2:Value2 ...
```

Error:
```
!<id> Error: <code> <message>
```

### Example Session

```
Client: ?0100 Connect
## Data Simulation

The simulator generates realistic photoelectron spectroscopy data in **1D, 2D, or 3D formats**:

### 1D Data (Simple Spectrum)
- **Parameters**: `ValuesPerSample=1`, `NumberOfSlices=1`
- **Shape**: `(num_samples,)` - one intensity value per energy
- **Use case**: Standard XPS/UPS scans
- **Example**: 21 energy points → 21 intensity values

### 2D Data (Imaging Detector)
- **Parameters**: `ValuesPerSample=N` (detector pixels), `NumberOfSlices=1`
- **Shape**: `(num_samples, detector_pixels)` - spatial/angular resolved
- **Use case**: ARPES, momentum-resolved spectroscopy
- **Example**: 21 energies × 128 pixels → 2,688 values
- **Data format**: Flattened as `[E0_P0, E0_P1, ..., E0_PN, E1_P0, E1_P1, ...]`

### 3D Data (Depth Profiling / Multi-slice)
- **Parameters**: `ValuesPerSample=N`, `NumberOfSlices=M`
- **Shape**: `(num_slices, num_samples, detector_pixels)`
- **Use case**: Depth profiling with sputtering, 3D imaging
- **Example**: 5 slices × 21 energies × 128 pixels → 13,440 values
- **Data format**: Flattened as `[S0_E0_P0, S0_E0_P1, ..., S1_E0_P0, ...]`

### Simulated Physics
- **Peak shape**: Gaussian centered in the energy range
- **Spatial variation**: Detector pixels show slight energy shifts (simulates angular dispersion)
- **Slice variation**: Different slices show offset peaks (simulates depth-dependent chemistry)
- **Intensity**: ~1000 counts at peak center
- **Noise**: ±10% random Poisson-like noise
- **Timing**: Simulated dwell time (10x faster than real for testing)

### Real-time Data Collection

**Key insight**: The Prodigy protocol returns data as **ASCII arrays in TCP responses**, NOT as files.

```python
# Client polls during acquisition
while acquisition_running:
    status = get_acquisition_status()  # Check progress
    new_data = get_acquisition_data(from_index, to_index)  # Read new points
    
    # Data arrives as ASCII: "Data:[123.4,567.8,...]"
    # Client must:
    # 1. Parse the ASCII response
    # 2. Reshape based on ValuesPerSample and NumberOfSlices
    # 3. Save to HDF5 or other format (YOUR choice)
```

See `realtime_data_example.py` for complete implementation.
Client: ?0105 GetAcquisitionData FromIndex:0 ToIndex:4
Server: !0105 OK: FromIndex:0 ToIndex:4 Data:[123.456,234.567,345.678,456.789,567.890]
```

## Data Simulation

The simulator generates realistic photoelectron spectroscopy data:

- **Peak shape**: Gaussian centered in the energy range
- **Intensity**: ~1000 counts at peak center
- **Noise**: ±10% random noise
- **Timing**: Simulated dwell time (10x faster than real for testing)

Example for 400-410 eV range:
- Peak centered at 405 eV
- FWHM ≈ 3.3 eV
- Background ≈ 0-50 counts
- Peak ≈ 1000 counts

## Device Parameters

Default parameters loaded from `parameters.dat`:

| Parameter Name | Type | Default Value |
|----------------|------|---------------|
| NumNonEnergyChannels | integer | 10 |
| Bias Voltage Electrons | double | 0 |
| Bias Voltage Ions | double | 0 |
| Detector Voltage | double | 0 |
| Kinetic Energy Base | double | 0 |
| Focus Displacement 1 | double | 0 |
| Aux Voltage | double | 0 |
| DLD Voltage | double | 0 |
| Coil Current | double | 0 |
| Maximum Count Rate [kcps] | double | 0 |
| Analyzer Standby Delay [s] | double | 0 |
| Skip Delay Up/Down | integer | 0 |

You can modify `parameters.dat` to add more parameters or change default values.

## Acquisition State Machine

```
IDLE ─────────> RUNNING ─────────> COMPLETED
                   │  ▲
                   │  │
                   ▼  │
                 PAUSED
                   │
                   ▼
                ABORTED
```

- **IDLE**: No acquisition defined or ready to start
- **RUNNING**: Actively acquiring data
- **PAUSED**: Temporarily suspended (can Resume)
- **COMPLETED**: All data points acquired
- **ABORTED**: User-requested stop

## Common Error Codes

| Code | Description |
|------|-------------|
| 2 | Already connected to a TCP client |
| 3 | You are not connected |
| 4 | Unknown message format |
| 101 | Unknown command |
| 201-208 | Spectrum/acquisition errors |
| 301 | Parameter not found |

See the protocol specification for complete error code list.

## Using with IOC Development

### Recommended Workflow

1. **Start simulator** on development machine
2. **Develop IOC** using the simulator as the target
3. **Test IOC commands** against simulator
4. **Verify data handling** with simulated acquisitions
5. **Deploy to production** pointing at real Windows/Prodigy instance

### Real-time Data Collection Pattern

The IOC should poll for new data during acquisition:

```python
# Start acquisition
send_command("Start")

# Poll loop (in background thread)
last_index = -1
while True:
    status = send_command("GetAcquisitionStatus")
    
    # Parse number of acquired points
    num_points = parse_int(status, "NumberOfAcquiredPoints")
    total_values = num_points * values_per_sample
    
    # Read new data since last poll
    if total_values > last_index + 1:
        new_data = send_command("GetAcquisitionData", 
                                {"FromIndex": last_index + 1, 
                                 "ToIndex": total_values - 1})
        
        # Parse ASCII response: Data:[123.4,567.8,...]
        values = parse_data_array(new_data)
        
        # Update EPICS waveform record
        update_pv("DATA_BUFFER", values)
        last_index = total_values - 1
    
    if "completed" in status:
        break
    
    time.sleep(0.5)  # Poll every 500ms

# Reshape for final storage
data_nd = reshape_data(buffer, num_samples, values_per_sample, num_slices)
save_to_hdf5(data_nd)
```

### Data Format Details

**Prodigy does NOT write files** - all data is transmitted via TCP/IP:

| Aspect | Prodigy Behavior | IOC Responsibility |
|--------|------------------|-------------------|
| **Transport** | ASCII over TCP/IP port 7010 | Parse socket responses |
| **Format** | `Data:[val1,val2,...]` in response | Parse array, convert to float |
| **Dimensions** | Flattened 1D array | Reshape based on metadata |
| **Storage** | None (real-time only) | Save to HDF5/NeXus/other |
| **Metadata** | In spectrum definition | Capture and store separately |

**Your IOC has full control** over the final data format. Options:
- **HDF5** (recommended): Non-proprietary, widely supported, self-describing
- **NeXus**: HDF5 with standardized metadata schema for scientific data
- **NumPy**: `.npy` files for Python-based analysis
- **TIFF**: For 2D images
- **CSV/ASCII**: Simple but large files
- **Custom binary**: Application-specific format

### Key Considerations for IOC

- **Single connection**: Only one client can connect at a time (like real Prodigy)
- **Asynchronous acquisition**: `Start` returns immediately, poll `GetAcquisitionStatus`
- **Data chunking**: Use `FromIndex/ToIndex` for large datasets
- **State tracking**: Monitor `ControllerStatus` to know when acquisition completes
- **Parameter mapping**: Map Prodigy parameter names to PV names
- **Buffer management**: Accumulate data in IOC memory, then reshape and save
- **Dimension tracking**: Store `ValuesPerSample` and `NumberOfSlices` to reshape correctly

### Example IOC Integration Points

```python
# Connect at IOC initialization
send_command("Connect")

# Define spectrum from PV values
send_command("DefineSpectrumFAT", {
    "StartEnergy": start_pv.get(),
    "EndEnergy": end_pv.get(),
    "StepWidth": step_pv.get(),
    ...
})

# Start acquisition when user triggers
send_command("Start")

# Poll in background thread
while True:
    status = send_command("GetAcquisitionStatus")
    if "completed" in status:
        break
    time.sleep(0.5)

# Retrieve all data
data = send_command("GetAcquisitionData", {"FromIndex": 0, "ToIndex": num_points-1})
```

## Troubleshooting

### Simulator won't start - "Address already in use"

Another process is using port 7010:
```bash
# Find the process
lsof -i :7010
# Kill it
kill <PID>
```

### Client can't connect - "Connection refused"

- Check simulator is running: `ps aux | grep ProdigySimServer`
- Check firewall: `sudo iptables -L`
- Try explicitly: `telnet localhost 7010`

### No data in GetAcquisitionData

- Ensure acquisition completed: check `GetAcquisitionStatus`
- Wait longer: acquisition takes `num_samples * dwell_time` seconds
- Check indices: `FromIndex` and `ToIndex` must be valid

### "Already connected" error

Simulator enforces single-client connection:
- Disconnect previous client first
- Restart simulator to clear connection state

## Testing Checklist

Before deploying IOC to production, verify with simulator:

- [ ] Connect/Disconnect sequence
- [ ] Parameter queries (names, info, values)
- [ ] Spectrum definition (FAT, FFR, FE modes)
- [ ] Spectrum validation
- [ ] Start/Pause/Resume/Abort
- [ ] Status polling during acquisition
- [ ] Data retrieval (full and sliced)
- [ ] Error handling (invalid commands, bad parameters)
- [ ] Reconnection after disconnect
- [ ] Multiple sequential acquisitions

## Next Steps

1. **Enhance simulator** (optional):
   - Add more realistic detector physics
   - Implement region-based acquisition
   - Add sputtering simulation
   - Persist acquisition history

2. **Develop IOC**:
   - Use `kreios_ioc/tools/prodigy_client.py` as base
   - Map PVs to Prodigy commands
   - Implement proxy for multi-user access
   - Add EPICS archiver integration

3. **Deploy**:
   - Test against real Prodigy instance
   - Validate data matches expected results
   - Set up monitoring and logging
   - Document operational procedures

## References

- **Protocol Spec**: `kreios_ioc/Documentation/SpecsLabProdigy_RemoteIn.md`
- **Remote Out Doc**: `kreios_ioc/Documentation/SpecsLabProdigy_RemoteOut.md`
- **Integration Plan**: `kreios_ioc/ioc_prodigy_bridge_kreios_integration.md`
- **SPECS Website**: http://www.specs-group.com

## License

This simulator is part of the systems repository and follows the same license terms.

## Support

For issues or questions:
- Check protocol specification first
- Review simulator logs (timestamps show request/response flow)
- Test with `test_client.py` to isolate issues
- Capture network traffic with `tcpdump` if needed

---

**Version**: 1.0  
**Date**: December 2025  
**Protocol**: SpecsLab Prodigy Remote In v1.2
