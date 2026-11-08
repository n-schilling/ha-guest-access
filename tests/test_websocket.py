"""The commands of the page: administrators only, validated, live updates."""

from __future__ import annotations

from typing import Any

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.guest_access.engine import GuestEngine

from .conftest import DOOR, RESIDENT, TRACKER

GUEST = {
    "type": "guest_access/save_guest",
    "name": "Ben",
    "trackers": ["device_tracker.ben", "device_tracker.ben"],
    "approval": {"kind": "until", "until": "2030-01-01T12:00:00", "window": None},
}


async def test_subscribe(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """The page gets everything now and again after a change."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "guest_access/subscribe"})
    assert (await client.receive_json())["success"]
    first = (await client.receive_json())["event"]
    assert [guest["name"] for guest in first["guests"]] == ["Anna"]
    assert first["guests"][0]["state"]["counting"] is False
    assert first["settings"]["residents"] == [RESIDENT]
    assert first["lock"]["active"] is False

    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    update = (await client.receive_json())["event"]
    assert update["guests"][0]["state"]["counting"] is True
    assert update["guests"][0]["state"]["home"] is True
    assert update["lock"]["only_guests_home"] is True
    assert update["lock"]["locked_rooms"]


async def test_save_lock_delete(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Add a guest, change, lock and delete it."""
    engine: GuestEngine = entry.runtime_data
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(GUEST)
    reply = await client.receive_json()
    assert reply["success"], reply
    guest_id = reply["result"]["guest_id"]
    ben = engine.data.guests[guest_id]
    assert ben.trackers == ("device_tracker.ben",)
    assert ben.approval.until is not None
    assert ben.approval.until.tzinfo is not None
    assert ben.visit_minutes == 60

    room = engine.data.settings.rooms[0].area_id
    await client.send_json_auto_id(
        {
            **GUEST,
            "guest_id": guest_id,
            "name": " Ben B ",
            "approval": {
                "kind": "permanent",
                "window": {"weekdays": [0, 1], "start": "08:00", "end": "18:00"},
            },
            "rooms": [room],
            "visit_minutes": None,
            "grace_minutes": 20,
        }
    )
    assert (await client.receive_json())["success"]
    ben = engine.data.guests[guest_id]
    assert ben.name == "Ben B"
    assert ben.rooms == (room,)
    assert ben.approval.window is not None
    assert ben.visit_minutes is None

    await client.send_json_auto_id({"type": "guest_access/lock_guest", "guest_id": guest_id})
    assert (await client.receive_json())["success"]
    assert engine.data.guests[guest_id].approval.kind == "off"

    await client.send_json_auto_id({"type": "guest_access/delete_guest", "guest_id": guest_id})
    assert (await client.receive_json())["success"]
    assert guest_id not in engine.data.guests

    for command in ("lock_guest", "delete_guest"):
        await client.send_json_auto_id({"type": f"guest_access/{command}", "guest_id": guest_id})
        reply = await client.receive_json()
        assert reply["error"]["code"] == "not_found"
    await client.send_json_auto_id({**GUEST, "guest_id": guest_id})
    assert (await client.receive_json())["error"]["code"] == "not_found"


async def test_save_guest_invalid(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Wrong trackers, unknown rooms and impossible approvals are refused."""
    client = await hass_ws_client(hass)
    for change in (
        {"trackers": ["person.ben"]},
        {"rooms": ["office"]},
        {"approval": {"kind": "once"}},
        {"name": " "},
    ):
        await client.send_json_auto_id({**GUEST, **change})
        reply = await client.receive_json()
        assert reply["error"]["code"] == "invalid_format", change


async def test_save_settings(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator, bedroom: str
) -> None:
    """Residents are persons, doors binary sensors, rooms existing areas."""
    engine: GuestEngine = entry.runtime_data
    client = await hass_ws_client(hass)
    good = {
        "type": "guest_access/save_settings",
        "residents": [RESIDENT, "person.robin"],
        "rooms": [{"area_id": bedroom, "door": DOOR}],
    }
    await client.send_json_auto_id(good)
    assert (await client.receive_json())["success"]
    assert engine.data.settings.residents == (RESIDENT, "person.robin")
    for change in (
        {"residents": ["device_tracker.robin"]},
        {"rooms": [{"area_id": bedroom, "door": "switch.door"}]},
        {"rooms": [{"area_id": "office", "door": DOOR}]},
        {"rooms": [{"area_id": bedroom, "door": DOOR}, {"area_id": bedroom, "door": DOOR}]},
    ):
        await client.send_json_auto_id({**good, **change})
        reply = await client.receive_json()
        assert reply["error"]["code"] == "invalid_format", change


async def test_admin_only(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
) -> None:
    """Users who are not administrators can neither read nor change guests."""
    client = await hass_ws_client(hass, hass_read_only_access_token)
    for message in (
        {"type": "guest_access/subscribe"},
        GUEST,
        {"type": "guest_access/lock_guest", "guest_id": "anna"},
        {"type": "guest_access/delete_guest", "guest_id": "anna"},
        {"type": "guest_access/save_settings", "residents": [], "rooms": []},
    ):
        await client.send_json_auto_id(message)
        reply = await client.receive_json()
        assert reply["error"]["code"] == "unauthorized", message


async def test_not_loaded(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """Without a loaded entry every command says so."""
    assert await hass.config_entries.async_unload(entry.entry_id)
    client = await hass_ws_client(hass)
    messages: list[dict[str, Any]] = [
        {"type": "guest_access/subscribe"},
        GUEST,
        {"type": "guest_access/lock_guest", "guest_id": "anna"},
        {"type": "guest_access/delete_guest", "guest_id": "anna"},
        {"type": "guest_access/save_settings", "residents": [], "rooms": []},
    ]
    for message in messages:
        await client.send_json_auto_id(message)
        reply = await client.receive_json()
        assert reply["error"]["code"] == "not_loaded", message


async def test_subscription_survives_reload(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """An open page keeps getting updates after the entry reloads."""
    assert await async_setup_component(hass, "websocket_api", {})
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "guest_access/subscribe"})
    await client.receive_json()
    await client.receive_json()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    hass.states.async_set(TRACKER, "home")
    await hass.async_block_till_done()
    event = None
    while event is None or not event["guests"][0]["state"]["counting"]:
        event = (await client.receive_json())["event"]
    assert event["guests"][0]["state"]["counting"]
