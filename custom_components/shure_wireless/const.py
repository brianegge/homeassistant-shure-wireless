"""Constants for the Shure Wireless integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "shure_wireless"

DEFAULT_PORT: Final = 2202

HEARTBEAT_INTERVAL: Final = 60

# A receiver that loses power never closes its TCP connection, and writes to it
# keep "succeeding" until the kernel gives up retransmitting (about 15 minutes).
# A live receiver answers every heartbeat's GETs and pushes a SAMPLE every 30 s,
# so silence for two heartbeats means it is gone.
STALE_TIMEOUT: Final = 2 * HEARTBEAT_INTERVAL

PLATFORMS: Final[list[str]] = ["binary_sensor", "button", "number", "sensor", "switch"]
