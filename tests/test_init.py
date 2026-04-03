"""Tests for Shure Wireless integration setup and teardown."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
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
    mock_client.connect = AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))

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

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, mock_config_entry.entry_id)})

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


async def test_coordinator_heartbeat_connected(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test coordinator heartbeat when connected."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    mock_setup_entry.send_command.assert_awaited()


async def test_coordinator_reconnect_on_disconnect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test coordinator reconnects when connection is lost."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Simulate disconnection
    mock_setup_entry.connected = False

    coordinator = mock_config_entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    mock_setup_entry.connect.assert_awaited()


async def test_coordinator_reconnect_failure(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test coordinator handles failed reconnection."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Simulate disconnection and failed reconnect
    mock_setup_entry.connected = False
    mock_setup_entry.connect = AsyncMock(side_effect=ConnectionRefusedError("Connection refused"))

    coordinator = mock_config_entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is False


async def test_coordinator_heartbeat_error(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test coordinator handles heartbeat command failure."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    mock_setup_entry.send_command = AsyncMock(side_effect=OSError("Connection reset"))

    coordinator = mock_config_entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is False


async def test_callback_triggers_coordinator_update(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test that the client callback triggers a coordinator data update."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # Get the callback that was registered
    callback_func = mock_setup_entry.register_callback.call_args[0][0]

    # Call it (simulates push update from device)
    callback_func()
    await hass.async_block_till_done()

    # Verify coordinator got updated (no error, still successful)
    coordinator = mock_config_entry.runtime_data.coordinator
    assert coordinator.last_update_success is True


async def test_coordinator_logs_reconnect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test coordinator logs when reconnecting after being unavailable."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    coordinator = mock_config_entry.runtime_data.coordinator

    # First, mark as unavailable via heartbeat failure
    mock_setup_entry.send_command = AsyncMock(side_effect=OSError("Connection reset"))
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    # Now restore connection and refresh again
    mock_setup_entry.connected = True
    mock_setup_entry.send_command = AsyncMock()
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert coordinator.last_update_success is True
