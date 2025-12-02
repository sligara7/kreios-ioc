# IOC → Windows (Prodigy) → KREIOS-150 Integration (Prodigy Bridge)

Goal: use an IOC on a RHEL VM to control the Kreios-150 detector via the Prodigy installation running on a Windows machine. This path accepts Windows in the runtime path but minimizes Windows-dependence for higher-level control.

## High-level overview
- The RHEL-hosted IOC uses the Prodigy `Remote In` protocol to control an instance of SpecsLab Prodigy running on a Windows machine.
- Prodigy handles the low-level hardware interaction with the Kreios device using its Windows-native drivers and `SerialPortBridge`/`Remote Out` mechanisms.
- The IOC is the single Remote In client (or a gateway service on Linux that holds the connection and multiplexes local users), ensuring Prodigy’s single-connection limitation is respected.

## Preconditions / required information
1. Windows machine with Prodigy installed and configured to control the Kreios device.
2. Network connectivity: RHEL VM can reach the Windows host on TCP port 7010 (Prodigy Remote In) and Windows host can reach Kreios hardware via serial/TCP as configured.
3. Access to Prodigy configuration: the Prodigy HSA/KREIOS config files already present in the Prodigy database will be used to determine parameter mappings.

## Minimal developer contract
- Inputs: Windows host IP, Prodigy Remote In port (7010), parameter mappings (from `HsaConfig`), and device connectivity info.
- Outputs: EPICS PVs on the Linux side that reflect Prodigy/device state and allow control commands to be issued.
- Success Criteria: IOC can initiate an acquisition via Remote In, poll status, and fetch acquisition data that matches expected shapes.

## Implementation steps (detailed)
1. Configure Prodigy
   - Ensure Prodigy on Windows has a Remote Control configuration that exposes the experiment template you want to run (e.g., KREIOS spectrum template).
   - Validate that Prodigy can talk to the Kreios hardware locally (run a manual acquisition from Prodigy).
2. Implement Linux Remote In client
   - `tools/prodigy_client.py` (Python): implement the Remote In request/response protocol (socket client with `?id Command` framing, parse `!id` replies, handle OK/OK:[...] and Error codes).
   - Implement helper functions: connect(), disconnect(), define_spectrum(...), validate_spectrum(), start(), get_acquisition_status(), get_acquisition_data(from,to).
3. Multiplexing/Single-connection handling
   - The IOC should be the single Remote In client. If multiple users/tools need access, run a small proxy (on Linux) that holds the single connection and exposes a local API (HTTP/JSON or socket) to local clients.
   - The proxy enforces single-client semantics and serializes requests to Prodigy.
4. EPICS IOC integration
   - Wrap the `prodigy_client` in the IOC driver (caproto or EPICS classic). Export PVs for high-level operations (start/stop, param setting, status, data retrieval).
5. Testing
   - Unit tests for `prodigy_client` parsing and request framing (mock socket server to respond with example `!id` replies from the Remote In doc).
   - Integration test: run the proxy + prodigy_client against a test Prodigy instance (if available) or a simulator that emulates Prodigy’s Remote In replies.
6. Deployment
   - Run the Linux proxy/IOC under `systemd` with supervised restart. Ensure logs and debugging capture raw requests/replies for troubleshooting.

## Operational considerations and optimizations
- Connection ownership: ensure the proxy holds the Remote In connection permanently or implements robust reconnect logic after reboots or network blips.
- Minimize Windows exposure: restrict the Windows host so it's only reachable by the IOC/proxy and the device network; keep Prodigy updates and maintenance under controlled change windows.
- Data handling: for very large datasets, make sure you chunk requests and avoid blocking the Remote In socket for excessive periods; `GetAcquisitionData FromIndex:ToIndex` supports slicing.

## Pros
- Leverages existing Prodigy drivers and templates; minimal driver work required.
- Faster to get working if Prodigy is already configured and the Windows machine is available.
- Useful when vendor drivers are Windows-only.

## Cons / Risks
- Windows remains in the runtime data/control path.
- Single-connection limitation in Prodigy requires careful design (proxy recommended).
- Slightly more complex architecture and extra network hops.

## Security & operational notes
- Protect the Prodigy Remote In port with a firewall so only the IOC/proxy can connect.
- Log all Remote In activity for audit and debugging.
- Use ACLs or network-level isolation so only authorized systems can talk to the Windows Prodigy host.

## Next steps (if chosen)
1. Implement `tools/prodigy_client.py` and unit tests.
2. Create a small Linux proxy service that holds the single Remote In connection and exposes a simple HTTP/JSON API for local use.
3. Map Prodigy parameter names to IOC PV names using the HSA config files (I can parse and produce this mapping).

---

## Implementation details — concrete

This section gives a concrete, runnable implementation plan and example artifacts you can use to deploy the IOC → Prodigy → KREIOS bridge in the lab. The ideas below are intentionally pragmatic and minimal to get a reliable, maintainable setup.

Components
 - `tools/prodigy_client.py` (library): already implemented; low-level Remote In request/response handling.
 - `tools/prodigy_proxy.py` (service): long-running proxy which holds one TCP connection to Prodigy, serializes requests, and exposes a small HTTP/JSON API to local consumers (the IOC and admin tools).
 - `ioc/` or `caproto_ioc/`: thin IOC glue that calls the local proxy API to implement PVs.
 - `tests/`: unit tests and an integration test that runs the proxy and a mock Prodigy server.

