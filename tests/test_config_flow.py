"""Tests for Shure Wireless config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shure_wireless.const import DEFAULT_PORT, DOMAIN

from .conftest import MOCK_CONFIG, MOCK_DEVICE_ID, MOCK_HOST, MOCK_PORT

MOCK_DISCOVERY_INFO = {
    "host": MOCK_HOST,
    "cid": "SLXD4DE-001",
    "model": "SLXD4DE",
    "name": "Studio A",
    "num_channels": 2,
}


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
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test successful manual config flow creates entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

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
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

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
    assert result["errors"] == {"base": "connection_refused"}


async def test_user_flow_timeout(hass: HomeAssistant) -> None:
    """Test user flow shows error on timeout."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

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
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

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


# ===== Discovery tests =====


async def test_discovery_flow_shows_confirm(hass: HomeAssistant) -> None:
    """Test ACN discovery shows confirmation form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "discovery"},
        data=MOCK_DISCOVERY_INFO,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discovery_confirm"


async def test_discovery_flow_confirm_creates_entry(hass: HomeAssistant) -> None:
    """Test confirming discovery creates an entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "discovery"},
        data=MOCK_DISCOVERY_INFO,
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert "Shure SLXD4DE" in result["title"]
    assert result["data"]["num_channels"] == 2
    assert result["data"]["port"] == DEFAULT_PORT


async def test_discovery_flow_already_configured(
    hass: HomeAssistant,
) -> None:
    """Test discovery aborts if device already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Existing",
        data=MOCK_CONFIG.copy(),
        unique_id="SLXD4DE-001",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "discovery"},
        data=MOCK_DISCOVERY_INFO,
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


# ===== _test_connection helper tests =====


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
        device_id = await _test_connection(hass, MOCK_HOST, DEFAULT_PORT)

    assert device_id == "SLXD4-001"
    mock_client.connect.assert_awaited_once()
    mock_client.disconnect.assert_awaited_once()


async def test_test_connection_no_device_id(hass: HomeAssistant) -> None:
    """Test _test_connection falls back to host:port when device has no ID."""
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
        device_id = await _test_connection(hass, MOCK_HOST, DEFAULT_PORT)

    assert device_id == f"{MOCK_HOST}:{DEFAULT_PORT}"
