"""Number platform for Shure Wireless."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ShureConfigEntry, ShureCoordinator
from .entity import ShureEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1

GAIN_RAW_OFFSET = 18


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShureConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Shure Wireless number entities from a config entry."""
    coordinator = entry.runtime_data.coordinator
    client = entry.runtime_data.client

    entities: list[NumberEntity] = []

    for ch_num in client.channels:
        entities.append(ShureGainNumber(coordinator, entry, ch_num))

    async_add_entities(entities)


class ShureGainNumber(ShureEntity, NumberEntity):
    """Number entity for adjusting audio gain on a Shure receiver channel."""

    _attr_translation_key = "audio_gain_control"
    _attr_native_unit_of_measurement = "dB"
    _attr_native_min_value = -18
    _attr_native_max_value = 42
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_audio_gain_control"

    @property
    def native_value(self) -> float | None:
        """Return current gain in dB."""
        return self._channel.audio_gain

    async def async_set_native_value(self, value: float) -> None:
        """Set the gain on the receiver."""
        raw_value = int(value) + GAIN_RAW_OFFSET
        await self._client.send_command(f"SET {self._channel_num} AUDIO_GAIN {raw_value}")
        self._channel.audio_gain = int(value)
        self.async_write_ha_state()
