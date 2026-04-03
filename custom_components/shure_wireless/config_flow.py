"""Config flow for Shure Wireless."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant

from .const import DEFAULT_PORT, DOMAIN
from .shure_client import ShureClient

if TYPE_CHECKING:
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo


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
    _discovered_model: str = ""
    _discovered_num_channels: int = 1

    async def async_step_discovery(self, discovery_info: dict[str, Any]) -> ConfigFlowResult:
        """Handle ACN multicast discovery of a Shure device."""
        host = discovery_info["host"]
        cid = discovery_info["cid"]
        model = discovery_info.get("model", "")
        name = discovery_info.get("name", "")
        num_channels = discovery_info.get("num_channels", 1)

        await self.async_set_unique_id(cid)
        self._abort_if_unique_id_configured(updates={"host": host})

        self._discovered_host = host
        self._discovered_name = name
        self._discovered_model = model
        self._discovered_num_channels = num_channels

        self.context["title_placeholders"] = {"name": name or model}

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Confirm ACN discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=f"Shure {self._discovered_model} ({self._discovered_name})",
                data={
                    "host": self._discovered_host,
                    "port": DEFAULT_PORT,
                    "num_channels": self._discovered_num_channels,
                },
            )

        return self.async_show_form(
            step_id="discovery_confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "host": self._discovered_host or "",
                "name": self._discovered_name,
                "model": self._discovered_model,
                "num_channels": str(self._discovered_num_channels),
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
            except ConnectionRefusedError:
                errors["base"] = "connection_refused"
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
            except ConnectionRefusedError:
                errors["base"] = "connection_refused"
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
