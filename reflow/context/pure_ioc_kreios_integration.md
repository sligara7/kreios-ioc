# Pure IOC (RHEL VM) → KREIOS-150 Integration

Goal: run an IOC on a RHEL VM that communicates directly with the KREIOS-150 detector (no Windows or Prodigy in the runtime control path).

Status: exploratory — feasible if the KREIOS device exposes a standard network or serial control API, or the vendor provides a documented protocol or CLI.

## High-level overview
- IOC (EPICS softIOC or equivalent) runs on RHEL VM.
- Python-based device client/service on the VM implements the Kreios command set (TCP or serial) to control the detector and retrieve spectra.
- The IOC driver wraps the client and exports EPICS PVs for control and data acquisition to the control system.

## Preconditions / required information
1. Kreios control protocol: must obtain either
   - ASCII-over-TCP or ASCII-over-serial protocol (command/response), or
   - A vendor CLI or network API, or
   - SDK documentation and permission to integrate.
2. Physical connectivity: detector reachable from the RHEL VM (Ethernet or serial path). If only a USB/PCI interface with Windows drivers exists, this approach is not viable without additional gateway hardware.
3. Sample acquisition data or specs: example acquisition payloads (m×n arrays), expected sizes, and units.

## Minimal developer contract (pure IOC)
- Inputs: host:port or serial device path; commands: status, define spectrum, start, pause/resume, get data; timeouts.
- Outputs: structured JSON or Python objects containing status, parameter values, and acquisition arrays.
- Success criteria: trigger an acquisition and retrieve a spectrum of the expected shape and values.

## Implementation steps (detailed)
1. Vendor protocol confirmation
   - Ask vendor for protocol docs or SDK. Request minimal example scripts to run status and read data.
2. Prototype low-level client
   - `tools/kreios_client.py` (Python): implement connect(), send(cmd, params), recv(), parse_reply().
   - Support both TCP sockets and `pyserial` for serial devices.
   - Implement logging and a `--dry-run` mode that reads canned responses for testing.
3. Unit tests
   - `tests/test_kreios_client.py` using pytest and socket/serial mocking.
4. Define a small API wrapper for IOC
   - `kreios_ioc_adapter.py` exposes functions: get_status(), set_params(dict), start_acq(), get_data(from,to).
   - Map logical parameters from Prodigy HSA configs (I can produce a mapping doc from `HsaConfig` files) to client commands.
5. EPICS IOC integration
   - Option A: EPICS softIOC with Python support (caput/caget wrappers) or a simple process variable layer using caproto.
   - Option B: Use ASYN interface and write a custom driver if using classic EPICS base.
6. Integration tests
   - Integration test that runs the client against a simulated Kreios (TCP echo server) and validates a complete acquisition path.
7. Deployment
   - Package as a systemd service with environment configuration (connection parameters, retries, logging path).
   - Add health-check endpoint (HTTP or simple status PV).

## Edge cases & error handling
- Device busy or long acquisition: implement asynchronous operations with polling and a bounded timeout.
- Partial reads: implement reattempts and a data integrity check (point counts, checksum if provided).
- Network reliability: exponential backoff and a limited number of retries.

## Tests & validation
- Unit tests for parsing and request/response handling.
- A small simulated server that returns sample `GetAcquisitionData` responses.
- Smoke test to validate EPICS PVs: set parameters, start, poll status, fetch data.

## Pros
- Removes Windows from the runtime path.
- Easier to maintain and deploy within a Linux-based control environment.
- Avoids the Prodigy single-connection limitation and Windows driver issues.

## Cons / Risks
- If vendor only supplies Windows drivers/SDK, this approach requires vendor cooperation or low-level driver reverse engineering (time-consuming and potentially legally restricted).
- Device-specific quirks may require low-level knowledge that only vendor software exposes.

## Next steps
- Get Kreios protocol docs or vendor sample scripts.
- I can scaffold `tools/kreios_client.py`, unit tests, and a simulated server for development once you confirm.