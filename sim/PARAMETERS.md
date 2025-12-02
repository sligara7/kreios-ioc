# Device Parameters Guide

## Overview

The `parameters.dat` file provides **initial default values** for KREIOS-150 analyzer device parameters. The IOC can read and modify these parameters at runtime using the protocol commands.

## File Format

```
ParameterName,Type,DefaultValue
```

**Example:**
```
Detector Voltage,double,0
Bias Voltage Electrons,double,0
Skip Delay Up/Down,integer,0
```

## Current Parameters

| Parameter Name | Type | Default | Description |
|----------------|------|---------|-------------|
| NumNonEnergyChannels | integer | 10 | Number of detector pixels/channels (non-energy dimension) |
| Bias Voltage Electrons | double | 0 | Electron bias voltage (V) |
| Bias Voltage Ions | double | 0 | Ion bias voltage (V) |
| Detector Voltage | double | 0 | Detector high voltage (V), typically 1800-2000V |
| Kinetic Energy Base | double | 0 | Base kinetic energy offset (eV) |
| Focus Displacement 1 | double | 0 | Lens focus displacement parameter 1 |
| Aux Voltage | double | 0 | Auxiliary voltage (V) |
| DLD Voltage | double | 0 | Delay-line detector voltage (V) |
| Coil Current | double | 0 | Magnetic coil current (A) |
| Maximum Count Rate [kcps] | double | 0 | Maximum detector count rate (kilo-counts per second) |
| Analyzer Standby Delay [s] | double | 0 | Delay before entering standby mode (seconds) |
| Skip Delay Up/Down | integer | 0 | Skip delay for voltage ramping (boolean: 0=false, 1=true) |

## Protocol Commands

### 1. List All Parameters
```
?0001 GetAllAnalyzerParameterNames
!0001 OK: ParameterNames:["Detector Voltage","Bias Voltage Electrons",...]
```

### 2. Get Parameter Information
```
?0002 GetAnalyzerParameterInfo ParameterName:"Detector Voltage"
!0002 OK: Type:LogicalVoltage ValueType:double Unit:"V"
```

### 3. Read Parameter Value
```
?0003 GetAnalyzerParameterValue ParameterName:"Detector Voltage"
!0003 OK: Name:"Detector Voltage" Value:0
```

### 4. Write Parameter Value
```
?0004 SetAnalyzerParameterValue ParameterName:"Detector Voltage" Value:1850
!0004 OK
```

**Important**: Parameters can only be changed when **no acquisition is running**.

## IOC Integration

### Reading Parameters

```python
class ProdigyIOC:
    def read_all_parameters(self):
        """Read all device parameters and create PVs"""
        # Get list of parameter names
        resp = self.client.send_command("GetAllAnalyzerParameterNames")
        param_names = self.parse_parameter_list(resp)
        
        # Read each parameter value
        for name in param_names:
            resp = self.client.send_command("GetAnalyzerParameterValue",
                                           {"ParameterName": name})
            value = self.parse_value(resp)
            
            # Create/update EPICS PV
            pv_name = self.map_to_pv_name(name)
            self.create_pv(pv_name, value)
```

### Writing Parameters

```python
class ProdigyIOC:
    def on_pv_write(self, pv_name, new_value):
        """Called when EPICS PV is written"""
        # Map PV name to parameter name
        param_name = self.map_to_param_name(pv_name)
        
        # Check if acquisition is running
        status = self.client.send_command("GetAcquisitionStatus")
        if self.is_running(status):
            print("Error: Cannot change parameters during acquisition")
            return False
        
        # Set the parameter
        resp = self.client.send_command("SetAnalyzerParameterValue",
                                       {"ParameterName": param_name,
                                        "Value": str(new_value)})
        return "OK" in resp
```

### PV Mapping Example

```python
PV_TO_PARAM = {
    "KREIOS:DETECTOR:VOLTAGE":     "Detector Voltage",
    "KREIOS:BIAS:ELECTRONS":       "Bias Voltage Electrons",
    "KREIOS:BIAS:IONS":            "Bias Voltage Ions",
    "KREIOS:FOCUS:DISP1":          "Focus Displacement 1",
    "KREIOS:AUX:VOLTAGE":          "Aux Voltage",
    "KREIOS:DLD:VOLTAGE":          "DLD Voltage",
    "KREIOS:COIL:CURRENT":         "Coil Current",
    "KREIOS:DETECTOR:MAXRATE":     "Maximum Count Rate [kcps]",
    "KREIOS:ANALYZER:STANDBY_DLY": "Analyzer Standby Delay [s]",
    "KREIOS:SKIP_DELAY":           "Skip Delay Up/Down",
}
```

## Parameter Lifecycle

