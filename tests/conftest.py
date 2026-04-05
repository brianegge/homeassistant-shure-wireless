"""Shared fixtures for Shure Wireless tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import loader
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shure_wireless.const import DEFAULT_PORT, DOMAIN
from custom_components.shure_wireless.shure_client import (
    ChannelState,
    ReceiverState,
    ShureClient,
)

MOCK_HOST = "shure-receiver.local"
MOCK_PORT = DEFAULT_PORT
MOCK_NUM_CHANNELS = 2

MOCK_CONFIG = {
    "host": MOCK_HOST,
    "port": MOCK_PORT,
    "num_channels": MOCK_NUM_CHANNELS,
}

MOCK_DEVICE_ID = "SLXD4DE-001"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass: HomeAssistant) -> None:
    """Enable custom integrations in all tests."""
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS)


def make_mock_client(
    *,
    host: str = MOCK_HOST,
    port: int = MOCK_PORT,
    num_channels: int = MOCK_NUM_CHANNELS,
    connected: bool = True,
) -> MagicMock:
    """Create a mock ShureClient with realistic state."""
    client = MagicMock(spec=ShureClient)
    client.host = host
    client.port = port
    client.num_channels = num_channels
    client._connected = connected
    client.connected = connected

    client.receiver = ReceiverState(
        device_id=MOCK_DEVICE_ID,
        firmware_version="2.5.1",
        model="SLXD4DE",
        rf_band="G58",
        encryption="OFF",
        lock_status="UNLOCKED",
    )

    client.channels = {}
    for ch in range(1, num_channels + 1):
        client.channels[ch] = ChannelState(
            name=f"Mic {ch}",
            frequency="470.125",
            audio_level=-30,
            audio_level_peak=-25,
            rf_level=-50,
            antenna="AB",
            battery_charge=75,
            battery_bars=4,
            battery_runtime=120,
            battery_type="LITHIUM_ION",
            battery_health=95,
            battery_cycle=50,
            battery_temp_c=25,
            tx_model="SLXD1",
            tx_device_id=f"TX-00{ch}",
            tx_mute_status="OFF",
            audio_gain=12,
            audio_mute="OFF",
            interference_status="NONE",
            encryption_status="OK",
            fd_mode="ON",
        )

    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.send_command = AsyncMock()
    client.register_callback = MagicMock(return_value=MagicMock())

    return client


@pytest.fixture
def mock_client() -> MagicMock:
    """Return a mock ShureClient."""
    return make_mock_client()


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create and add a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Shure SLXD4DE ({MOCK_HOST})",
        data=MOCK_CONFIG.copy(),
        unique_id=MOCK_DEVICE_ID,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_setup_entry(mock_client: MagicMock):
    """Mock ShureClient for integration setup."""
    with patch(
        "custom_components.shure_wireless.ShureClient",
        return_value=mock_client,
    ):
        yield mock_client
