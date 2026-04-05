"""Sensor platform for Shure Wireless."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfFrequency,
)
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
    """Set up Shure Wireless sensors from a config entry."""
    coordinator = entry.runtime_data.coordinator
    client = entry.runtime_data.client

    entities: list[SensorEntity] = []

    for ch_num in client.channels:
        entities.extend(
            [
                ShureBatteryLevelSensor(coordinator, entry, ch_num),
                ShureBatteryRuntimeSensor(coordinator, entry, ch_num),
                ShureRFLevelSensor(coordinator, entry, ch_num),
                ShureAudioLevelSensor(coordinator, entry, ch_num),
                ShureChannelNameSensor(coordinator, entry, ch_num),
                ShureFrequencySensor(coordinator, entry, ch_num),
                ShureBatteryHealthSensor(coordinator, entry, ch_num),
            ]
        )

    async_add_entities(entities)


class ShureSensorBase(CoordinatorEntity[ShureCoordinator], SensorEntity):
    """Base class for Shure sensors."""

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
        """Return True if the sensor is available."""
        return self._client.connected and super().available


class ShureBatteryLevelSensor(ShureSensorBase):
    """Battery charge percentage sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery_level"

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_battery"

    @property
    def native_value(self) -> int | None:
        """Return battery charge percentage.

        Falls back to estimating from battery bars when charge percentage
        is not available (common on SLX-D transmitters with AA batteries).
        """
        charge = self._channel.battery_charge
        if charge is not None:
            return charge
        # Derive approximate percentage from battery bars (1-5)
        bars = self._channel.battery_bars
        if bars is not None:
            return bars * 20
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional battery attributes."""
        channel = self._channel
        attrs: dict[str, Any] = {}
        if channel.battery_bars is not None:
            attrs["battery_bars"] = channel.battery_bars
        if channel.battery_type:
            attrs["battery_type"] = channel.battery_type
        if channel.battery_health is not None:
            attrs["battery_health"] = channel.battery_health
        if channel.battery_cycle is not None:
            attrs["battery_cycle_count"] = channel.battery_cycle
        if channel.battery_temp_c is not None:
            attrs["battery_temperature_c"] = channel.battery_temp_c
        return attrs


class ShureBatteryRuntimeSensor(ShureSensorBase):
    """Battery runtime remaining sensor."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = "min"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery_runtime"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_battery_runtime"

    @property
    def native_value(self) -> int | None:
        """Return battery runtime in minutes."""
        return self._channel.battery_runtime


class ShureRFLevelSensor(ShureSensorBase):
    """RF signal level sensor."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "rf_level"

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_rf_level"

    @property
    def native_value(self) -> int | None:
        """Return RF signal level in dBm."""
        level = self._channel.rf_level
        # -120 is the default/no-signal value
        return level if level > -120 else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional RF attributes."""
        channel = self._channel
        attrs: dict[str, Any] = {}
        if channel.frequency:
            attrs["frequency"] = f"{channel.frequency} MHz"
        if channel.interference_status:
            attrs["interference_status"] = channel.interference_status
        if channel.encryption_status:
            attrs["encryption_status"] = channel.encryption_status
        return attrs


class ShureAudioLevelSensor(ShureSensorBase):
    """Audio level sensor."""

    _attr_native_unit_of_measurement = "dBFS"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "audio_level"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_audio_level"

    @property
    def native_value(self) -> int | None:
        """Return audio level in dBFS."""
        level = self._channel.audio_level
        return level if level > -120 else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional audio attributes."""
        channel = self._channel
        attrs: dict[str, Any] = {}
        if channel.audio_level_peak > -120:
            attrs["peak_level"] = channel.audio_level_peak
        if channel.audio_gain is not None:
            attrs["gain"] = channel.audio_gain
        if channel.audio_mute:
            attrs["mute"] = channel.audio_mute
        if channel.tx_mute_status:
            attrs["tx_mute"] = channel.tx_mute_status
        return attrs


class ShureChannelNameSensor(ShureSensorBase):
    """Channel name / transmitter info sensor."""

    _attr_translation_key = "channel_name"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_name"

    @property
    def native_value(self) -> str | None:
        """Return the channel name."""
        return self._channel.name or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return transmitter info."""
        channel = self._channel
        attrs: dict[str, Any] = {}
        if channel.tx_model:
            attrs["tx_model"] = channel.tx_model
        if channel.tx_device_id:
            attrs["tx_device_id"] = channel.tx_device_id
        return attrs


class ShureFrequencySensor(ShureSensorBase):
    """RF frequency sensor with group and channel info."""

    _attr_device_class = SensorDeviceClass.FREQUENCY
    _attr_native_unit_of_measurement = UnitOfFrequency.MEGAHERTZ
    _attr_translation_key = "frequency"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_frequency"

    @property
    def native_value(self) -> float | None:
        """Return the frequency in MHz."""
        freq = self._channel.frequency
        if not freq:
            return None
        try:
            return float(freq)
        except ValueError:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return group and channel attributes."""
        channel = self._channel
        attrs: dict[str, Any] = {}
        if channel.group:
            attrs["group"] = channel.group
        if channel.channel_num:
            attrs["channel"] = channel.channel_num
        return attrs


class ShureBatteryHealthSensor(ShureSensorBase):
    """Battery health percentage sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery_health"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_battery_health"

    @property
    def native_value(self) -> int | None:
        """Return battery health percentage."""
        return self._channel.battery_health

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional battery health attributes."""
        channel = self._channel
        attrs: dict[str, Any] = {}
        if channel.battery_cycle is not None:
            attrs["cycle_count"] = channel.battery_cycle
        return attrs
