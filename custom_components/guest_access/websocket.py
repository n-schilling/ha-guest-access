"""WebSocket commands of the page; administrators only."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import probatio

from homeassistant.components.websocket_api import async_register_command
from homeassistant.components.websocket_api.connection import ActiveConnection
from homeassistant.components.websocket_api.const import ERR_INVALID_FORMAT, ERR_NOT_FOUND
from homeassistant.components.websocket_api.decorators import require_admin, websocket_command
from homeassistant.components.websocket_api.messages import event_message
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util
from homeassistant.util.hass_dict import HassKey

from .const import (
    DOMAIN,
    MAX_GRACE_MINUTES,
    SIGNAL_CHANGED,
    VISIT_CHOICES,
    WS_DELETE_GUEST,
    WS_LOCK_GUEST,
    WS_SAVE_GUEST,
    WS_SAVE_SETTINGS,
    WS_SUBSCRIBE,
)
from .model import Approval, ApprovalKind, Guest, Room, Settings, Window

if TYPE_CHECKING:
    from .engine import GuestEngine

ERR_NOT_LOADED = "not_loaded"
DATA_REGISTERED: HassKey[bool] = HassKey(f"{DOMAIN}_websocket")

WINDOW = {
    probatio.Required("weekdays"): [probatio.All(probatio.Coerce(int), probatio.Range(0, 6))],
    probatio.Required("start"): cv.time,
    probatio.Required("end"): cv.time,
}
APPROVAL = {
    probatio.Required("kind"): probatio.In([kind.value for kind in ApprovalKind]),
    probatio.Optional("until"): probatio.Any(None, cv.datetime),
    probatio.Optional("windows", default=[]): [WINDOW],
}
ROOM = {probatio.Required("area_id"): cv.string, probatio.Required("door"): cv.entity_id}


@callback
def async_register_websocket(hass: HomeAssistant) -> None:
    """Register the commands once per run."""
    if DATA_REGISTERED in hass.data:
        return
    hass.data[DATA_REGISTERED] = True
    for command in (ws_subscribe, ws_save_guest, ws_delete_guest, ws_lock_guest, ws_save_settings):
        async_register_command(hass, command)


def _engine(hass: HomeAssistant, connection: ActiveConnection, msg_id: int) -> GuestEngine | None:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        connection.send_error(msg_id, ERR_NOT_LOADED, "Guest Access is not set up")
        return None
    engine: GuestEngine = entries[0].runtime_data
    return engine


def _aware(moment: datetime | None) -> datetime | None:
    if moment is None or moment.tzinfo is not None:
        return moment
    return moment.replace(tzinfo=dt_util.get_default_time_zone())


def _check_domain(entity_ids: list[str], domain: str, what: str) -> None:
    if wrong := [entity_id for entity_id in entity_ids if not entity_id.startswith(f"{domain}.")]:
        raise ValueError(f"{what} must be {domain} entities: {', '.join(wrong)}")


@require_admin
@websocket_command({probatio.Required("type"): WS_SUBSCRIBE})
@callback
def ws_subscribe(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None:
    """Send the guests, their state and the settings now and after every change."""
    msg_id = msg["id"]

    @callback
    def _send() -> None:
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if entries:
            engine: GuestEngine = entries[0].runtime_data
            connection.send_message(event_message(msg_id, engine.snapshot()))

    if _engine(hass, connection, msg_id) is None:
        return
    connection.subscriptions[msg_id] = async_dispatcher_connect(hass, SIGNAL_CHANGED, _send)
    connection.send_result(msg_id)
    _send()


@require_admin
@websocket_command(
    {
        probatio.Required("type"): WS_SAVE_GUEST,
        probatio.Optional("guest_id"): cv.string,
        probatio.Required("name"): cv.string,
        probatio.Required("trackers"): [cv.entity_id],
        probatio.Required("approval"): APPROVAL,
        probatio.Optional("rooms", default=[]): [cv.string],
        probatio.Optional("all_rooms", default=False): cv.boolean,
        probatio.Optional("visit_minutes", default=60): probatio.In(list(VISIT_CHOICES)),
        probatio.Optional("grace_minutes", default=15): probatio.All(
            probatio.Coerce(int), probatio.Range(1, MAX_GRACE_MINUTES)
        ),
    }
)
@callback
def ws_save_guest(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None:
    """Add a guest, or change one when an id is given."""
    if (engine := _engine(hass, connection, msg["id"])) is None:
        return
    guest_id = msg.get("guest_id")
    if guest_id is not None and engine.guest(guest_id) is None:
        connection.send_error(msg["id"], ERR_NOT_FOUND, f"no guest {guest_id}")
        return
    try:
        _check_domain(msg["trackers"], "device_tracker", "trackers")
        configured = {room.area_id for room in engine.data.settings.rooms}
        if unknown := set(msg["rooms"]) - configured:
            raise ValueError(f"not a lockable room: {', '.join(sorted(unknown))}")
        raw = msg["approval"]
        guest = Guest(
            id=guest_id or engine.new_guest_id(),
            name=msg["name"].strip(),
            trackers=tuple(dict.fromkeys(msg["trackers"])),
            approval=Approval(
                ApprovalKind(raw["kind"]),
                _aware(raw.get("until")),
                tuple(
                    Window(frozenset(window["weekdays"]), window["start"], window["end"])
                    for window in raw["windows"]
                ),
            ),
            rooms=tuple(dict.fromkeys(msg["rooms"])),
            all_rooms=msg["all_rooms"],
            visit_minutes=msg["visit_minutes"],
            grace_minutes=msg["grace_minutes"],
        )
    except ValueError as err:
        connection.send_error(msg["id"], ERR_INVALID_FORMAT, str(err))
        return
    engine.async_save_guest(guest, connection.context(msg), connection.user.name)
    connection.send_result(msg["id"], {"guest_id": guest.id})


@require_admin
@websocket_command(
    {probatio.Required("type"): WS_DELETE_GUEST, probatio.Required("guest_id"): cv.string}
)
@callback
def ws_delete_guest(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None:
    """Remove a guest with its device."""
    if (engine := _engine(hass, connection, msg["id"])) is None:
        return
    if engine.guest(msg["guest_id"]) is None:
        connection.send_error(msg["id"], ERR_NOT_FOUND, f"no guest {msg['guest_id']}")
        return
    engine.async_delete_guest(msg["guest_id"])
    connection.send_result(msg["id"])


@require_admin
@websocket_command(
    {probatio.Required("type"): WS_LOCK_GUEST, probatio.Required("guest_id"): cv.string}
)
@callback
def ws_lock_guest(hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]) -> None:
    """Take a guest's approval away at once."""
    if (engine := _engine(hass, connection, msg["id"])) is None:
        return
    if engine.guest(msg["guest_id"]) is None:
        connection.send_error(msg["id"], ERR_NOT_FOUND, f"no guest {msg['guest_id']}")
        return
    engine.async_lock_guest(msg["guest_id"], connection.context(msg), connection.user.name)
    connection.send_result(msg["id"])


@require_admin
@websocket_command(
    {
        probatio.Required("type"): WS_SAVE_SETTINGS,
        probatio.Required("residents"): [cv.entity_id],
        probatio.Required("rooms"): [ROOM],
    }
)
@callback
def ws_save_settings(
    hass: HomeAssistant, connection: ActiveConnection, msg: dict[str, Any]
) -> None:
    """Change the residents and the lockable rooms."""
    if (engine := _engine(hass, connection, msg["id"])) is None:
        return
    areas = ar.async_get(hass)
    try:
        _check_domain(msg["residents"], "person", "residents")
        _check_domain([room["door"] for room in msg["rooms"]], "binary_sensor", "doors")
        if unknown := [
            room["area_id"]
            for room in msg["rooms"]
            if areas.async_get_area(room["area_id"]) is None
        ]:
            raise ValueError(f"no area {', '.join(unknown)}")
        settings = Settings(
            tuple(dict.fromkeys(msg["residents"])),
            tuple(Room(room["area_id"], room["door"]) for room in msg["rooms"]),
        )
    except ValueError as err:
        connection.send_error(msg["id"], ERR_INVALID_FORMAT, str(err))
        return
    engine.async_save_settings(settings)
    connection.send_result(msg["id"])
