"""The interface others build on, pinned: a change here is a breaking change.

Automations, dashboards and scripts use the entity IDs, unique IDs, event types,
event data, attributes and WebSocket commands; the store keeps the guests across
updates. README, section Interface, describes the same; change both together and
note the change in CHANGELOG.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import ClientSessionGenerator

from homeassistant.components.websocket_api import DOMAIN as WS_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.guest_access.const import STORAGE_KEY, STORAGE_VERSION
from custom_components.guest_access.engine import GuestEngine
from custom_components.guest_access.model import AccessData, Approval, ApprovalKind

from .conftest import DOOR, RESIDENT, TRACKER

ACTIVITY = "event.guest_anna_activity"
VIOLATION = "event.guest_access_room_violation"
GUESTS_HOME = "binary_sensor.guest_access_guests_home"
# What Home Assistant adds to every event entity; the rest is the event data
EVENT_BASE = {"event_type", "event_types", "friendly_name"}


@pytest.fixture
def hass_config_dir(hass_tmp_config_dir: str) -> str:
    """Uploaded images go to a directory of their own, not into the repository."""
    return hass_tmp_config_dir


def _engine(entry: MockConfigEntry) -> GuestEngine:
    engine: GuestEngine = entry.runtime_data
    return engine


def _event(hass: HomeAssistant, entity_id: str) -> tuple[str, dict[str, Any]]:
    """The last event of an event entity: its type and its data."""
    current = hass.states.get(entity_id)
    assert current is not None
    data = {key: value for key, value in current.attributes.items() if key not in EVENT_BASE}
    return str(current.attributes["event_type"]), data


async def test_entities(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Entity IDs, unique IDs and translation keys of the hub and of a guest."""
    registry = er.async_get(hass)
    entities = {
        item.entity_id: (item.unique_id, item.translation_key, item.disabled_by is None)
        for item in er.async_entries_for_config_entry(registry, entry.entry_id)
    }
    hub = entry.entry_id
    assert entities == {
        "binary_sensor.guest_access_guests_home": (f"{hub}_guests_home", "guests_home", True),
        "binary_sensor.guest_access_only_guests_home": (
            f"{hub}_only_guests_home",
            "only_guests_home",
            True,
        ),
        "sensor.guest_access_guests_home_since": (
            f"{hub}_guests_home_since",
            "guests_home_since",
            True,
        ),
        "event.guest_access_room_violation": (f"{hub}_room_violation", "room_violation", True),
        "binary_sensor.guest_anna_counts": ("anna_counts", "counts", True),
        "sensor.guest_anna_status": ("anna_status", "status", True),
        "sensor.guest_anna_visit_ends": ("anna_visit_ends", "visit_ends", True),
        "sensor.guest_anna_hours_this_month": ("anna_month_hours", "month_hours", False),
        "event.guest_anna_activity": ("anna_activity", "activity", True),
    }
    status = hass.states.get("sensor.guest_anna_status")
    assert status is not None
    assert status.attributes["options"] == [
        "counting",
        "time_up",
        "approval_expired",
        "not_approved",
        "resuming",
        "away",
        "inactive",
    ]
    activity = hass.states.get(ACTIVITY)
    assert activity is not None
    assert activity.attributes["event_types"] == [
        "arrived",
        "left",
        "time_up",
        "approval_expired",
        "approval_changed",
    ]
    violation = hass.states.get(VIOLATION)
    assert violation is not None
    assert violation.attributes["event_types"] == ["opened"]


async def test_guest_events(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """The data each event type of a guest carries."""
    engine = _engine(entry)
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    ends = engine.data.presence_of("anna").visit_ends
    assert ends is not None
    assert _event(hass, ACTIVITY) == (
        "arrived",
        {"visit_ends": ends.replace(microsecond=0).isoformat()},
    )

    freezer.tick(timedelta(minutes=61))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _event(hass, ACTIVITY) == (
        "time_up",
        {"visit_ends": ends.replace(microsecond=0).isoformat()},
    )

    until = (dt_util.utcnow() + timedelta(minutes=5)).replace(microsecond=0)
    guest = replace(engine.data.guests["anna"], approval=Approval(ApprovalKind.UNTIL, until))
    engine.async_save_guest(guest, None, "Admin")
    await hass.async_block_till_done()
    assert _event(hass, ACTIVITY) == (
        "approval_changed",
        {
            "kind": "until",
            "until": until.isoformat(),
            "windows": [],
            "reason": "changed",
            "by": "Admin",
        },
    )

    freezer.tick(timedelta(minutes=6))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _event(hass, ACTIVITY) == (
        "approval_expired",
        {"kind": "until", "until": until.isoformat(), "windows": []},
    )

    hass.states.async_set(TRACKER, "not_home")
    await hass.async_block_till_done()
    assert _event(hass, ACTIVITY) == ("left", {})


async def test_visit_over_event(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """A once approval ends after the visit, without an administrator."""
    engine = _engine(entry)
    until = (dt_util.utcnow() + timedelta(hours=5)).replace(microsecond=0)
    guest = replace(engine.data.guests["anna"], approval=Approval(ApprovalKind.ONCE, until))
    engine.async_save_guest(guest)
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    hass.states.async_set(TRACKER, "not_home")
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=16))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _event(hass, ACTIVITY) == (
        "approval_changed",
        {"kind": "off", "until": None, "windows": [], "reason": "visit_over", "by": None},
    )


