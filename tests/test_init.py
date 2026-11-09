"""The entry in Home Assistant: entities, events, timers, the room lock, restart and removal."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from homeassistant.components.frontend import DATA_PANELS
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from homeassistant.helpers.event import EventStateChangedData, async_track_state_change_event
from homeassistant.util import dt as dt_util

from custom_components.guest_access.const import DOMAIN, PANEL_URL_PATH, STORAGE_KEY
from custom_components.guest_access.engine import GuestEngine

from .conftest import DOOR, RESIDENT, TRACKER

COUNTS = "binary_sensor.guest_anna_counts"
GUESTS_HOME = "binary_sensor.guest_access_guests_home"
ONLY_GUESTS = "binary_sensor.guest_access_only_guests_home"
VISIT_ENDS = "sensor.guest_anna_visit_ends"
STATUS = "sensor.guest_anna_status"
HOME_SINCE = "sensor.guest_access_guests_home_since"
ACTIVITY = "event.guest_anna_activity"
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
    assert state(hass, HOME_SINCE) == STATE_UNKNOWN
    assert state(hass, VISIT_ENDS) == STATE_UNKNOWN
    assert state(hass, STATUS) == "away"
    assert attr(hass, STATUS, "options") == [
        "counting",
        "time_up",
        "approval_expired",
        "not_approved",
        "resuming",
        "away",
        "inactive",
    ]
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
    assert state(hass, HOME_SINCE) != STATE_UNKNOWN
    assert attr(hass, ACTIVITY, "event_type") == "arrived"
    assert state(hass, STATUS) == "counting"

    freezer.tick(timedelta(minutes=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert attr(hass, ACTIVITY, "event_type") == "time_up"
    assert state(hass, COUNTS) == STATE_ON
    assert state(hass, STATUS) == "time_up"

    # A resident comes home: no longer only guests
    hass.states.async_set(RESIDENT, "home")
    await hass.async_block_till_done()
    assert state(hass, ONLY_GUESTS) == STATE_OFF
    assert attr(hass, GUESTS_HOME, "locked_rooms") == []

    hass.states.async_set(TRACKER, "unavailable")
    await hass.async_block_till_done()
    assert state(hass, COUNTS) == STATE_OFF
    assert state(hass, VISIT_ENDS) == STATE_UNKNOWN
    assert state(hass, HOME_SINCE) == STATE_UNKNOWN
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
    assert state(hass, STATUS) == "not_approved"
    assert attr(hass, ACTIVITY, "event_type") == "approval_changed"
    assert attr(hass, ACTIVITY, "kind") == "off"
    # Locked and gone: no longer an approved guest who is away
    hass.states.async_set(TRACKER, "not_home")
    await hass.async_block_till_done()
    assert state(hass, STATUS) == "inactive"

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
    assert state(hass, "binary_sensor.guest_ben_counts") == STATE_OFF
    assert attr(hass, "event.guest_ben_activity", "event_type") == "approval_changed"
    assert engine.area_name("gone") == "gone"


async def test_door_contact_back_from_unavailable(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """A contact reconnecting while the door is open is no opening."""
    hass.states.async_set(DOOR, "on")
    await hass.async_block_till_done()
    hass.states.async_set(TRACKER, "home")
    hass.states.async_set(DOOR, "unavailable")
    await hass.async_block_till_done()
    hass.states.async_set(DOOR, "on")
    await hass.async_block_till_done()
    assert state(hass, VIOLATION) == STATE_UNKNOWN


async def test_door_opened_while_unavailable(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A door closed before the outage and open after it was opened: a violation."""
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    hass.states.async_set(DOOR, "unavailable")
    hass.states.async_set(DOOR, "on")
    await hass.async_block_till_done()
    assert attr(hass, VIOLATION, "event_type") == "opened"
    # A contact that disappears raises nothing
    first = state(hass, VIOLATION)
    hass.states.async_remove(DOOR)
    await hass.async_block_till_done()
    assert state(hass, VIOLATION) == first


async def test_locked_while_resuming(
    hass: HomeAssistant, entry: MockConfigEntry, bedroom: str
) -> None:
    """A guest locked while waiting to resume frees no room any more."""
    from dataclasses import replace

    engine = engine_of(entry)
    engine.async_save_guest(replace(engine.data.guests["anna"], rooms=(bedroom,)))
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    hass.states.async_set(TRACKER, "unavailable")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    engine = engine_of(entry)
    engine.async_lock_guest("anna")
    await hass.async_block_till_done()
    assert engine.data.presence["anna"].resume_until is None
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    assert state(hass, COUNTS) == STATE_OFF


async def test_own_room_free_after_restart(
    hass: HomeAssistant, entry: MockConfigEntry, bedroom: str
) -> None:
    """A guest's own room raises nothing while the tracker is not back yet."""
    from dataclasses import replace

    engine = engine_of(entry)
    engine.async_save_guest(replace(engine.data.guests["anna"], rooms=(bedroom,)))
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    hass.states.async_set(TRACKER, "unavailable")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set(DOOR, "on")
    await hass.async_block_till_done()
    assert state(hass, VIOLATION) == STATE_UNKNOWN


