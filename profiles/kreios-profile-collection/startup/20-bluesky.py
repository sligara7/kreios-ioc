"""
Bluesky RunEngine setup for KREIOS profile.

Sets up the RunEngine with standard callbacks for data collection.
"""
print(f"Loading file {__file__!r} ...")

from bluesky import RunEngine
from bluesky.callbacks.best_effort import BestEffortCallback

# Create RunEngine
RE = RunEngine({})

# Add best-effort callback for live plotting/printing
bec = BestEffortCallback()
RE.subscribe(bec)

# Import standard plans
import bluesky.plans as bp
import bluesky.plan_stubs as bps

print("  RunEngine created: RE")
print("  BestEffortCallback subscribed")
print("  Standard plans imported: bp, bps")
print()
