"""Tests for Shure Wireless sensor platform."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shure_wireless.shure_client import ChannelState


def _get_entity_id(hass: HomeAssistant, unique_id_suffix: str, entry_id: str) -> str:
    """Look up entity_id by unique_id pattern."""
    entity_registry = er.async_get(hass)
    target_uid = f"{entry_id}_{unique_id_suffix}"
    for entity in entity_registry.entities.values():
        if entity.unique_id == target_uid:
            return entity.entity_id
    raise AssertionError(f"Entity with unique_id '{target_uid}' not found")


async def test_battery_level_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test battery level sensor reports correct value."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_battery", mock_config_entry.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "75"

    attrs = state.attributes
    assert attrs.get("battery_bars") == 4
    assert attrs.get("battery_type") == "LITHIUM_ION"
    assert attrs.get("battery_health") == 95
    assert attrs.get("battery_cycle_count") == 50
    assert attrs.get("battery_temperature_c") == 25


async def test_battery_runtime_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test battery runtime sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_battery_runtime", mock_config_entry.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "120"


async def test_rf_level_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test RF level sensor with normal signal."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_rf_level", mock_config_entry.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "-50"

    attrs = state.attributes
    assert attrs.get("frequency") == "470.125 MHz"
    assert attrs.get("interference_status") == "NONE"
    assert attrs.get("encryption_status") == "OK"


async def test_rf_level_sensor_no_signal(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test RF level sensor returns None when at no-signal threshold."""
    mock_setup_entry.channels[1].rf_level = -120
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_rf_level", mock_config_entry.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"


async def test_channel_name_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test channel name sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_name", mock_config_entry.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "Mic 1"

    attrs = state.attributes
    assert attrs.get("tx_model") == "SLXD1"
    assert attrs.get("tx_device_id") == "TX-001"


async def test_channel_name_empty(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test channel name sensor when name is empty."""
    mock_setup_entry.channels[1].name = ""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_name", mock_config_entry.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"


async def test_multiple_channels(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test that sensors are created for all channels."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    # We have 2 channels in mock config - verify battery sensors for both
    for ch in [1, 2]:
        entity_id = _get_entity_id(hass, f"ch{ch}_battery", mock_config_entry.entry_id)
        state = hass.states.get(entity_id)
        assert state is not None, f"Battery sensor for channel {ch} not found"


async def test_sensor_unavailable_when_disconnected(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test sensors become unavailable when client disconnects."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_battery", mock_config_entry.entry_id)

    # Verify initially available
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state != STATE_UNAVAILABLE

    # Simulate disconnection
    mock_setup_entry.connected = False
    mock_setup_entry.send_command.side_effect = OSError("Connection lost")

    coordinator = mock_config_entry.runtime_data.coordinator
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state.state == STATE_UNAVAILABLE


async def test_battery_level_none_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test battery sensor when optional attributes are None."""
    mock_setup_entry.channels[1] = ChannelState(
        name="Mic 1",
        battery_charge=50,
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_battery", mock_config_entry.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "50"
    assert "battery_bars" not in state.attributes
    assert "battery_type" not in state.attributes


async def test_audio_level_sensor_enabled(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test audio level sensor when enabled."""
    # First, set up so the entity is registered (but disabled)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_audio_level", mock_config_entry.entry_id)

    # Enable the disabled-by-default entity
    entity_registry = er.async_get(hass)
    entity_registry.async_update_entity(
        entity_id,
        disabled_by=None,
    )

    # Reload to pick up the enabled entity
    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "-30"

    attrs = state.attributes
    assert attrs.get("peak_level") == -25
    assert attrs.get("gain") == 12
    assert attrs.get("mute") == "OFF"
    assert attrs.get("tx_mute") == "OFF"


async def test_audio_level_no_signal(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test audio level sensor at no-signal threshold."""
    mock_setup_entry.channels[1].audio_level = -120
    mock_setup_entry.channels[1].audio_level_peak = -120

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_audio_level", mock_config_entry.entry_id)

    entity_registry = er.async_get(hass)
    entity_registry.async_update_entity(
        entity_id,
        disabled_by=None,
    )

    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "unknown"
    assert "peak_level" not in state.attributes


async def test_audio_level_none_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test audio level sensor when optional attributes are None/empty."""
    mock_setup_entry.channels[1] = ChannelState(
        name="Mic 1",
        audio_level=-30,
        audio_level_peak=-120,
        audio_gain=None,
        audio_mute="",
        tx_mute_status="",
    )

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_audio_level", mock_config_entry.entry_id)

    entity_registry = er.async_get(hass)
    entity_registry.async_update_entity(
        entity_id,
        disabled_by=None,
    )

    await hass.config_entries.async_reload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "-30"
    assert "peak_level" not in state.attributes
    assert "gain" not in state.attributes
    assert "mute" not in state.attributes
    assert "tx_mute" not in state.attributes


async def test_rf_level_empty_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test RF sensor when optional attributes are empty."""
    mock_setup_entry.channels[1] = ChannelState(
        name="Mic 1",
        rf_level=-50,
        frequency="",
        interference_status="",
        encryption_status="",
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_rf_level", mock_config_entry.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == "-50"
    assert "frequency" not in state.attributes
    assert "interference_status" not in state.attributes


async def test_channel_name_no_tx_attributes(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test channel name sensor when TX info is empty."""
    mock_setup_entry.channels[1] = ChannelState(
        name="Mic 1",
        tx_model="",
        tx_device_id="",
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_id = _get_entity_id(hass, "ch1_name", mock_config_entry.entry_id)
    state = hass.states.get(entity_id)
    assert state is not None
    assert "tx_model" not in state.attributes
    assert "tx_device_id" not in state.attributes


async def test_device_info(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Test channel devices are created with correct info."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    from homeassistant.helpers import device_registry as dr

    from custom_components.shure_wireless.const import DOMAIN

    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, f"{mock_config_entry.entry_id}_ch1")})
    assert device is not None
    assert device.manufacturer == "Shure"
    assert device.model == "SLXD1"
