"""The entry in Home Assistant: entities, events, timers, the room lock, restart and removal."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from homeassistant.components.frontend import DATA_PANELS
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.guest_access.const import DOMAIN, PANEL_URL_PATH, STORAGE_KEY
from custom_components.guest_access.engine import GuestEngine

from .conftest import DOOR, RESIDENT, TRACKER

COUNTS = "binary_sensor.anna_counts"
GUESTS_HOME = "binary_sensor.guest_access_guests_home"
ONLY_GUESTS = "binary_sensor.guest_access_only_guests_home"
VISIT_ENDS = "sensor.anna_visit_ends"
ACTIVITY = "event.anna_activity"
VIOLATION = "event.guest_access_room_violation"


def engine_of(entry: MockConfigEntry) -> GuestEngine:
    """The engine of the entry."""
    engine: GuestEngine = entry.runtime_data
    return engine


def state(hass: HomeAssistant, entity_id: str) -> str:
    """The state of an entity, which must exist."""
    current = hass.states.get(entity_id)
    assert current is not None, entity_id
    return current.state


def attr(hass: HomeAssistant, entity_id: str, name: str) -> Any:
    """An attribute of an entity, which must exist."""
    current = hass.states.get(entity_id)
    assert current is not None, entity_id
    return current.attributes.get(name)


async def test_setup_and_unload(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The entry loads with its entities and the page, and unloads cleanly."""
    assert entry.state is ConfigEntryState.LOADED
    assert state(hass, COUNTS) == STATE_OFF
    assert state(hass, GUESTS_HOME) == STATE_OFF
    assert state(hass, ONLY_GUESTS) == STATE_OFF
    assert state(hass, VISIT_ENDS) == STATE_UNKNOWN
    assert state(hass, ACTIVITY) == STATE_UNKNOWN
    assert state(hass, VIOLATION) == STATE_UNKNOWN
    assert PANEL_URL_PATH in hass.data[DATA_PANELS]
    assert hass.data[DATA_PANELS][PANEL_URL_PATH].require_admin
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    # The page stays until the entry is removed; loading again keeps it
    assert PANEL_URL_PATH in hass.data[DATA_PANELS]
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, COUNTS) == STATE_OFF


async def test_remove_entry(
    hass: HomeAssistant, entry: MockConfigEntry, hass_storage: dict[str, Any]
) -> None:
    """Removing the entry removes the page and the stored guests."""
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in hass.data[DATA_PANELS]
    assert STORAGE_KEY not in hass_storage


async def test_visit(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """Arrive, time up, leave: states and events follow."""
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    assert state(hass, COUNTS) == STATE_ON
    assert state(hass, GUESTS_HOME) == STATE_ON
    assert attr(hass, GUESTS_HOME, "guests") == ["Anna"]
    assert attr(hass, GUESTS_HOME, "locked_rooms") == ["Bedroom"]
    assert attr(hass, GUESTS_HOME, "free_rooms") == []
    assert state(hass, ONLY_GUESTS) == STATE_ON
    assert state(hass, VISIT_ENDS) != STATE_UNKNOWN
    assert attr(hass, ACTIVITY, "event_type") == "arrived"

    freezer.tick(timedelta(minutes=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert attr(hass, ACTIVITY, "event_type") == "time_up"
    assert state(hass, COUNTS) == STATE_ON

    # A resident comes home: no longer only guests
    hass.states.async_set(RESIDENT, "home")
    await hass.async_block_till_done()
    assert state(hass, ONLY_GUESTS) == STATE_OFF
    assert attr(hass, GUESTS_HOME, "locked_rooms") == []

    hass.states.async_set(TRACKER, "unavailable")
    await hass.async_block_till_done()
    assert state(hass, COUNTS) == STATE_OFF
    assert state(hass, VISIT_ENDS) == STATE_UNKNOWN
    assert attr(hass, ACTIVITY, "event_type") == "left"


async def test_room_violation(hass: HomeAssistant, entry: MockConfigEntry, bedroom: str) -> None:
    """The door of a locked room opening raises a violation; with a resident home it does not."""
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    hass.states.async_set(DOOR, "on")
    await hass.async_block_till_done()
    assert attr(hass, VIOLATION, "event_type") == "opened"
    assert attr(hass, VIOLATION, "area_id") == bedroom
    assert attr(hass, VIOLATION, "area") == "Bedroom"
    assert attr(hass, VIOLATION, "door") == DOOR
    assert attr(hass, VIOLATION, "guests") == ["Anna"]
    first = state(hass, VIOLATION)

    # Staying open raises nothing more; with a resident home closing and opening neither
    hass.states.async_set(DOOR, "on", {"changed": True})
    hass.states.async_set(RESIDENT, "home")
    hass.states.async_set(DOOR, "off")
    hass.states.async_set(DOOR, "on")
    await hass.async_block_till_done()
    assert state(hass, VIOLATION) == first


async def test_open_door_at_lock_start(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A door open when the lock starts frees its room for that lock."""
    hass.states.async_set(DOOR, "on")
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    assert attr(hass, GUESTS_HOME, "locked_rooms") == []
    hass.states.async_set(DOOR, "off")
    hass.states.async_set(DOOR, "on")
    await hass.async_block_till_done()
    assert state(hass, VIOLATION) == STATE_UNKNOWN


async def test_restart_keeps_visit(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """A reload with the guest still home continues the visit without a new arrival."""
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    ends = state(hass, VISIT_ENDS)
    arrived = state(hass, ACTIVITY)
    freezer.tick(timedelta(minutes=5))
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, COUNTS) == STATE_ON
    assert state(hass, VISIT_ENDS) == ends
    assert state(hass, ACTIVITY) == arrived


async def test_restart_guest_gone(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """A guest not back within the resume window has left."""
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    hass.states.async_set(TRACKER, "not_home")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, COUNTS) == STATE_OFF
    freezer.tick(timedelta(minutes=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert attr(hass, ACTIVITY, "event_type") == "left"


async def test_change_delete_guest(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Renaming moves the device name; deleting removes device and entities."""
    engine = engine_of(entry)
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    guest = engine.data.guests["anna"]
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    from dataclasses import replace

    engine.async_save_guest(replace(guest, name="Anna B", visit_minutes=120))
    await hass.async_block_till_done()
    device = devices.async_get_device_by_identifier((DOMAIN, "anna"), entry.entry_id)
    assert device is not None
    assert device.name == "Anna B"
    presence = engine.data.presence["anna"]
    assert presence.arrived is not None
    assert presence.visit_ends == presence.arrived + timedelta(minutes=120)

    engine.async_lock_guest("anna")
    await hass.async_block_till_done()
    assert state(hass, COUNTS) == STATE_OFF
    assert attr(hass, ACTIVITY, "event_type") == "approval_changed"
    assert attr(hass, ACTIVITY, "kind") == "off"

    engine.async_delete_guest("anna")
    await hass.async_block_till_done()
    assert devices.async_get_device_by_identifier((DOMAIN, "anna"), entry.entry_id) is None
    assert entities.async_get(COUNTS) is None
    assert hass.states.get(COUNTS) is None


async def test_new_guest_gets_entities(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A guest added later gets a device with its entities."""
    engine = engine_of(entry)
    from custom_components.guest_access.model import Guest

    engine.async_save_guest(Guest("ben", "Ben", ("device_tracker.ben",)))
    await hass.async_block_till_done()
    assert state(hass, "binary_sensor.ben_counts") == STATE_OFF
    assert attr(hass, "event.ben_activity", "event_type") == "approval_changed"
    assert engine.area_name("gone") == "gone"
