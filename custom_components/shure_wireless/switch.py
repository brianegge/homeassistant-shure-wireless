"""Switch platform for Shure Wireless."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ShureConfigEntry, ShureCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShureConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Shure Wireless switches from a config entry."""
    coordinator = entry.runtime_data.coordinator
    client = entry.runtime_data.client

    entities: list[SwitchEntity] = []

    for ch_num in client.channels:
        entities.append(ShureAudioMuteSwitch(coordinator, entry, ch_num))

    # Receiver-level switch for front panel lock
    entities.append(ShureLockSwitch(coordinator, entry))

    async_add_entities(entities)


class ShureAudioMuteSwitch(CoordinatorEntity[ShureCoordinator], SwitchEntity):
    """Switch to control receiver-side audio mute."""

    _attr_has_entity_name = True
    _attr_translation_key = "audio_mute_control"

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._channel_num = channel_num
        self._client = coordinator.client
        self._entry = entry
        self._attr_unique_id = (
            f"{entry.entry_id}_ch{channel_num}_audio_mute_control"
        )

    @property
    def _channel(self):
        """Return the channel state."""
        return self._client.channels[self._channel_num]

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this channel."""
        channel = self._channel
        name = channel.name or f"Channel {self._channel_num}"
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry.entry_id}_ch{self._channel_num}")},
            name=f"{name}",
            manufacturer="Shure",
            model=channel.tx_model or "Wireless Transmitter",
            sw_version=channel.tx_fw_ver or None,
            via_device=(DOMAIN, self._entry.entry_id),
        )

    @property
    def available(self) -> bool:
        """Return True if the switch is available."""
        return self._client.connected and super().available

    @property
    def is_on(self) -> bool | None:
        """Return True if audio is muted."""
        status = self._channel.audio_mute
        if not status:
            return None
        return status == "ON"

    async def async_turn_on(self, **kwargs) -> None:
        """Mute the audio."""
        await self._client.send_command(
            f"SET {self._channel_num} AUDIO_MUTE ON"
        )
        self._channel.audio_mute = "ON"
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Unmute the audio."""
        await self._client.send_command(
            f"SET {self._channel_num} AUDIO_MUTE OFF"
        )
        self._channel.audio_mute = "OFF"
        self.async_write_ha_state()


class ShureLockSwitch(CoordinatorEntity[ShureCoordinator], SwitchEntity):
    """Switch to control the receiver front panel lock."""

    _attr_has_entity_name = True
    _attr_translation_key = "panel_lock"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._client = coordinator.client
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_panel_lock"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the receiver."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
        )

    @property
    def available(self) -> bool:
        """Return True if the switch is available."""
        return self._client.connected and super().available

    @property
    def is_on(self) -> bool | None:
        """Return True if the panel is locked."""
        status = self._client.receiver.lock_status
        if not status:
            return None
        return status == "LOCKED"

    async def async_turn_on(self, **kwargs) -> None:
        """Lock the front panel."""
        await self._client.send_command("SET LOCK_STATUS LOCKED")
        self._client.receiver.lock_status = "LOCKED"
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Unlock the front panel."""
        await self._client.send_command("SET LOCK_STATUS UNLOCKED")
        self._client.receiver.lock_status = "UNLOCKED"
        self.async_write_ha_state()
