"""
Bluesky RunEngine setup for KREIOS profile.

Sets up the RunEngine with standard callbacks for data collection,
then creates and connects the KREIOS ophyd-async devices.
"""
print(f"Loading file {__file__!r} ...")

from bluesky.callbacks.best_effort import BestEffortCallback
from bluesky.run_engine import RunEngine, autoawait_in_bluesky_event_loop

# Create RunEngine and configure IPython to use its event loop
RE = RunEngine(call_returns_result=True)
autoawait_in_bluesky_event_loop()

# Add best-effort callback for live plotting/printing
bec = BestEffortCallback()
RE.subscribe(bec)

# Import standard plans
import bluesky.plans as bp
import bluesky.plan_stubs as bps

print("  RunEngine created: RE")
print("  BestEffortCallback subscribed")
print("  Standard plans imported: bp, bps")

# Create and connect KREIOS devices on the RunEngine's event loop
print(f"  Connecting KREIOS devices to {KREIOS_PREFIX} ...")
try:
    with init_devices():
        kreios = KreiosDetector(KREIOS_PREFIX, name="kreios")
        kreios_spectrum = KreiosSpectrum(KREIOS_PREFIX, name="kreios_spectrum")
        kreios_image = KreiosImage(KREIOS_PREFIX, name="kreios_image")
    print("    kreios connected")
    print("    kreios_spectrum connected")
    print("    kreios_image connected")
except Exception as e:
    print(f"    WARNING: Could not connect KREIOS devices: {e}")
    print("    Creating devices without connection (connect manually later):")
    print("      await kreios.connect()")
    kreios = KreiosDetector(KREIOS_PREFIX, name="kreios")
    kreios_spectrum = KreiosSpectrum(KREIOS_PREFIX, name="kreios_spectrum")
    kreios_image = KreiosImage(KREIOS_PREFIX, name="kreios_image")

print()
