"""Config flow for Shure Wireless."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .const import DEFAULT_PORT, DOMAIN
from .shure_client import ShureClient


async def _test_connection(hass: HomeAssistant, host: str, port: int) -> str:
    """Test connection and return device ID. Raises on failure."""
    client = ShureClient(host, port)
    try:
        await client.connect()
        device_id = client.receiver.device_id or f"{host}:{port}"
        return device_id
    finally:
        await client.disconnect()


class ShureWirelessConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Shure Wireless."""

    VERSION = 1

    _discovered_host: str | None = None
    _discovered_port: int = DEFAULT_PORT
    _discovered_name: str = ""

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        """Handle zeroconf discovery of a Shure device."""
        host = discovery_info.host
        port = discovery_info.port or DEFAULT_PORT

        # Use hostname (without .local.) as unique ID
        device_id = discovery_info.hostname.removesuffix(".").removesuffix(".local")

        await self.async_set_unique_id(device_id)
        self._abort_if_unique_id_configured(updates={"host": host, "port": port})

        self._discovered_host = host
        self._discovered_port = port
        self._discovered_name = discovery_info.name.split(".")[0]

        self.context["title_placeholders"] = {"name": self._discovered_name}

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm zeroconf discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"Shure Wireless ({self._discovered_host})",
                data={
                    "host": self._discovered_host,
                    "port": self._discovered_port,
                    "num_channels": user_input.get("num_channels", 1),
                },
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="zeroconf_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required("num_channels", default=1): vol.In({1: "1", 2: "2", 4: "4"}),
                }
            ),
            description_placeholders={
                "host": self._discovered_host or "",
                "name": self._discovered_name,
            },
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input["host"]
            port = user_input["port"]
            num_channels = user_input.get("num_channels", 4)

            try:
                device_id = await _test_connection(self.hass, host, port)
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Shure Wireless ({host})",
                    data={
                        "host": host,
                        "port": port,
                        "num_channels": num_channels,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("host"): str,
                    vol.Required("port", default=DEFAULT_PORT): int,
                    vol.Required("num_channels", default=4): vol.In({1: "1", 2: "2", 4: "4"}),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle reconfiguration."""
        errors: dict[str, str] = {}
        reconfigure_entry = self._get_reconfigure_entry()

        if user_input is not None:
            host = user_input["host"]
            port = user_input["port"]
            num_channels = user_input.get("num_channels", 4)

            try:
                device_id = await _test_connection(self.hass, host, port)
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()
                return self.async_update_reload_and_abort(
                    reconfigure_entry,
                    data={
                        "host": host,
                        "port": port,
                        "num_channels": num_channels,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "host",
                        default=reconfigure_entry.data.get("host", ""),
                    ): str,
                    vol.Required(
                        "port",
                        default=reconfigure_entry.data.get("port", DEFAULT_PORT),
                    ): int,
                    vol.Required(
                        "num_channels",
                        default=reconfigure_entry.data.get("num_channels", 4),
                    ): vol.In({1: "1", 2: "2", 4: "4"}),
                }
            ),
            errors=errors,
        )