async def test_event_at_start_reaches_entity(
    hass: HomeAssistant, entry: MockConfigEntry, hass_storage: dict[str, Any]
) -> None:
    """A once approval that ended while Home Assistant was down raises its event."""
    assert await hass.config_entries.async_unload(entry.entry_id)
    data = hass_storage[STORAGE_KEY]["data"]
    data["guests"][0]["approval"] = {
        "kind": "once",
        "until": "2099-01-01T00:00:00+00:00",
        "windows": [],
    }
    data["presence"] = {"anna": {"counting": False, "away_since": "2026-01-01T00:00:00+00:00"}}
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert attr(hass, ACTIVITY, "event_type") == "approval_changed"
    assert attr(hass, ACTIVITY, "reason") == "visit_over"


async def test_attribute_change_not_evaluated(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A tracker's position update without a state change decides nothing."""
    from unittest.mock import patch

    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    engine = engine_of(entry)
    with patch.object(engine, "_evaluate") as evaluate:
        hass.states.async_set(TRACKER, "home", {"latitude": 1.0})
        await hass.async_block_till_done()
    evaluate.assert_not_called()


async def test_admin_changes_are_saved(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Changes on the page reach the store without an unload, so a crash keeps them."""
    from dataclasses import replace

    from custom_components.guest_access.model import Guest, Settings

    engine = engine_of(entry)

    def saved() -> dict[str, Any]:
        freezer.tick(timedelta(seconds=5))
        async_fire_time_changed(hass)
        data: dict[str, Any] = hass_storage[STORAGE_KEY]["data"]
        return {**data, "guests": {guest["id"]: guest for guest in data["guests"]}}

    engine.async_save_guest(Guest("ben", "Ben", ("device_tracker.ben",)))
    await hass.async_block_till_done()
    assert "ben" in saved()["guests"]

    engine.async_save_guest(replace(engine.data.guests["ben"], name="Ben B"))
    await hass.async_block_till_done()
    assert saved()["guests"]["ben"]["name"] == "Ben B"

    engine.async_save_settings(Settings((RESIDENT, "person.robin"), ()))
    await hass.async_block_till_done()
    assert saved()["settings"]["residents"] == [RESIDENT, "person.robin"]

    engine.async_delete_guest("ben")
    await hass.async_block_till_done()
    assert "ben" not in saved()["guests"]


async def test_entity_id_change_keeps_device_name(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Changing an entity ID re-adds the entity; the device keeps the guest's current name."""
    from dataclasses import replace

    engine = engine_of(entry)
    devices = dr.async_get(hass)
    engine.async_save_guest(replace(engine.data.guests["anna"], name="Anna B"))
    await hass.async_block_till_done()
    er.async_get(hass).async_update_entity(COUNTS, new_entity_id="binary_sensor.guest_anna_counts")
    await hass.async_block_till_done()
    device = devices.async_get_device_by_identifier((DOMAIN, "anna"), entry.entry_id)
    assert device is not None
    assert device.name == "Anna B"


async def test_reload_keeps_guest_home(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A reload never shows a guest who is home as gone."""
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    assert state(hass, GUESTS_HOME) == STATE_ON
    last_event = state(hass, ACTIVITY)
    seen: list[str] = []

    @callback
    def _record(event: Event[EventStateChangedData]) -> None:
        if (new := event.data["new_state"]) is not None:
            seen.append(new.state)

    unsub = async_track_state_change_event(hass, [GUESTS_HOME, COUNTS], _record)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    unsub()
    assert STATE_OFF not in seen
    assert state(hass, GUESTS_HOME) == STATE_ON
    # The continued visit raises nothing new; the entity only restores its last event
    assert state(hass, ACTIVITY) == last_event


async def test_events_wait_for_their_entity(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """An event raised before its guest has a listener reaches the first one, the last ten."""
    engine = engine_of(entry)
    for n in range(12):
        engine._raise("ghost", "left", {"n": n})
    got: list[int] = []
    unsub = engine.async_add_event_listener(lambda _g, _t, data, _c: got.append(data["n"]), "ghost")
    assert got == list(range(2, 12))
    engine._raise("ghost", "left", {"n": 99})
    assert got[-1] == 99
    unsub()


async def test_visit_time_change_while_away(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """A new time per visit also applies to a visit that goes on after the grace time."""
    from dataclasses import replace

    engine = engine_of(entry)
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    arrived = engine.data.presence["anna"].arrived
    assert arrived is not None
    hass.states.async_set(TRACKER, "not_home")
    await hass.async_block_till_done()
    engine.async_save_guest(replace(engine.data.guests["anna"], visit_minutes=120))
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=5))
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    assert engine.data.presence["anna"].visit_ends == arrived + timedelta(minutes=120)


async def test_approval_change_no_second_expiry(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Changing an expired approval to another invalid one raises no new expiry; the change comes first."""
    from dataclasses import replace

    from custom_components.guest_access.model import Approval, ApprovalKind

    engine = engine_of(entry)
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    types: list[str] = []
    engine.async_add_event_listener(lambda _g, event_type, _d, _c: types.append(event_type), "anna")
    past = dt_util.utcnow() - timedelta(hours=1)
    engine.async_save_guest(
        replace(engine.data.guests["anna"], approval=Approval(ApprovalKind.UNTIL, past))
    )
    await hass.async_block_till_done()
    assert types == ["approval_changed", "approval_expired"]
    engine.async_save_guest(
        replace(
            engine.data.guests["anna"],
            approval=Approval(ApprovalKind.UNTIL, past - timedelta(hours=1)),
        )
    )
    await hass.async_block_till_done()
    assert types == ["approval_changed", "approval_expired", "approval_changed"]


async def test_room_added_during_lock_with_open_door(
    hass: HomeAssistant, entry: MockConfigEntry, bedroom: str
) -> None:
    """A room that becomes lockable during the lock is free while its door is open then."""
    from custom_components.guest_access.model import Room, Settings

    engine = engine_of(entry)
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    assert engine.data.lock.active
    office = ar.async_get(hass).async_create("Office").id
    hass.states.async_set("binary_sensor.office_door", "on")
    engine.async_save_settings(
        Settings((RESIDENT,), (Room(bedroom, DOOR), Room(office, "binary_sensor.office_door")))
    )
    await hass.async_block_till_done()
    assert office in engine.data.lock.exempt
    assert attr(hass, GUESTS_HOME, "locked_rooms") == ["Bedroom"]


async def test_visit_log_sensor_and_off(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """The month's hours follow the finished visits; switching the log off removes it."""
    from dataclasses import replace

    engine = engine_of(entry)
    hours = "sensor.guest_anna_hours_this_month"
    registry = er.async_get(hass)
    assert registry.async_get(hours).disabled_by is er.RegistryEntryDisabler.INTEGRATION  # type: ignore[union-attr]
    registry.async_update_entity(hours, disabled_by=None)
    # Home Assistant reloads the entry itself after enabling an entity
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    engine = engine_of(entry)
    assert state(hass, hours) == STATE_UNKNOWN
    engine.async_save_guest(replace(engine.data.guests["anna"], log_visits=True))
    await hass.async_block_till_done()
    assert state(hass, hours) == "0.0"
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=90))
    hass.states.async_set(TRACKER, "not_home")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert state(hass, hours) == "1.5"
    engine.async_save_guest(replace(engine.data.guests["anna"], log_visits=False))
    await hass.async_block_till_done()
    assert state(hass, hours) == STATE_UNKNOWN
    assert engine.data.visits == []


async def test_month_change_wakes(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The engine wakes at the start of the next month, so the hours start again."""
    from custom_components.guest_access.engine import _next_month

    moment = dt_util.as_utc(dt_util.parse_datetime("2026-12-31T23:30:00+01:00"))
    start = _next_month(moment)
    assert dt_util.as_local(start).strftime("%Y-%m-%d %H:%M") == "2027-01-01 00:00"


async def test_guest_list(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """The guest list shows every guest but inactive ones, with status and visit end."""

    def guest_list() -> list[dict[str, Any]]:
        value: list[dict[str, Any]] = attr(hass, GUESTS_HOME, "guest_list")
        return value

    # Approved but not home: shown as away, without an end
    assert guest_list() == [
        {
            "name": "Anna",
            "picture": None,
            "status": "away",
            "status_entity": STATUS,
            "visit_ends": None,
        }
    ]

    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    ends = dt_util.parse_datetime(state(hass, VISIT_ENDS))
    assert ends is not None
    assert guest_list() == [
        {
            "name": "Anna",
            "picture": None,
            "status": "counting",
            "status_entity": STATUS,
            "visit_ends": ends.isoformat(),
        }
    ]

    freezer.tick(timedelta(minutes=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert guest_list()[0]["status"] == "time_up"
    assert guest_list()[0]["visit_ends"] == ends.isoformat()

    # The device name a user gives wins over the profile name
    device = dr.async_get(hass).async_get_device_by_identifier((DOMAIN, "anna"), entry.entry_id)
    assert device is not None
    dr.async_get(hass).async_update_device(device.id, name_by_user="Anna B.")
    hass.states.async_set(TRACKER, "not_home")
    await hass.async_block_till_done()
    assert guest_list()[0]["name"] == "Anna B."

    # Locked and away: inactive, left out
    engine_of(entry).async_lock_guest("anna", None, "Admin")
    await hass.async_block_till_done()
    assert state(hass, STATUS) == "inactive"
    assert guest_list() == []