Data flow (runtime)
 1. Proxy starts on RHEL VM and connects to Windows:7010 (Prodigy Remote In).
 2. Proxy keeps a single open socket to Prodigy and accepts local HTTP requests from the IOC.
 3. A request like POST /start -> proxy -> proxy uses `prodigy_client.send_command('Start')` -> Prodigy executes and returns OK -> proxy maps the reply to JSON and returns to the caller.
 4. For large acquisition data, the IOC calls GET /data?from=0&to=99 and the proxy requests `GetAcquisitionData FromIndex:0 ToIndex:99` and streams or returns a chunked JSON response.

Proxy API (suggested minimal endpoints)
 - POST /connect {"host": "10.0.0.5", "port":7010} — instruct proxy to connect (or reconfigure target)
 - POST /disconnect — close connection
 - GET /status — returns connection and last-known controller status
 - POST /cmd {"command":"GetAcquisitionStatus"} — sends arbitrary Remote In command and returns parsed reply
 - POST /start {"SetSafeStateAfter": "true"} — convenience helper to start
 - GET /data?from=0&to=99 — get slice of acquisition data

Proxy behavior details
 - Request queue: proxy accepts local requests and enqueues them; only one request is in-flight to Prodigy at any time.
 - Timeouts & retries: for every outgoing request to Prodigy, use a configurable timeout (default 10s) and a retry policy (3 attempts, exponential backoff).
 - Reconnect: if connection fails, attempt reconnect with linear or exponential backoff; expose status via /status and push logs.
 - Logging: JSON structured logs to stdout/stderr so `journalctl` captures them; include raw request and reply (configurable with a low/normal/high verbosity level to avoid leaking secrets).

Example systemd unit for the proxy
Place this at `/etc/systemd/system/kreios-proxy.service` on the RHEL VM (adjust paths and user/group):

[Unit]
Description=Kreios Prodigy RemoteIn Proxy
After=network.target

[Service]
User=kreios
Group=kreios
WorkingDirectory=/opt/kreios
ExecStart=/opt/kreios/.venv/bin/python /opt/kreios/tools/prodigy_proxy.py --listen 127.0.0.1:5000 --prod-host 10.0.0.5 --prod-port 7010
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target

Example usage of `prodigy_client` (Python REPL snippet)
```python
from tools.prodigy_client import ProdigyClient
cli = ProdigyClient('10.0.0.5', 7010)
cli.connect()
print(cli.send_command('Connect'))
print(cli.send_command('GetAcquisitionStatus'))
print(cli.send_command('GetAcquisitionData', {'FromIndex':0, 'ToIndex':9}))
cli.disconnect()
```

Security and firewall notes
 - On Windows: allow inbound TCP 7010 only from the RHEL VM's IP. (Minimal attack surface.)
 - On RHEL VM: run the proxy bound to localhost (127.0.0.1) so only local services can call it; expose the proxy to other machines only if you add authentication+TLS.

Deployment checklist (RHEL VM)
1. Create service account and application directory:
   - sudo useradd -r -s /sbin/nologin kreios
   - sudo mkdir -p /opt/kreios && sudo chown kreios:kreios /opt/kreios
2. Copy repository files into /opt/kreios (or git clone) and create virtualenv:
   - python3 -m venv /opt/kreios/.venv
   - /opt/kreios/.venv/bin/pip install -r requirements-dev.txt
3. Configure systemd unit (see above) and enable/start it:
   - sudo systemctl daemon-reload
   - sudo systemctl enable --now kreios-proxy.service
4. Test connectivity from the VM:
   - nc -vz <WINDOWS_IP> 7010
   - curl localhost:5000/status
5. Run quick connect test with the proxy: POST /connect (or let systemd start with configured args)

Tests
 - Unit tests: keep the mock Prodigy server used in `tests/test_prodigy_client.py` to validate the low-level client.
 - Proxy tests: write unit tests that spawn the proxy with a mock prodigy server and assert the HTTP API returns expected JSON for start/status/data.
 - Integration test: when Windows/Prodigy are networked, run the end-to-end scenario: proxy -> windows -> hardware. Capture raw logs and at least one full acquisition.

Parameter mapping & calibration data
 - Use the HSA config and lensdata files in the Prodigy distribution (e.g., files under `SpecsLab Prodigy/database/HsaConfig` like `Hsa3500CCDKreiosConfig.*` and `KREIOS 150.lensdata`) to map logical parameter names to the IOC PV names and units.
 - Example quick grep to locate KREIOS files:
   - `ls "SpecsLab Prodigy/database/HsaConfig" | grep -i kreios`

Operational runbook (short)
 - If proxy reports connection errors: check `nc` from VM to Windows:7010. Restart proxy after Windows maintenance.
 - If `GetAcquisitionData` returns fewer points than expected: query `GetAcquisitionStatus` to confirm NumberOfAcquiredPoints and request a slice only for valid indices.
 - For prolonged acquisitions, poll `GetAcquisitionStatus` periodically rather than blocking on `GetAcquisitionData`.

Notes about future improvements
 - Add authentication (JWT or mTLS) to the proxy if it must be exposed beyond localhost.
 - Add a small web UI for test-triggered acquisitions and basic plotting (optional).
 - Implement request/response persistence for auditing (store raw requests/replies for troubleshooting).
