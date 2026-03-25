"""Fixtures for Shure Wireless tests."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# Mock homeassistant modules so we can import shure_client without HA installed
_ha_modules = [
    "homeassistant",
    "homeassistant.config_entries",
    "homeassistant.core",
    "homeassistant.exceptions",
    "homeassistant.helpers",
    "homeassistant.helpers.device_registry",
    "homeassistant.helpers.update_coordinator",
    "homeassistant.components",
    "homeassistant.components.sensor",
    "homeassistant.const",
    "homeassistant.helpers.entity_platform",
    "voluptuous",
]

for mod in _ha_modules:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()


from custom_components.shure_wireless.shure_client import (  # noqa: E402
    ChannelState,
    ReceiverState,
    ShureClient,
)


@pytest.fixture
def mock_client() -> ShureClient:
    """Return a ShureClient with mocked connection."""
    client = ShureClient("192.168.1.100", 2202, num_channels=1)
    client._connected = True
    client.receiver = ReceiverState(
        device_id="SLXD4-001",
        firmware_version="1.2.3",
        model="SLXD4",
        rf_band="G58",
    )
    client.channels[1] = ChannelState(
        name="Mic 1",
        frequency="470.125",
        audio_level=-30,
        audio_level_peak=-25,
        rf_level=-50,
        antenna="AB",
        battery_charge=75,
        battery_bars=4,
        battery_runtime=120,
        battery_type="LITHIUM_ION",
        tx_model="SLXD1",
        tx_device_id="TX-001",
    )
    return client
