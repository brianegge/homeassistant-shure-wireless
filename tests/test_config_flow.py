"""Tests for Shure Wireless config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shure_wireless.const import DOMAIN

from .conftest import MOCK_CONFIG, MOCK_DEVICE_ID, MOCK_HOST, MOCK_PORT

MOCK_ZEROCONF_INFO = ZeroconfServiceInfo(
    ip_address=None,
    ip_addresses=[],
    hostname="SLXD4DE-001.local.",
    name="Shure SLXD4DE._shure-slxd._tcp.local.",
    port=MOCK_PORT,
    properties={},
    type="_shure-slxd._tcp.local.",
)


def _mock_test_connection(device_id: str = MOCK_DEVICE_ID):
    """Create a patch for _test_connection that returns a device ID."""
    return patch(
        "custom_components.shure_wireless.config_flow._test_connection",
        new_callable=AsyncMock,
        return_value=device_id,
    )


# ===== User flow tests =====


async def test_user_flow_shows_form(hass: HomeAssistant) -> None:
    """Test that the user flow shows a form initially."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test successful manual config flow creates entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _mock_test_connection():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": MOCK_HOST,
                "port": MOCK_PORT,
                "num_channels": 2,
            },
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"Shure Wireless ({MOCK_HOST})"
    assert result["data"] == MOCK_CONFIG


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test user flow shows error on connection failure."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.shure_wireless.config_flow._test_connection",
        new_callable=AsyncMock,
        side_effect=ConnectionRefusedError("refused"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": MOCK_HOST,
                "port": MOCK_PORT,
                "num_channels": 2,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_timeout(hass: HomeAssistant) -> None:
    """Test user flow shows error on timeout."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.shure_wireless.config_flow._test_connection",
        new_callable=AsyncMock,
        side_effect=TimeoutError("Connection timed out"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": MOCK_HOST,
                "port": MOCK_PORT,
                "num_channels": 2,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test user flow aborts if device already configured."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with _mock_test_connection():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": MOCK_HOST,
                "port": MOCK_PORT,
                "num_channels": 2,
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ===== Zeroconf discovery tests =====


async def test_zeroconf_flow_shows_confirm(hass: HomeAssistant) -> None:
    """Test zeroconf discovery shows confirmation form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCK_ZEROCONF_INFO,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "zeroconf_confirm"


async def test_zeroconf_flow_confirm_creates_entry(hass: HomeAssistant) -> None:
    """Test confirming zeroconf discovery creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCK_ZEROCONF_INFO,
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"num_channels": 2},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "Shure Wireless" in result["title"]
    assert result["data"]["num_channels"] == 2
    assert result["data"]["port"] == MOCK_PORT


async def test_zeroconf_flow_already_configured(
    hass: HomeAssistant,
) -> None:
    """Test zeroconf aborts if device already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Existing",
        data=MOCK_CONFIG.copy(),
        unique_id="SLXD4DE-001",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_ZEROCONF},
        data=MOCK_ZEROCONF_INFO,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# ===== Reconfigure tests =====


async def test_reconfigure_flow_success(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test successful reconfigure flow updates config."""
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    new_host = "10.0.0.50"
    with patch(
        "custom_components.shure_wireless.config_flow._test_connection",
        new_callable=AsyncMock,
        return_value="new-device-id",
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": new_host,
                "port": MOCK_PORT,
                "num_channels": 4,
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data["host"] == new_host
    assert mock_config_entry.data["num_channels"] == 4


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test reconfigure shows error on connection failure."""
    result = await mock_config_entry.start_reconfigure_flow(hass)

    with patch(
        "custom_components.shure_wireless.config_flow._test_connection",
        new_callable=AsyncMock,
        side_effect=OSError("cannot connect"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                "host": "badhost",
                "port": MOCK_PORT,
                "num_channels": 2,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
