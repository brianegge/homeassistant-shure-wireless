"""Tests for the Shure Wireless config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shure_wireless.const import DEFAULT_PORT, DOMAIN

# ZeroconfServiceInfo may not be available on older HA versions / CI environments.
try:
    from homeassistant.helpers.service_info.zeroconf import (
        ZeroconfServiceInfo,
    )

    HAS_ZEROCONF = True
except (ModuleNotFoundError, ImportError):
    HAS_ZEROCONF = False

# ZeroconfServiceInfo requires an ip_address field from network discovery.
# SonarCloud may flag this as a security hotspot; it's safe (test-only mock data).
DISCOVERED_HOST = "192.168.1.50"  # NOSONAR


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test the full user setup flow."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    with patch(
        "custom_components.shure_wireless.config_flow._test_connection",
        new_callable=AsyncMock,
        return_value="SLXD4-001",
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": "shure-test.local",
                "port": DEFAULT_PORT,
                "num_channels": 4,
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Shure Wireless (shure-test.local)"
    assert result["data"] == {
        "host": "shure-test.local",
        "port": DEFAULT_PORT,
        "num_channels": 4,
    }


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test user flow when connection fails."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    with patch(
        "custom_components.shure_wireless.config_flow._test_connection",
        new_callable=AsyncMock,
        side_effect=ConnectionRefusedError("Connection refused"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": "shure-test.local",
                "port": DEFAULT_PORT,
                "num_channels": 4,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "connection_refused"}


async def test_user_flow_already_configured(hass: HomeAssistant) -> None:
    """Test user flow when device is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "shure-test.local", "port": DEFAULT_PORT, "num_channels": 4},
        unique_id="SLXD4-001",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    with patch(
        "custom_components.shure_wireless.config_flow._test_connection",
        new_callable=AsyncMock,
        return_value="SLXD4-001",
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": "shure-other.local",
                "port": DEFAULT_PORT,
                "num_channels": 4,
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.skipif(not HAS_ZEROCONF, reason="ZeroconfServiceInfo not available")
async def test_zeroconf_flow_success(hass: HomeAssistant) -> None:
    """Test zeroconf discovery flow."""
    discovery_info = ZeroconfServiceInfo(
        ip_address=DISCOVERED_HOST,
        ip_addresses=[DISCOVERED_HOST],
        hostname="SLXD4DE-001.local.",
        name="Shure SLXD4DE._shure._tcp.local.",
        port=DEFAULT_PORT,
        type="_shure._tcp.local.",
        properties={},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"num_channels": 2},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["host"] == DISCOVERED_HOST
    assert result["data"]["num_channels"] == 2


@pytest.mark.skipif(not HAS_ZEROCONF, reason="ZeroconfServiceInfo not available")
async def test_zeroconf_flow_already_configured(hass: HomeAssistant) -> None:
    """Test zeroconf flow when device is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "shure-test.local", "port": DEFAULT_PORT, "num_channels": 4},
        unique_id="SLXD4DE-001",
    )
    entry.add_to_hass(hass)

    discovery_info = ZeroconfServiceInfo(
        ip_address=DISCOVERED_HOST,
        ip_addresses=[DISCOVERED_HOST],
        hostname="SLXD4DE-001.local.",
        name="Shure SLXD4DE._shure._tcp.local.",
        port=DEFAULT_PORT,
        type="_shure._tcp.local.",
        properties={},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    # Verify host was updated
    assert entry.data["host"] == DISCOVERED_HOST


async def test_reconfigure_flow_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test successful reconfigure flow updates config."""
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    new_host = "shure-reconfigure.local"
    with patch(
        "custom_components.shure_wireless.config_flow._test_connection",
        new_callable=AsyncMock,
        return_value="new-device-id",
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": new_host,
                "port": DEFAULT_PORT,
                "num_channels": 2,
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data["host"] == new_host


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test reconfigure flow when connection fails."""
    result = await mock_config_entry.start_reconfigure_flow(hass)

    with patch(
        "custom_components.shure_wireless.config_flow._test_connection",
        new_callable=AsyncMock,
        side_effect=ConnectionRefusedError("Connection refused"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": "bad-host.local",
                "port": DEFAULT_PORT,
                "num_channels": 2,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "connection_refused"}


async def test_test_connection_function(hass: HomeAssistant) -> None:
    """Test the _test_connection helper function."""
    from custom_components.shure_wireless.config_flow import _test_connection
    from custom_components.shure_wireless.shure_client import ReceiverState

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.receiver = ReceiverState(device_id="SLXD4-001")

    with patch(
        "custom_components.shure_wireless.config_flow.ShureClient",
        return_value=mock_client,
    ):
        device_id = await _test_connection(hass, "shure-test.local", DEFAULT_PORT)

    assert device_id == "SLXD4-001"
    mock_client.connect.assert_awaited_once()
    mock_client.disconnect.assert_awaited_once()


async def test_test_connection_no_device_id(hass: HomeAssistant) -> None:
    """Test _test_connection when device has no ID falls back to host:port."""
    from custom_components.shure_wireless.config_flow import _test_connection
    from custom_components.shure_wireless.shure_client import ReceiverState

    mock_client = MagicMock()
    mock_client.connect = AsyncMock()
    mock_client.disconnect = AsyncMock()
    mock_client.receiver = ReceiverState(device_id=None)

    with patch(
        "custom_components.shure_wireless.config_flow.ShureClient",
        return_value=mock_client,
    ):
        device_id = await _test_connection(hass, "shure-test.local", DEFAULT_PORT)

    assert device_id == f"shure-test.local:{DEFAULT_PORT}"
