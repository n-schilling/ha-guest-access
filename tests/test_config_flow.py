"""Tests of the config flow."""

from __future__ import annotations

from pytest_homeassistant.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.guest_access.const import DOMAIN, TITLE


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """The form is confirmed and creates the single entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TITLE
    assert result["data"] == {}


async def test_only_one_entry(hass: HomeAssistant) -> None:
    """A second entry is refused."""
    MockConfigEntry(domain=DOMAIN, title=TITLE).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"
