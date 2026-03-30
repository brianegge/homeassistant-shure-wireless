"""Tests for Shure Wireless diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shure_wireless.const import DOMAIN
from custom_components.shure_wireless.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import MOCK_HOST, MOCK_PORT, make_mock_client


async def test_diagnostics(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test diagnostics returns expected structure."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    # Check top-level structure
    assert "config_entry" in result
    assert "receiver" in result
    assert "connection" in result
    assert "channels" in result
    assert "coordinator" in result

    # Config entry data - host and unique_id should be redacted
    assert result["config_entry"]["data"]["host"] == "**REDACTED**"
    assert result["config_entry"]["data"]["port"] == MOCK_PORT
    assert result["config_entry"]["unique_id"] == "**REDACTED**"

    # Receiver info - device_id should be redacted
    assert result["receiver"]["model"] == "SLXD4DE"
    assert result["receiver"]["firmware_version"] == "2.5.1"
    assert result["receiver"]["rf_band"] == "G58"
    assert result["receiver"]["device_id"] == "**REDACTED**"

    # Connection info - host should be redacted
    assert result["connection"]["host"] == "**REDACTED**"
    assert result["connection"]["port"] == MOCK_PORT
    assert result["connection"]["connected"] is True
    assert result["connection"]["num_channels"] == 2

    # Channels - tx_device_id should be redacted
    assert "1" in result["channels"]
    assert "2" in result["channels"]
    ch1 = result["channels"]["1"]
    assert ch1["name"] == "Mic 1"
    assert ch1["frequency"] == "470.125"
    assert ch1["battery_charge"] == 75
    assert ch1["rf_level"] == -50
    assert ch1["tx_model"] == "SLXD1"
    assert ch1["tx_device_id"] == "**REDACTED**"
    assert ch1["battery_health"] == 95

    ch2 = result["channels"]["2"]
    assert ch2["name"] == "Mic 2"
    assert ch2["tx_device_id"] == "**REDACTED**"

    # Coordinator
    assert "last_update_success" in result["coordinator"]


async def test_diagnostics_single_channel(
    hass: HomeAssistant,
) -> None:
    """Test diagnostics with a single-channel receiver."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Shure SLXD4 ({MOCK_HOST})",
        data={
            "host": MOCK_HOST,
            "port": MOCK_PORT,
            "num_channels": 1,
        },
        unique_id="SLXD4-SINGLE",
    )
    entry.add_to_hass(hass)

    mock_client = make_mock_client(num_channels=1)

    with patch(
        "custom_components.shure_wireless.ShureClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    result = await async_get_config_entry_diagnostics(hass, entry)

    assert len(result["channels"]) == 1
    assert "1" in result["channels"]
    assert result["connection"]["num_channels"] == 1
