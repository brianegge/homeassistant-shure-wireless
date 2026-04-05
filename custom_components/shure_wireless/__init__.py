"""Shure Wireless integration for Home Assistant."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, HEARTBEAT_INTERVAL, PLATFORMS
from .discovery import ShureDeviceInfo, create_discovery_listener
from .shure_client import ShureClient

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema(vol.Any({}, None))},
    extra=vol.ALLOW_EXTRA,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ShureRuntimeData:
    """Runtime data for a Shure Wireless config entry."""

    client: ShureClient
    coordinator: ShureCoordinator


ShureConfigEntry = ConfigEntry[ShureRuntimeData]


class ShureCoordinator(DataUpdateCoordinator[None]):
    """Coordinator that manages polling and push updates from the receiver."""

    def __init__(self, hass: HomeAssistant, client: ShureClient) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=HEARTBEAT_INTERVAL),
        )
        self.client = client
        self._was_available = True

    async def _async_update_data(self) -> None:
        """Heartbeat: verify connection and re-request state if needed."""
        if not self.client.connected:
            if self._was_available:
                _LOGGER.warning("Lost connection to Shure receiver at %s", self.client.host)
                self._was_available = False
            try:
                await self.client.connect()
                _LOGGER.info("Reconnected to Shure receiver at %s", self.client.host)
                self._was_available = True
            except Exception as err:
                raise UpdateFailed(f"Cannot connect to Shure receiver at {self.client.host}: {err}") from err
        else:
            if not self._was_available:
                _LOGGER.info("Shure receiver at %s is available again", self.client.host)
                self._was_available = True
            # Send a heartbeat query and refresh battery state
            try:
                await self.client.send_command("GET 1 METER_RATE")
                for ch in self.client.channels:
                    for prop in ("TX_BATT_BARS", "TX_BATT_MINS"):
                        await self.client.send_command(f"GET {ch} {prop}")
            except Exception as err:
                self._was_available = False
                raise UpdateFailed(f"Error communicating with Shure receiver at {self.client.host}: {err}") from err


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Shure Wireless integration (discovery listener)."""
    _LOGGER.info("Starting Shure Wireless ACN discovery listener")
    try:
        transport, protocol = await create_discovery_listener(hass)
    except Exception:
        _LOGGER.exception("Failed to start Shure ACN discovery listener")
        return True  # Don't block manual setup

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["discovery_transport"] = transport
    hass.data[DOMAIN]["discovery_protocol"] = protocol

    def on_device_discovered(device: ShureDeviceInfo, is_new: bool) -> None:
        """Handle a discovered Shure device."""
        if not is_new:
            return
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "discovery"},
                data={
                    "host": device.host,
                    "model": device.model,
                    "name": device.name,
                    "cid": device.cid,
                    "num_channels": device.num_channels,
                },
            )
        )

    protocol.register_callback(on_device_discovered)

    async def async_set_channel_name(call: ServiceCall) -> None:
        """Set the channel name on a Shure receiver."""
        device_id = call.data["device_id"]
        new_name = call.data["name"][:8]

        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)
        if device is None:
            raise ValueError(f"Device {device_id} not found")

        # Find the config entry and channel number from device identifiers
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN and "_ch" in identifier[1]:
                entry_id = identifier[1].rsplit("_ch", 1)[0]
                channel_num = int(identifier[1].rsplit("_ch", 1)[1])
                break
        else:
            raise ValueError(f"Device {device_id} is not a Shure channel device")

        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or not hasattr(entry, "runtime_data"):
            raise ValueError(f"Config entry {entry_id} not found or not loaded")

        client = entry.runtime_data.client
        await client.send_command(f"SET {channel_num} CHAN_NAME {{{new_name}}}")

    hass.services.async_register(
        DOMAIN,
        "set_channel_name",
        async_set_channel_name,
        schema=vol.Schema(
            {
                vol.Required("device_id"): str,
                vol.Required("name"): str,
            }
        ),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ShureConfigEntry) -> bool:
    """Set up Shure Wireless from a config entry."""
    host = entry.data["host"]
    port = entry.data["port"]
    num_channels = entry.data.get("num_channels", 4)

    client = ShureClient(host, port, num_channels)

    try:
        await client.connect()
    except ConnectionRefusedError as err:
        raise ConfigEntryNotReady(
            f"Connection refused by {host}:{port}. "
            "Enable command strings: Advanced Settings > Controller Access > Allow"
        ) from err
    except Exception as err:
        raise ConfigEntryNotReady(f"Cannot connect to Shure receiver at {host}:{port}: {err}") from err

    coordinator = ShureCoordinator(hass, client)

    # When the client receives push data, request a coordinator refresh
    def on_update() -> None:
        coordinator.async_set_updated_data(None)

    client.register_callback(on_update)

    await coordinator.async_config_entry_first_refresh()

    # Register the receiver as a parent device
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Shure {client.receiver.model or 'Receiver'} ({host})",
        manufacturer="Shure",
        model=client.receiver.model or "Wireless Receiver",
        sw_version=client.receiver.firmware_version or None,
    )

    entry.runtime_data = ShureRuntimeData(client=client, coordinator=coordinator)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ShureConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        await entry.runtime_data.client.disconnect()

    return unload_ok
