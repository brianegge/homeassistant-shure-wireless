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
from .entity import ShureEntity

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
                ShureGainSensor(coordinator, entry, ch_num),
                ShureFeedbackReductionSensor(coordinator, entry, ch_num),
                ShureAntennaSensor(coordinator, entry, ch_num),
                ShureTxPowerSensor(coordinator, entry, ch_num),
                ShureTxOffsetSensor(coordinator, entry, ch_num),
                ShureSquelchSensor(coordinator, entry, ch_num),
            ]
        )

    # Receiver-level sensor (not per-channel)
    entities.append(ShureRfBandSensor(coordinator, entry))

    async_add_entities(entities)


class ShureSensorBase(ShureEntity, SensorEntity):
    """Base class for Shure sensors."""


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


class ShureGainSensor(ShureSensorBase):
    """Audio gain sensor."""

    _attr_native_unit_of_measurement = "dB"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "audio_gain"

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_audio_gain"

    @property
    def native_value(self) -> int | None:
        """Return audio gain in dB."""
        return self._channel.audio_gain


class ShureFeedbackReductionSensor(ShureSensorBase):
    """Feedback reduction (FD_MODE) status sensor."""

    _attr_translation_key = "feedback_reduction"

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_feedback_reduction"

    @property
    def native_value(self) -> str | None:
        """Return feedback reduction status."""
        return self._channel.fd_mode or None


class ShureAntennaSensor(ShureSensorBase):
    """Antenna diversity status sensor."""

    _attr_translation_key = "antenna"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_antenna"

    @property
    def native_value(self) -> str | None:
        """Return active antenna (A, B, AB, or XX for unknown)."""
        ant = self._channel.antenna
        return ant if ant != "XX" else None


class ShureTxPowerSensor(ShureSensorBase):
    """Transmitter RF power level sensor."""

    _attr_translation_key = "tx_rf_power"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_tx_rf_power"

    @property
    def native_value(self) -> str | None:
        """Return TX RF power level."""
        return self._channel.tx_rf_power or None


class ShureTxOffsetSensor(ShureSensorBase):
    """Transmitter audio offset sensor."""

    _attr_native_unit_of_measurement = "dB"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "tx_offset"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_tx_offset"

    @property
    def native_value(self) -> int | None:
        """Return TX audio offset in dB."""
        return self._channel.tx_offset


class ShureSquelchSensor(ShureSensorBase):
    """Squelch level sensor."""

    _attr_native_unit_of_measurement = "dB"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "squelch"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
        channel_num: int,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator, entry, channel_num)
        self._attr_unique_id = f"{entry.entry_id}_ch{channel_num}_squelch"

    @property
    def native_value(self) -> int | None:
        """Return squelch level."""
        return self._channel.squelch


class ShureRfBandSensor(CoordinatorEntity[ShureCoordinator], SensorEntity):
    """RF band sensor (receiver-level)."""

    _attr_has_entity_name = True
    _attr_translation_key = "rf_band"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator: ShureCoordinator,
        entry: ShureConfigEntry,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._client = coordinator.client
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_rf_band"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the receiver."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
        )

    @property
    def available(self) -> bool:
        """Return True if the sensor is available."""
        return self._client.connected and super().available

    @property
    def native_value(self) -> str | None:
        """Return the RF band."""
        return self._client.receiver.rf_band or None
