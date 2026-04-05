"""Constants for the Shure Wireless integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "shure_wireless"

DEFAULT_PORT: Final = 2202

HEARTBEAT_INTERVAL: Final = 60

PLATFORMS: Final[list[str]] = ["binary_sensor", "button", "number", "sensor", "switch"]
