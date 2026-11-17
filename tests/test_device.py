"""Tests for how Shure Wireless registers its receiver and channel devices."""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shure_wireless import entity as shure_entity
from custom_components.shure_wireless.const import DOMAIN

requires_child_devices = pytest.mark.skipif(
    not shure_entity._HAS_CHILD_DEVICES,
    reason="Home Assistant under test has no child devices (added in 2026.9)",
)


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _channel_identifier(entry: MockConfigEntry, channel: int) -> tuple[str, str]:
    return (DOMAIN, f"{entry.entry_id}_ch{channel}")


def _entities_by_unique_id(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, er.RegistryEntry]:
    return {e.unique_id: e for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)}


def _friendly_names(hass: HomeAssistant, entries) -> dict[str, str]:
    """Return the friendly name of each entity that has a state (enabled ones)."""
    return {e.entity_id: state.name for e in entries if (state := hass.states.get(e.entity_id)) is not None}


@requires_child_devices
async def test_channels_are_child_devices_of_the_receiver(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """On HA with child devices, each channel is a child device of its receiver."""
    await _setup(hass, mock_config_entry)

    device_registry = dr.async_get(hass)
    entry_id = mock_config_entry.entry_id
    receiver = device_registry.async_get_device_by_identifier((DOMAIN, entry_id), entry_id)
    assert receiver is not None
    assert mock_config_entry.runtime_data.receiver_device_id == receiver.id

    for channel in (1, 2):
        identifier = _channel_identifier(mock_config_entry, channel)
        child = device_registry.async_get_child_device_by_identifier(identifier, entry_id)
        assert isinstance(child, dr.ChildDeviceEntry)
        assert child.parent_device_id == receiver.id
        assert child.name == f"Mic {channel}"
        # Not registered as a main device as well
        assert device_registry.async_get_device_by_identifier(identifier, entry_id) is None
        # The channel's entities hang off the child device
        entities = er.async_entries_for_device(er.async_get(hass), child.id)
        assert entities
        assert all(e.unique_id.startswith(f"{entry_id}_ch{channel}_") for e in entities)

    assert {c.id for c in dr.async_entries_for_parent_device(device_registry, receiver.id)} == {
        device_registry.async_get_child_device_by_identifier(_channel_identifier(mock_config_entry, ch), entry_id).id
        for ch in (1, 2)
    }


@pytest.mark.parametrize("has_via_device_id", [True, False], ids=["via_device_id", "via_device_fallback"])
async def test_channels_link_via_receiver_without_child_devices(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
    has_via_device_id: bool,
) -> None:
    """Without child devices (HA < 2026.9), channels are devices linked via the receiver.

    The via_device fallback serves HA < 2026.8; current HA stops accepting it in 2027.8,
    at which point this case fails and the fallback (and old-HA support) should be dropped.
    """
    with (
        patch.object(shure_entity, "_HAS_CHILD_DEVICES", False),
        patch.object(shure_entity, "_HAS_VIA_DEVICE_ID", has_via_device_id),
    ):
        await _setup(hass, mock_config_entry)

    device_registry = dr.async_get(hass)
    entry_id = mock_config_entry.entry_id
    receiver = device_registry.async_get_device_by_identifier((DOMAIN, entry_id), entry_id)
    channel = device_registry.async_get_device_by_identifier(_channel_identifier(mock_config_entry, 1), entry_id)
    assert receiver is not None
    assert channel is not None
    assert channel.via_device_id == receiver.id
    assert channel.name == "Mic 1"
    assert channel.manufacturer == "Shure"
    assert channel.model == "SLXD1"
    assert mock_config_entry.runtime_data.receiver_device_id == receiver.id


async def test_child_device_detection_follows_ha(monkeypatch: pytest.MonkeyPatch) -> None:
    """The child-device path switches off when HA has no ChildDeviceInfo."""
    try:
        monkeypatch.delattr(dr, "ChildDeviceInfo", raising=False)
        importlib.reload(shure_entity)
        assert shure_entity._HAS_CHILD_DEVICES is False
    finally:
        monkeypatch.undo()
        importlib.reload(shure_entity)
    assert shure_entity._HAS_CHILD_DEVICES is hasattr(dr, "ChildDeviceInfo")


@requires_child_devices
async def test_existing_channel_devices_migrate_in_place(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Channel devices registered by earlier versions become child devices in place.

    Device ids, entity ids, user customisations and friendly names must survive:
    automations and dashboards reference them.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    entry_id = mock_config_entry.entry_id

    # 1. Earlier version: channels are main devices linked with via_device_id. The user
    # renamed a channel device, put it in an area, and renamed one entity id.
    area = ar.async_get(hass).async_get_or_create("Church")
    with patch.object(shure_entity, "_HAS_CHILD_DEVICES", False):
        await _setup(hass, mock_config_entry)

        receiver = device_registry.async_get_device_by_identifier((DOMAIN, entry_id), entry_id)
        old_channel = device_registry.async_get_device_by_identifier(
            _channel_identifier(mock_config_entry, 1), entry_id
        )
        assert old_channel is not None
        assert old_channel.via_device_id == receiver.id

        device_registry.async_update_device(old_channel.id, name_by_user="Channel 3", area_id=area.id)
        battery = _entities_by_unique_id(hass, mock_config_entry)[f"{entry_id}_ch1_battery"]
        entity_registry.async_update_entity(battery.entity_id, new_entity_id="sensor.pastor_mic_battery")
        await hass.async_block_till_done()

    before = _entities_by_unique_id(hass, mock_config_entry)
    friendly_before = _friendly_names(hass, before.values())
    assert friendly_before["sensor.pastor_mic_battery"] == "Channel 3 Battery"
    old_ids = {
        ch: device_registry.async_get_device_by_identifier(_channel_identifier(mock_config_entry, ch), entry_id).id
        for ch in (1, 2)
    }

    # 2. Upgrade: unload (as a restart would) and set up with child devices.
    assert await hass.config_entries.async_unload(entry_id)
    await hass.async_block_till_done()
    await _setup(hass, mock_config_entry)

    for ch, old_id in old_ids.items():
        identifier = _channel_identifier(mock_config_entry, ch)
        assert device_registry.async_get_device_by_identifier(identifier, entry_id) is None
        child = device_registry.async_get_child_device_by_identifier(identifier, entry_id)
        assert isinstance(child, dr.ChildDeviceEntry)
        assert child.id == old_id
        assert child.parent_device_id == receiver.id
        assert device_registry.async_get(old_id) == child

    child1 = device_registry.async_get(old_ids[1])
    assert child1.name == "Mic 1"
    assert child1.name_by_user == "Channel 3"
    assert child1.area_id == area.id

    # The receiver is untouched and no device was duplicated.
    assert device_registry.async_get(receiver.id) is not None
    assert len(dr.async_entries_for_config_entry(device_registry, entry_id)) == 1
    assert len(dr.async_child_entries_for_config_entry(device_registry, entry_id)) == 2

    after = _entities_by_unique_id(hass, mock_config_entry)
    assert {uid: (e.entity_id, e.device_id) for uid, e in after.items()} == {
        uid: (e.entity_id, e.device_id) for uid, e in before.items()
    }
    assert after[f"{entry_id}_ch1_battery"].entity_id == "sensor.pastor_mic_battery"
    assert _friendly_names(hass, after.values()) == friendly_before


@requires_child_devices
async def test_set_channel_name_accepts_child_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """The set_channel_name action resolves a channel child device."""
    await _setup(hass, mock_config_entry)

    child = dr.async_get(hass).async_get_child_device_by_identifier(
        _channel_identifier(mock_config_entry, 2), mock_config_entry.entry_id
    )
    await hass.services.async_call(DOMAIN, "set_channel_name", {"device_id": child.id, "name": "Hand 3"}, blocking=True)
    mock_setup_entry.send_command.assert_any_await("SET 2 CHAN_NAME {Hand 3}")


@requires_child_devices
async def test_diagnostics_list_child_devices(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_setup_entry: MagicMock,
) -> None:
    """Diagnostics still list the channel devices once they are child devices."""
    await _setup(hass, mock_config_entry)

    from custom_components.shure_wireless.diagnostics import async_get_config_entry_diagnostics

    result = await async_get_config_entry_diagnostics(hass, mock_config_entry)
    assert sorted(d["name"] for d in result["child_devices"]) == ["Mic 1", "Mic 2"]
