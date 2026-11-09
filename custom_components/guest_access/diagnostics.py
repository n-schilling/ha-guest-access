"""Diagnostics: how the integration is set up and what it decides, without who the guests are.

Names, trackers, residents, areas and door contacts are replaced by placeholders
(Guest 1, Room 1), times by minutes from now and the visit log by its size, so
the download can be attached to an issue as it is.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.const import STATE_HOME, STATE_NOT_HOME, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import GuestAccessConfigEntry
from .issues import find_problems


def _minutes(moment: datetime | None, now: datetime) -> int | None:
    """Minutes from now to a moment, negative when it has passed."""
    if moment is None:
        return None
    return round((moment - now).total_seconds() / 60)


# A tracker or person in a zone has the zone's name as state, which can say
# where someone is; diagnostics only tell whether it is at home
_PLAIN_STATES = frozenset({STATE_HOME, STATE_NOT_HOME, STATE_UNKNOWN, STATE_UNAVAILABLE})


def _state(hass: HomeAssistant, entity_id: str) -> str:
    """The state of a tracker, person or door, a zone name only as "zone"."""
    current = hass.states.get(entity_id)
    if current is None:
        return "missing"
    if entity_id.startswith("binary_sensor.") or current.state in _PLAIN_STATES:
        return current.state
    return "zone"


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GuestAccessConfigEntry
) -> dict[str, Any]:
    """The settings, the guests and their runtime state, with placeholders for names."""
    engine = entry.runtime_data
    data = engine.data
    now = dt_util.utcnow()
    settings = data.settings
    rooms = {room.area_id: f"Room {number}" for number, room in enumerate(settings.rooms, 1)}
    guests = {guest_id: f"Guest {number}" for number, guest_id in enumerate(data.guests, 1)}

    def room(area_id: str) -> str:
        return rooms.get(area_id, "unknown room")

    def guest_info(guest_id: str) -> dict[str, Any]:
        guest = data.guests[guest_id]
        presence = data.presence_of(guest_id)
        approval = guest.approval
        return {
            "guest": guests[guest_id],
            "status": engine.status(guest_id),
            "trackers": [_state(hass, tracker) for tracker in guest.trackers],
            "approval": {
                "kind": approval.kind,
                "until_minutes": _minutes(approval.until, now),
                "valid_now": approval.valid(now),
                "windows": [window.as_dict() for window in approval.windows],
            },
            "rooms": "all" if guest.all_rooms else [room(area) for area in guest.rooms],
            "visit_minutes": guest.visit_minutes,
            "grace_minutes": guest.grace_minutes,
            "log_visits": guest.log_visits,
            "presence": {
                "counting": presence.counting,
                "arrived_minutes": _minutes(presence.arrived, now),
                "visit_ends_minutes": _minutes(presence.visit_ends, now),
                "away_since_minutes": _minutes(presence.away_since, now),
                "resume_until_minutes": _minutes(presence.resume_until, now),
                "time_up": presence.time_up,
                "approval_expired": presence.approval_expired,
            },
            "visit_log": {
                "visits": sum(1 for visit in data.visits if visit.guest_id == guest_id),
                "months": len(data.months.get(guest_id, {})),
            },
        }

    return {
        "about": engine.about,
        "settings": {
            "residents": [_state(hass, person) for person in settings.residents],
            "rooms": [
                {"room": rooms[item.area_id], "door": _state(hass, item.door)}
                for item in settings.rooms
            ],
            "resume_minutes": settings.resume_minutes,
            "log_grid_minutes": settings.log_grid_minutes,
            "log_keep_days": settings.log_keep_days,
            "log_keep_months": settings.log_keep_months,
        },
        "only_guests_home": engine.only_guests_home,
        "lock": {
            "active": data.lock.active,
            "exempt": sorted(room(area) for area in data.lock.exempt),
        },
        "guests": [guest_info(guest_id) for guest_id in data.guests],
        "problems": sorted({problem.key for problem in find_problems(hass, data).values()}),
    }