async def test_room_violation_and_summary(
    hass: HomeAssistant, entry: MockConfigEntry, bedroom: str
) -> None:
    """The data of a room violation and the attributes of "Guests home"."""
    hass.states.async_set(RESIDENT, "not_home")
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    hass.states.async_set(DOOR, "on")
    await hass.async_block_till_done()
    assert _event(hass, VIOLATION) == (
        "opened",
        {"area_id": bedroom, "area": "Bedroom", "door": DOOR, "guests": ["Anna"]},
    )
    current = hass.states.get(GUESTS_HOME)
    assert current is not None
    attributes = {
        key: value
        for key, value in current.attributes.items()
        if key not in {"device_class", "friendly_name"}
    }
    ends = _engine(entry).data.presence_of("anna").visit_ends
    assert ends is not None
    assert attributes == {
        "guests": ["Anna"],
        "free_rooms": [],
        "locked_rooms": ["Bedroom"],
        "guest_list": [
            {
                "name": "Anna",
                "picture": None,
                "status": "counting",
                "status_entity": "sensor.guest_anna_status",
                "visit_ends": ends.replace(microsecond=0).isoformat(),
            }
        ],
    }


async def test_websocket_commands(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The commands of the page, by name."""
    commands = {name for name in hass.data[WS_DOMAIN] if name.startswith("guest_access/")}
    assert commands == {
        "guest_access/subscribe",
        "guest_access/save_guest",
        "guest_access/delete_guest",
        "guest_access/delete_visits",
        "guest_access/lock_guest",
        "guest_access/save_settings",
    }


# The stored format, version 1: every field a store of this version may hold
STORED_V1: dict[str, Any] = {
    "settings": {
        "residents": ["person.sam"],
        "rooms": [{"area_id": "bedroom", "door": "binary_sensor.bedroom_door"}],
        "resume_minutes": 10,
        "log_grid_minutes": 15,
        "log_keep_days": 90,
        "log_keep_months": 13,
    },
    "guests": [
        {
            "id": "0123456789abcdef0123456789abcdef",
            "name": "Anna",
            "trackers": ["device_tracker.anna_phone"],
            "approval": {
                "kind": "until",
                "until": "2026-12-31T23:00:00+00:00",
                "windows": [{"weekdays": [0, 4], "start": "08:00", "end": "18:00"}],
            },
            "rooms": ["bedroom"],
            "all_rooms": False,
            "visit_minutes": None,
            "grace_minutes": 15,
            "log_visits": True,
            "picture": "fedcba9876543210fedcba9876543210",
            "note": "Brings the dog",
        }
    ],
    "presence": {
        "0123456789abcdef0123456789abcdef": {
            "counting": True,
            "arrived": "2026-11-09T10:00:00+00:00",
            "visit_ends": None,
            "away_since": None,
            "resume_until": None,
            # Added in 0.4.0: when Home Assistant started, while waiting to resume
            "restarted": None,
            "time_up": False,
            "approval_expired": False,
        }
    },
    "lock": {"active": True, "exempt": ["kitchen"]},
    "visits": [
        {
            "guest_id": "0123456789abcdef0123456789abcdef",
            "start": "2026-11-02T09:00:00+00:00",
            "minutes": 90,
        }
    ],
    "months": {"0123456789abcdef0123456789abcdef": {"2026-11": {"visits": 1, "minutes": 90}}},
    # The photos uploaded through Guest Access, with the time of the upload
    "pictures": {"fedcba9876543210fedcba9876543210": "2026-11-02T08:00:00+00:00"},
}


def test_store_format() -> None:
    """Version 1 of the store reads and writes exactly these fields."""
    assert STORAGE_KEY == "guest_access"
    assert STORAGE_VERSION == 1
    assert AccessData.from_dict(STORED_V1).as_dict() == STORED_V1


def test_store_before_restart_time() -> None:
    """A store written before 0.4.0, without the start time, still reads."""
    presence = {
        guest_id: {key: value for key, value in fields.items() if key != "restarted"}
        for guest_id, fields in STORED_V1["presence"].items()
    }
    data = AccessData.from_dict({**STORED_V1, "presence": presence})
    assert data.presence["0123456789abcdef0123456789abcdef"].restarted is None


async def test_photo_interface(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_tmp_config_dir: str,
) -> None:
    """The upload's address, and where a photo shows: counts, status and guest_list."""
    import io

    import aiohttp
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, format="PNG")
    form = aiohttp.FormData()
    form.add_field("file", buffer.getvalue(), filename="p.png", content_type="image/png")
    response = await (await hass_client()).post("/api/guest_access/picture", data=form)
    assert response.status == 200
    image_id = (await response.json())["id"]
    engine = _engine(entry)
    engine.async_save_guest(replace(engine.data.guests["anna"], picture=image_id))
    await hass.async_block_till_done()
    url = f"/api/image/serve/{image_id}/512x512"
    for entity_id in ("binary_sensor.guest_anna_counts", "sensor.guest_anna_status"):
        current = hass.states.get(entity_id)
        assert current is not None
        assert current.attributes["entity_picture"] == url
    current = hass.states.get(GUESTS_HOME)
    assert current is not None
    assert current.attributes["guest_list"][0]["picture"] == url
