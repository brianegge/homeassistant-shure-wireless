"""Diagnostics support for Shure Wireless."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import ShureConfigEntry

TO_REDACT: set[str] = {"host", "device_id", "tx_device_id", "unique_id"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ShureConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    runtime = entry.runtime_data
    client = runtime.client
    coordinator = runtime.coordinator

    channels_data: dict[str, dict[str, Any]] = {}
    for ch_num, ch_state in client.channels.items():
        channels_data[str(ch_num)] = {
            "name": ch_state.name,
            "frequency": ch_state.frequency,
            "audio_level": ch_state.audio_level,
            "audio_level_peak": ch_state.audio_level_peak,
            "rf_level": ch_state.rf_level,
            "antenna": ch_state.antenna,
            "battery_bars": ch_state.battery_bars,
            "battery_charge": ch_state.battery_charge,
            "battery_runtime": ch_state.battery_runtime,
            "battery_type": ch_state.battery_type,
            "battery_health": ch_state.battery_health,
            "battery_cycle": ch_state.battery_cycle,
            "battery_temp_c": ch_state.battery_temp_c,
            "tx_model": ch_state.tx_model,
            "tx_device_id": ch_state.tx_device_id,
            "tx_mute_status": ch_state.tx_mute_status,
            "audio_gain": ch_state.audio_gain,
            "audio_mute": ch_state.audio_mute,
            "interference_status": ch_state.interference_status,
            "encryption_status": ch_state.encryption_status,
        }

    return async_redact_data(
        {
            "config_entry": {
                "data": dict(entry.data),
                "unique_id": entry.unique_id,
            },
            "receiver": {
                "device_id": client.receiver.device_id,
                "model": client.receiver.model,
                "firmware_version": client.receiver.firmware_version,
                "rf_band": client.receiver.rf_band,
                "encryption": client.receiver.encryption,
                "lock_status": client.receiver.lock_status,
            },
            "connection": {
                "host": client.host,
                "port": client.port,
                "connected": client.connected,
                "num_channels": client.num_channels,
            },
            "channels": channels_data,
            "coordinator": {
                "last_update_success": coordinator.last_update_success,
            },
        },
        TO_REDACT,
    )
