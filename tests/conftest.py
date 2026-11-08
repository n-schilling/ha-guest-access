"""Fixtures shared by the tests: a stored guest, the bedroom as lockable room, a loaded entry."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.setup import async_setup_component

from custom_components.guest_access.const import DOMAIN, STORAGE_KEY, TITLE

TRACKER = "device_tracker.anna_phone"
DOOR = "binary_sensor.bedroom_door"
RESIDENT = "person.sam"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: Any) -> None:
    """Load the integration from custom_components in every test."""


@pytest.fixture
def bedroom(hass: HomeAssistant) -> str:
    """The id of the bedroom area."""
    return ar.async_get(hass).async_create("Bedroom").id


@pytest.fixture
def stored(bedroom: str) -> dict[str, Any]:
    """What is in storage before the entry loads: Anna, permanent, living area only."""
    return {
        "settings": {"residents": [RESIDENT], "rooms": [{"area_id": bedroom, "door": DOOR}]},
        "guests": [
            {
                "id": "anna",
                "name": "Anna",
                "trackers": [TRACKER],
                "approval": {"kind": "permanent", "until": None, "windows": []},
                "rooms": [],
                "all_rooms": False,
                "visit_minutes": 60,
                "grace_minutes": 15,
            }
        ],
        "presence": {},
        "lock": {"active": False, "exempt": []},
    }


@pytest.fixture
async def entry(
    hass: HomeAssistant, hass_storage: dict[str, Any], stored: dict[str, Any]
) -> MockConfigEntry:
    """The loaded entry, with the stored data in place."""
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": stored,
    }
    assert await async_setup_component(hass, "http", {})
    hass.states.async_set(RESIDENT, "not_home")
    hass.states.async_set(DOOR, "off")
    entry = MockConfigEntry(domain=DOMAIN, title=TITLE)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