```
┌─────────────────────────────────────────────────┐
│ 1. Simulator Starts                             │
│    └─> Loads parameters.dat                     │
│        └─> Creates default values in memory     │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ 2. IOC Connects                                 │
│    └─> GetAllAnalyzerParameterNames             │
│    └─> GetAnalyzerParameterValue (for each)     │
│        └─> Creates EPICS PVs with current values│
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ 3. Runtime Operation                            │
│    └─> User writes to EPICS PV                  │
│        └─> IOC calls SetAnalyzerParameterValue  │
│            └─> Simulator updates in-memory value│
│                └─> IOC reads back to confirm    │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ 4. Simulator Restart                            │
│    └─> In-memory changes LOST                   │
│    └─> Reloads from parameters.dat              │
│    └─> Back to defaults                         │
└─────────────────────────────────────────────────┘
```

## Persistence

**Important**: Parameter changes are **NOT persistent** across simulator restarts.

- Changes via `SetAnalyzerParameterValue` only update in-memory values
- Simulator does NOT write back to `parameters.dat`
- When simulator restarts, all parameters reset to `parameters.dat` defaults

**For the real Prodigy system**: Parameter changes may be persistent depending on the remote experiment configuration in Prodigy.

**For the IOC**: If you need to restore parameter values after restart:
1. Store desired values in IOC database/configuration
2. Re-apply them after connecting to Prodigy/simulator
3. Or: Modify `parameters.dat` directly for permanent defaults

## Adding New Parameters

To add a new parameter to the simulator:

1. **Add to `parameters.dat`**:
   ```
   My New Parameter,double,100.5
   ```

2. **Restart simulator** - it will load the new parameter

3. **Verify** it's available:
   ```
   ?0001 GetAllAnalyzerParameterNames
   !0001 OK: ParameterNames:[..,"My New Parameter"]
   ```

4. **Use it** in your IOC:
   ```python
   resp = client.send_command("GetAnalyzerParameterValue",
                             {"ParameterName": "My New Parameter"})
   # Returns: !0001 OK: Name:"My New Parameter" Value:100.5
   ```

## Protocol Constraints

### When Parameters Can Be Changed

✅ **Allowed States**:
- `idle` - No spectrum defined
- `validated` - Spectrum validated but not started
- `finished` - Acquisition completed
- `aborted` - Acquisition was aborted

❌ **Forbidden States**:
- `running` - Acquisition in progress
- `paused` - Acquisition paused

**Example Error**:
```
?0005 SetAnalyzerParameterValue ParameterName:"Detector Voltage" Value:1900
!0005 Error: 214 Trying to interfere with a running acquisition
```

### Special Parameters

Some parameters affect acquisition behavior:

- **NumNonEnergyChannels**: Changes detector dimensionality (1D→2D)
  - After changing, must re-validate spectrum
- **Detector Voltage**: Critical safety parameter
  - Real Prodigy may enforce ramping limits
  - Simulator accepts any value
- **Skip Delay Up/Down**: Boolean encoded as integer (0/1)

## Testing Parameters

```bash
# Start simulator
python3 ProdigySimServer.py

# In another terminal - test parameter operations
telnet localhost 7010

?0001 Connect
?0002 GetAllAnalyzerParameterNames
?0003 GetAnalyzerParameterValue ParameterName:"Detector Voltage"
?0004 SetAnalyzerParameterValue ParameterName:"Detector Voltage" Value:1850
?0005 GetAnalyzerParameterValue ParameterName:"Detector Voltage"
?0006 Disconnect
```

## Troubleshooting

### "Unknown parameter" error
```
!0001 Error: 206 Unknown parameter "DetectorVoltage".
```
**Solution**: Check exact spelling with spaces - use `GetAllAnalyzerParameterNames` to see available parameters. Parameter names are case-sensitive and must match exactly.

### Cannot set parameter during acquisition
```
!0001 Error: 214 Trying to interfere with a running acquisition
```
**Solution**: Wait for acquisition to finish or abort it first:
```
?0001 Abort
?0002 SetAnalyzerParameterValue ParameterName:"..." Value:...
```

### Parameter not persisting
**Expected behavior**: Parameters reset to `parameters.dat` values on simulator restart. This is intentional - the simulator doesn't modify the file. For permanent changes, edit `parameters.dat` directly.

## Best Practices

1. **Initialize on Connect**: Read all parameters when IOC connects to populate PVs
2. **Validate Before Write**: Check acquisition state before attempting to change parameters
3. **Confirm Changes**: Read back parameter after writing to verify
4. **Document Ranges**: Note safe operating ranges for voltages in your IOC comments
5. **Handle Errors**: Gracefully handle "parameter not found" and "acquisition running" errors
6. **Quote Names**: Always quote parameter names with spaces: `ParameterName:"Detector Voltage"`

## See Also

- **Protocol Spec**: `kreios_ioc/Documentation/SpecsLab_Prodigy_RemoteIn.md` - Section 2.21-2.25
- **Simulator Code**: `ProdigySimServer.py` - `load_device_parameters()`, `cmd_set_parameter_value()`
- **README**: `README.md` - Device Parameters section
- **Test Client**: `test_client.py` - Example parameter queries

---

**File**: `parameters.dat`  
**Format**: CSV (ParameterName, Type, DefaultValue)  
**Encoding**: UTF-8 text  
**Persistence**: Not modified by simulator - defaults only
