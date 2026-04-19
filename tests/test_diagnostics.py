"""Tests for Shure Wireless diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_diagnostics(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test diagnostics returns expected data."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    from custom_components.shure_wireless.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)

    assert "config_entry" in result
    assert "receiver" in result
    assert "connection" in result
    assert "channels" in result
    assert "coordinator" in result
    assert "devices" in result

    # Verify sensitive data is redacted
    assert result["config_entry"]["data"]["host"] == "**REDACTED**"
    assert result["receiver"]["device_id"] == "**REDACTED**"
    assert result["config_entry"]["unique_id"] == "**REDACTED**"

    # Verify non-sensitive data is present
    assert result["receiver"]["model"] == "SLXD4DE"
    assert result["receiver"]["firmware_version"] == "2.5.1"
    assert result["connection"]["port"] == 2202
    assert result["coordinator"]["last_update_success"] is True

    # Verify channel data
    assert "1" in result["channels"]
    ch1 = result["channels"]["1"]
    assert ch1["name"] == "Mic 1"
    assert ch1["tx_device_id"] == "**REDACTED**"
    assert ch1["battery_charge"] == 75
