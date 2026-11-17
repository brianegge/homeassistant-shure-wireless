"""Base entity for Shure Wireless."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ShureConfigEntry, ShureCoordinator
from .const import DOMAIN

try:
    # HA 2026.9 added child devices: logical parts of one physical product, which is
    # what a receiver channel is. An existing channel device (registered with
    # via_device_id) is converted to a child device in place, keeping its device id.
    from homeassistant.helpers.device_registry import ChildDeviceInfo
except ImportError:  # HA < 2026.9
    ChildDeviceInfo = None

# HA 2026.8 replaced DeviceInfo's via_device with via_device_id; the old key stops working in 2027.8.
_HAS_VIA_DEVICE_ID = "via_device_id" in DeviceInfo.__annotations__
_HAS_CHILD_DEVICES = ChildDeviceInfo is not None


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
    def device_info(self) -> DeviceInfo | ChildDeviceInfo:
        """Return device info for this channel."""
        channel = self._channel
        identifiers = {(DOMAIN, f"{self._entry.entry_id}_ch{self._channel_num}")}
        name = channel.name or f"Channel {self._channel_num}"

        if _HAS_CHILD_DEVICES:
            # A child device has no manufacturer, model or firmware of its own; those
            # belong to the receiver. The transmitter model remains an attribute of the
            # channel name sensor, and model and firmware are in the diagnostics.
            return ChildDeviceInfo(
                identifiers=identifiers,
                name=name,
                parent_device_id=self._entry.runtime_data.receiver_device_id,
            )

        if _HAS_VIA_DEVICE_ID:
            via = {"via_device_id": self._entry.runtime_data.receiver_device_id}
        else:
            via = {"via_device": (DOMAIN, self._entry.entry_id)}
        return DeviceInfo(
            identifiers=identifiers,
            name=name,
            manufacturer="Shure",
            model=channel.tx_model or "Wireless Transmitter",
            sw_version=channel.tx_fw_ver or None,
            **via,
        )

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        return self._client.connected and super().available
