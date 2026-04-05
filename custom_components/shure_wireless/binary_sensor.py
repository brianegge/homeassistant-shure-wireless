"""Binary sensor platform for Shure Wireless."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ShureConfigEntry, ShureCoordinator
from .entity import ShureEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShureConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Shure Wireless binary sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator
    client = entry.runtime_data.client

    entities: list[BinarySensorEntity] = []

    for ch_num in client.channels:
        entities.extend(
            [
                ShureTxMuteBinarySensor(coordinator, entry, ch_num),
                ShureAudioMuteBinarySensor(coordinator, entry, ch_num),
                ShureInterferenceBinarySensor(coordinator, entry, ch_num),
                ShureEncryptionWarningBinarySensor(coordinator, entry, ch_num),
            ]
        )

    async_add_entities(entities)


class ShureBinarySensorBase(ShureEntity, BinarySensorEntity):
    """Base class for Shure binary sensors."""


class ShureTxMuteBinarySensor(ShureBinarySensorBase):
    """Transmitter mute status binary sensor."""

    _attr_translation_key = "tx_mute"

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_tx_mute"

    @property
    def is_on(self) -> bool | None:
        """Return True if the transmitter is muted."""
        status = self._channel.tx_mute_status
        if not status:
            return None
        return status == "ON"


class ShureAudioMuteBinarySensor(ShureBinarySensorBase):
    """Receiver audio mute status binary sensor."""

    _attr_translation_key = "audio_mute"

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_audio_mute"

    @property
    def is_on(self) -> bool | None:
        """Return True if audio is muted."""
        status = self._channel.audio_mute
        if not status:
            return None
        return status == "ON"


class ShureInterferenceBinarySensor(ShureBinarySensorBase):
    """RF interference detected binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "interference"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_interference"

    @property
    def is_on(self) -> bool | None:
        """Return True if interference is detected."""
        status = self._channel.interference_status
        if not status:
            return None
        return status == "DETECTED"


class ShureEncryptionWarningBinarySensor(ShureBinarySensorBase):
    """Encryption warning binary sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "encryption_warning"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_encryption_warning"

    @property
    def is_on(self) -> bool | None:
        """Return True if there is an encryption mismatch."""
        status = self._channel.encryption_status
        if not status:
            return None
        return status not in ("OK", "OFF")
