"""Base entity for Shure Wireless."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ShureConfigEntry, ShureCoordinator
from .const import DOMAIN


class ShureEntity(CoordinatorEntity[ShureCoordinator]):
    """Base class for Shure channel entities."""

    _attr_has_entity_name = True

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
        """Return True if the entity is available."""
        return self._client.connected and super().available
