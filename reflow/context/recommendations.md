# Kreios-150mm Integration — Recommendations

Date: 2025-10-29
Source: repository review (specs tree, Prodigy binaries, Prodigy Remote In documentation), `reflow2/context/00-kreios-integration-summary.md`

## Executive summary

We reviewed the local Prodigy distribution and its Remote In/Remote Out documentation. The key recommendations below present the most practical approaches to integrate the Kreios-150mm detector with an IOC running on a Linux VM, prioritized by how well they meet the goal of removing Windows from the control path.

## Findings (short)
- SpecsLab Prodigy supports a text-based Remote In protocol (ASCII over TCP, port 7010) that is well-documented and usable by a Linux-based client.
- The local distribution is Windows-native (many EXE/DLL files in `Bin_x64`), and includes helper tools such as `SerialPortBridge.exe`, `RemoteOutTemplate.exe`, and device-specific DLLs.
- Release notes indicate KREIOS support exists in Prodigy; device definition/config files likely exist under the `database` folder in the Prodigy tree.

## Recommendation summary (priority order)
1. Direct Linux IOC client (preferred)
   - If the Kreios device exposes a TCP or serial ASCII protocol (or vendor can provide such documentation), implement a Python client on the IOC VM to control the device directly.
   - Benefits: removes Windows entirely; simplest architecture; maintainable on Linux.

2. Windows adapter/gateway (if Windows-only SDK/driver required)
   - If Kreios requires a Windows SDK or vendor DLL, implement a small Windows service that wraps minimal device functionality and exposes a text-over-TCP API that the IOC VM can call.
   - Benefits: isolates vendor binary code to Windows; allows Linux IOC to remain the control plane.

3. Use Prodigy as a bridge (last resort)
   - Use Prodigy `Remote Out` or its templates to send device commands, and `Remote In` to control Prodigy programmatically. This keeps Windows in the loop but can be used when immediate integration is required and other options are not available.
   - Benefits: fastest to begin if the Windows machine and Prodigy are already available; leverages existing tools like `SerialPortBridge`.

## Technical details & rationale
- Remote In protocol is request/response ASCII (requests `?id Command ...`, responses `!id OK/OK:[...] / Error:`). This maps cleanly to a Python socket client or a small stateful wrapper.
- Remote Out supports TCP/UDP/Serial and can forward text commands to the Kreios if Prodigy is used as the gateway; Prodigy ships templates and helper tools that likely allow configuration for the Kreios command format.
- `Bin_x64` reveals Windows-only executables and DLLs. Running Prodigy on Linux would require heavy porting or Wine-level emulation (not recommended for production). Accordingly, removing Windows from the control path means avoiding any reliance on the supplied binaries for run-time control.

## Required information before full implementation
- Device protocol: Obtain Kreios-150mm control protocol documentation (TCP/serial text format and examples), or an SDK. If vendor SDK exists, request documentation for programmatic integration and whether a CLI example can be provided.
- Sample dataset: a sample acquisition data dump (or recorded `GetAcquisitionData` response from Prodigy) to verify expected shapes and parsing logic for m×n arrays.
- Confirm constraints: whether the lab will permit the detector to be directly connected to the IOC VM network or whether the Windows machine will remain the only possible physical host.

## Concrete next steps (short-term tasks)
1. Search repository for KREIOS device definitions and share any files found (I can run this now and return exact file paths and snippets).
2. Ask vendor for device protocol or SDK (serial protocol, TCP commands, or Windows SDK/COM API). Provide vendor the minimal list of operations we'll need (status, start/stop acquisition, read data, set parameters).
3. If protocol is text/TCP/serial: implement `tools/kreios_client.py` (Python), add unit tests and a small demo script to fetch a status and a small dataset. Include timeouts and retry logic.
4. If Windows SDK required: design a minimal Windows gateway (C#/Python) that exposes a secured text-over-TCP API (simple JSON or ASCII commands) implementing the small contract described below.

## Minimal developer contract (for the client/gateway)
- Inputs: text-based commands (status, define spectrum, start, get data), connection info (host:port or serial port), timeouts.
- Outputs: parsed structured responses (status object, arrays of acquisition data, error codes/messages).
- Error modes: connection refused/timeouts, malformed responses, device busy, incomplete acquisition data.
- Success criterion: reproducibly trigger one acquisition and retrieve a valid m×n array that matches a supplied sample (or the Prodigy remote response example).

## Implementation sketch (Linux client)
- Language: Python 3
- Dependencies: standard library (socket), optional `pyserial` for serial devices, `pytest` for tests.
- Modules:
  - `kreios_client.py` — connect(), send_request(cmd, params), parse_reply(), get_acquisition_data(from_idx, to_idx)
  - `examples/` — small demo script: query status, define a simple spectrum, start and fetch first N points.
  - `tests/test_kreios_client.py` — socket/serial mocking of expected replies.

## Gateway sketch (Windows-only SDK case)
- Language options: C#/.NET or Python (via pythonnet or vendor-provided bindings)
- Expose: minimal ASCII-over-TCP API compatible with Remote In style (or simple JSON) that the Linux IOC can call.
- Keep the gateway small: only wrap required device functions to reduce attack surface and maintenance.

## Tests and CI
- Add `pytest` tests mocking the device for the client library.
- Add a lightweight CI workflow (GitHub Actions or local) to run linting (flake8) and `pytest` on push/PR.

## Operational & deployment notes
- Run the client/gateway under systemd on the IOC VM and create a health-check endpoint or use the EPICS IOC monitoring capabilities.
- Implement robust logging and retries; capture raw packet logs during development for debugging.
- If using Prodigy in the loop, ensure only the IOC client holds the single Remote In connection, and offer multiplexing if multiple tools need to access Prodigy.

## Risks & mitigations
- Vendor SDK dependence — mitigate with a gateway or keep Windows machine for device-specific tasks.
- Large data transfer performance — benchmark `GetAcquisitionData` and consider file-based handoff if needed.
- Single-client limitation of Prodigy — prefer direct device integration to avoid it, or implement a multiplexer service.

## Suggested immediate tasks I can perform for you
- Search for KREIOS templates and device-definition files in the Prodigy `database/` and return their paths and snippets (I can run this right away).
- Create the initial `tools/kreios_client.py` stub + unit tests and CI skeleton.

---

If you want me to proceed, tell me which of the immediate tasks to perform next (search for KREIOS config, or scaffold the Python client and tests).