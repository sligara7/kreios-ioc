# Kreios-150mm Integration — Findings & Plan

Date: 2025-10-29
Source: repository review (reflow2, Documentation, ioc_deploy), SpecsLab Prodigy docs

## Executive summary
- Goal: Control the new Kreios-150mm detector from an IOC (RHEL VM) and remove the Windows machine from the control path where possible.
- Key finding: SpecsLab Prodigy provides text-based "Remote In" and "Remote Out" protocols (ASCII over TCP/serial) that are suitable for integration. Remote In listens on TCP port 7010 with a request/response protocol; Remote Out can send text to external devices (TCP/UDP/serial).
- Feasibility: Controlling the detector from an IOC is feasible if the Kreios exposes a network/serial text protocol (or if we can create a translator/adapter). If Kreios requires a Windows-only binary driver, we will need a translation layer (Windows agent or a small gateway) or use Prodigy as a bridge.

## Where I looked
- `system_decomposition.md`
- `reflow2/workflows/00-setup.json` and `reflow2/tools/*`
- `Documentation/SpecsLabProdigy_RemoteIn.md` (protocol details)
- `Documentation/LicenseModules/Remote Out.htm`
- `ioc_deploy/` (not executed, identified as the Ansible role for IOC deployment)

## Key protocol & integration details (from Prodigy docs)
- Protocol type: ASCII text-based, request/response over TCP/IP (Prodigy acts as server for Remote In).
- Port: default TCP 7010.
- Message framing: newline-terminated; requests start with '?' + 4-hex request id; responses start with '!' + id; responses are `OK`, `OK: [...]`, or `Error: <code> "message"`.
- Connection model: single-connection server (Prodigy only accepts one client at a time).
- Remote Out: Prodigy can send text commands to external devices via TCP/UDP/serial — useful to adapt devices that speak text protocols.

## Concrete next actions (short, prioritized)
1. Deploy the IOC VM using the existing `ioc_deploy` Ansible role.
   - Acceptance: IOC VM accessible via SSH; Python3 installed; firewall rules allow outbound TCP/serial connectivity to device or Prodigy.
2. Identify Kreios device control interface (ask vendor / check device docs):
   - Does Kreios support TCP or serial ASCII commands? If yes, obtain full command set.
   - If Kreios only has a Windows SDK/API, collect SDK docs and decide adapter approach.
3. Prototype a control client on the IOC:
   - If Kreios is text/TCP/serial: implement a Python client (socket or pyserial) implementing connect/command/response with timeout/retries.
   - If Kreios is Windows-only: prototype a small Windows agent that exposes a text-over-TCP wrapper; alternatively, configure Prodigy `Remote Out` to bridge commands.
4. Test integration scenarios:
   - Basic connectivity and status query.
   - Start/stop acquisition.
   - Acquire and transfer one spectrum (m x n array) and verify file/stream handling.
5. Capture results in reflow context and iterate: use `reflow2` tools to record work products, artifacts, and next steps.

## Repository/automation tasks I recommend now (I can create these):
- Add a short integration summary artifact (created here at `reflow2/context/00-kreios-integration-summary.md`).
- Add a small Python client stub and tests (e.g., `tools/kreios_stub.py`) to accelerate prototyping once protocol is available.
- Add a CI workflow to run lint/tests on push/PR; helps maintain quality while we add prototypes.

## Minimal developer contract (2–4 bullets)
- Inputs: device protocol (text commands) or vendor SDK; an IOC VM with network/serial access; Prodigy server (optional).
- Outputs: a Python client/service running on the IOC capable of sending device commands and handling responses; integration test that performs a single acquisition.
- Error modes: connection refused/timeouts; malformed or undocumented commands; Prodigy single-connection limitation; device access/permissions.
- Success criteria: IOC can trigger a detector acquisition and retrieve at least one spectrum (validated by data shape and content).

## Edge cases & risks
- Kreios requires proprietary Windows-only drivers/SDK — adds complexity; mitigations: Windows agent, hardware gateway, or use Prodigy as intermediary.
- Single-connection server (Prodigy) — if Prodigy remains in the loop, design the client to be the sole connection or add a multiplexing gateway.
- Network reliability/timeouts — implement robust retry and state query commands.
- Data volume/format — ensure acquisition data (m x n arrays) can be reliably transferred and parsed (binary vs ASCII). Current Prodigy RemoteIn docs note no binary transfer in early version; check full docs for large array transfer method.

## Files I created / will create
- `reflow2/context/00-kreios-integration-summary.md` — this file (findings, plan, contract, checklist).
- Next (I can add on your confirmation): `tools/kreios_stub.py` (python stub client) and a small test under `tests/`.

## Quick commands to run on the IOC (suggested)
Run reflow directory validation and bootstrap (optional; run inside repo root):

```bash
python3 reflow2/tools/validate_directory_structure.py .
python3 reflow2/tools/bootstrap_development_context.py kreios_integration --system-path=reflow2/context
```

(These create tracking artifacts used by the reflow process; I did not execute them here.)

## Information still needed from you or the environment
- Does the Kreios-150mm have a documented control protocol (TCP/serial ASCII, or another documented API)? If yes, please attach or provide the docs.
- Will Prodigy remain in the control path, or do we aim to connect directly from the IOC to the Kreios hardware?
- Access to a test device (or recorded sample command traces) so I can implement and validate the client.

## Acceptance / next handoff
- If you want, I will: 
  - Add the Python stub and a basic unit test.
  - Add the CI workflow to run lint/tests.
  - Run `bootstrap_development_context.py` to create reflow tracking artifacts in `reflow2/context/`.

If you confirm which of the above to proceed with, I'll implement it next.

---

*End of summary.*
