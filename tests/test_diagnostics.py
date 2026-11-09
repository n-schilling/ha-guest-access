"""Diagnostics: the setup and the decisions, without names, entities or areas."""

from __future__ import annotations

import json
from typing import Any

from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.components.diagnostics import get_diagnostics_for_config_entry
from pytest_homeassistant.typing import ClientSessionGenerator

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .conftest import DOOR, RESIDENT, TRACKER


async def _diagnostics(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, entry: MockConfigEntry
) -> dict[str, Any]:
    assert await async_setup_component(hass, "diagnostics", {})
    return await get_diagnostics_for_config_entry(hass, hass_client, entry)


async def test_diagnostics_hide_who(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    entry: MockConfigEntry,
    bedroom: str,
) -> None:
    """A counting guest shows up with placeholders, states and minutes only."""
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()

    result = await _diagnostics(hass, hass_client, entry)

    text = json.dumps(result)
    for secret in ("Anna", "anna", TRACKER, RESIDENT, DOOR, bedroom, "Bedroom"):
        assert secret not in text
    assert result["settings"]["residents"] == ["not_home"]
    assert result["settings"]["rooms"] == [{"room": "Room 1", "door": "off"}]
    assert result["only_guests_home"] is True
    assert result["problems"] == []
    (guest,) = result["guests"]
    assert guest["guest"] == "Guest 1"
    assert guest["status"] == "counting"
    assert guest["trackers"] == ["home"]
    assert guest["approval"] == {
        "kind": "permanent",
        "until_minutes": None,
        "valid_now": True,
        "windows": [],
    }
    assert guest["rooms"] == []
    assert guest["presence"]["counting"] is True
    assert guest["presence"]["arrived_minutes"] == 0
    assert guest["presence"]["visit_ends_minutes"] == 60
    assert guest["visit_log"] == {"visits": 0, "months": 0}
    assert result["lock"] == {"active": True, "exempt": []}


async def test_diagnostics_name_problems(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, entry: MockConfigEntry
) -> None:
    """A tracker without a state is reported as missing, and as a problem by its kind."""
    result = await _diagnostics(hass, hass_client, entry)

    assert result["guests"][0]["trackers"] == ["missing"]
    assert result["guests"][0]["status"] == "away"
    assert result["problems"] == ["missing_tracker"]
