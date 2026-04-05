"""Button platform for Shure Wireless."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
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
    """Set up Shure Wireless buttons from a config entry."""
    coordinator = entry.runtime_data.coordinator
    client = entry.runtime_data.client

    entities: list[ButtonEntity] = []

    for ch_num in client.channels:
        entities.append(ShureFlashButton(coordinator, entry, ch_num))

    async_add_entities(entities)


class ShureFlashButton(ShureEntity, ButtonEntity):
    """Button to flash/identify a Shure transmitter channel."""

    _attr_translation_key = "flash"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_flash"

    async def async_press(self) -> None:
        """Flash the channel LEDs on the receiver."""
        await self._client.send_command(f"SET {self._channel_num} FLASH ON")
