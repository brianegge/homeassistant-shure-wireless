"""Tests for Shure Wireless integration setup and teardown."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shure_wireless import ShureRuntimeData
from custom_components.shure_wireless.const import DOMAIN

from .conftest import make_mock_client


async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test successful setup of a config entry."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert isinstance(mock_config_entry.runtime_data, ShureRuntimeData)
    assert mock_config_entry.runtime_data.client is mock_setup_entry
    assert mock_config_entry.runtime_data.coordinator is not None


async def test_setup_entry_connection_refused(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup retries when connection is refused."""
    mock_client = make_mock_client(connected=False)
    mock_client.connect = AsyncMock(
        side_effect=ConnectionRefusedError("Connection refused")
    )

    with patch(
        "custom_components.shure_wireless.ShureClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_generic_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test setup retries on generic connection error."""
    mock_client = make_mock_client(connected=False)
    mock_client.connect = AsyncMock(side_effect=OSError("Network unreachable"))

    with patch(
        "custom_components.shure_wireless.ShureClient",
        return_value=mock_client,
    ):
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test successful unload of a config entry."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    mock_setup_entry.disconnect.assert_awaited_once()


async def test_setup_registers_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test that setup registers the receiver as a device."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    from homeassistant.helpers import device_registry as dr

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(
        identifiers={(DOMAIN, mock_config_entry.entry_id)}
    )

    assert device is not None
    assert device.manufacturer == "Shure"
    assert "SLXD4DE" in device.model
    assert device.sw_version == "2.5.1"


async def test_setup_registers_callback(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test that setup registers an update callback on the client."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    mock_setup_entry.register_callback.assert_called_once()
