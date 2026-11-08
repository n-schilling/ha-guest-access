"""Runs the rules: watches trackers, residents and doors, keeps the state, raises the events."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
import logging
from typing import Any
import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_ON
from homeassistant.core import CALLBACK_TYPE, Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_state_change_event,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    EVENT_APPROVAL_CHANGED,
    EVENT_OPENED,
    SIGNAL_CHANGED,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .logic import (
    Observed,
    counting_guests,
    evaluate,
    free_rooms,
    locked_rooms,
    next_wake,
    only_guests_home,
    prepare_restart,
)
from .model import AccessData, Approval, Guest, Settings

_LOGGER = logging.getLogger(__name__)

# Guest id (None for the room lock), event type, event data
type EventListener = Callable[[str | None, str, dict[str, Any]], None]

SAVE_DELAY = 1


class GuestEngine:
    """The guests, their state and the room lock of one config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the engine; async_start loads and starts it."""
        self.hass = hass
        self.entry = entry
        self.data = AccessData()
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._listeners: list[CALLBACK_TYPE] = []
        self._event_listeners: list[EventListener] = []
        self._unsub_states: CALLBACK_TYPE | None = None
        self._unsub_wake: CALLBACK_TYPE | None = None

    # Life cycle

    async def async_start(self) -> None:
        """Load the stored state, carry visits over the restart and start watching."""
        if (stored := await self._store.async_load()) is not None:
            self.data = AccessData.from_dict(stored)
        prepare_restart(self.data, dt_util.utcnow())
        self._watch()
        self._evaluate()

    async def async_stop(self) -> None:
        """Stop watching and save the state, so the next start reads it."""
        if self._unsub_states is not None:
            self._unsub_states()
            self._unsub_states = None
        if self._unsub_wake is not None:
            self._unsub_wake()
            self._unsub_wake = None
        await self._store.async_save(self.data.as_dict())

    # Listeners

    @callback
    def async_add_listener(self, listener: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Call the listener after every change; returns the function that removes it."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def async_add_event_listener(self, listener: EventListener) -> CALLBACK_TYPE:
        """Call the listener for every raised event; returns the function that removes it."""
        self._event_listeners.append(listener)
        return lambda: self._event_listeners.remove(listener)

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()
        async_dispatcher_send(self.hass, SIGNAL_CHANGED)

    def _raise(self, guest_id: str | None, event_type: str, data: dict[str, Any]) -> None:
        for listener in list(self._event_listeners):
            listener(guest_id, event_type, data)

    # Observation

    def _is(self, entity_id: str, state: str) -> bool:
        current = self.hass.states.get(entity_id)
        return current is not None and current.state == state

    def observe(self) -> Observed:
        """What Home Assistant reports right now; unknown and unavailable never count."""
        settings = self.data.settings
        return Observed(
            home={
                guest.id: any(self._is(tracker, STATE_HOME) for tracker in guest.trackers)
                for guest in self.data.guests.values()
            },
            residents_home=any(self._is(person, STATE_HOME) for person in settings.residents),
            open_doors=frozenset(
                room.area_id for room in settings.rooms if self._is(room.door, STATE_ON)
            ),
        )

    def _watch(self) -> None:
        """Follow the trackers, the residents and the doors that are configured now."""
        if self._unsub_states is not None:
            self._unsub_states()
        settings = self.data.settings
        entities = {tracker for guest in self.data.guests.values() for tracker in guest.trackers}
        entities.update(settings.residents)
        entities.update(room.door for room in settings.rooms)
        self._unsub_states = async_track_state_change_event(
            self.hass, sorted(entities), self._state_changed
        )

    @callback
    def _state_changed(self, event: Event[EventStateChangedData]) -> None:
        self._check_door(event)
        self._evaluate()

    def _check_door(self, event: Event[EventStateChangedData]) -> None:
        """Raise a room violation when the door of a locked room opens."""
        new, old = event.data["new_state"], event.data["old_state"]
        if new is None or new.state != STATE_ON or (old is not None and old.state == STATE_ON):
            return
        room = next(
            (room for room in self.data.settings.rooms if room.door == event.data["entity_id"]),
            None,
        )
        if room is None or room.area_id not in locked_rooms(self.data):
            return
        area = ar.async_get(self.hass).async_get_area(room.area_id)
        self._raise(
            None,
            EVENT_OPENED,
            {
                "area_id": room.area_id,
                "area": room.area_id if area is None else area.name,
                "door": room.door,
                "guests": [guest.name for guest in counting_guests(self.data)],
            },
        )

    # Evaluation

    @callback
    def _evaluate(self, _now: datetime | None = None) -> None:
        now = dt_util.utcnow()
        before = self.data.as_dict()
        raised = evaluate(self.data, self.observe(), now)
        self._schedule(now)
        if self.data.as_dict() != before:
            self._save()
        self._notify()
        for item in raised:
            self._raise(item.guest_id, item.event_type, item.data)

    def _schedule(self, now: datetime) -> None:
        if self._unsub_wake is not None:
            self._unsub_wake()
            self._unsub_wake = None
        if (wake := next_wake(self.data, now)) is not None:
            self._unsub_wake = async_track_point_in_utc_time(self.hass, self._wake, wake)

    @callback
    def _wake(self, now: datetime) -> None:
        self._unsub_wake = None
        self._evaluate()

    def _save(self) -> None:
        self._store.async_delay_save(self.data.as_dict, SAVE_DELAY)

    # What the entities and the page read

    def guest(self, guest_id: str) -> Guest | None:
        """A guest, or None when there is no such guest."""
        return self.data.guests.get(guest_id)

    @property
    def only_guests_home(self) -> bool:
        """Whether guests count and no resident is home."""
        return only_guests_home(self.data, self.observe())

    def area_name(self, area_id: str) -> str:
        """The name of an area, or its id when the area is gone."""
        area = ar.async_get(self.hass).async_get_area(area_id)
        return area_id if area is None else area.name

    def summary(self) -> dict[str, Any]:
        """Who counts and which rooms are free or locked, by name."""
        return {
            "guests": [guest.name for guest in counting_guests(self.data)],
            "free_rooms": sorted(self.area_name(area) for area in free_rooms(self.data)),
            "locked_rooms": sorted(self.area_name(area) for area in locked_rooms(self.data)),
        }

    def snapshot(self) -> dict[str, Any]:
        """Everything the page shows."""
        now = dt_util.utcnow()
        observed = self.observe()
        guests = []
        for guest in self.data.guests.values():
            presence = self.data.presence_of(guest.id)
            guests.append(
                {
                    **guest.as_dict(),
                    "state": {
                        **presence.as_dict(),
                        "home": observed.home.get(guest.id, False),
                        "approval_valid": guest.approval.valid(now),
                    },
                }
            )
        return {
            "settings": self.data.settings.as_dict(),
            "guests": sorted(guests, key=lambda guest: str(guest["name"]).casefold()),
            "lock": {
                **self.data.lock.as_dict(),
                "only_guests_home": only_guests_home(self.data, observed),
                "free_rooms": sorted(free_rooms(self.data)),
                "locked_rooms": sorted(locked_rooms(self.data)),
            },
        }

    # Changes by administrators

    def new_guest_id(self) -> str:
        """An id for a new guest."""
        return uuid.uuid4().hex

    @callback
    def async_save_guest(self, guest: Guest) -> None:
        """Add or change a guest."""
        old = self.data.guests.get(guest.id)
        self.data.guests[guest.id] = guest
        presence = self.data.presence_of(guest.id)
        if old is not None and presence.counting:
            if old.visit_minutes != guest.visit_minutes and presence.arrived is not None:
                # A new time per visit counts from the arrival
                presence.visit_ends = (
                    None if guest.visit is None else presence.arrived + guest.visit
                )
                presence.time_up = False
            if old.approval != guest.approval:
                presence.approval_expired = False
        if old is not None and old.approval != guest.approval:
            # A new approval starts afresh, also the grace time of a once approval
            presence.away_since = None
        if old is not None and old.name != guest.name:
            self._rename_device(guest)
        self._watch()
        self._evaluate()
        if old is None or old.approval != guest.approval:
            self._raise(guest.id, EVENT_APPROVAL_CHANGED, guest.approval.as_dict())

    @callback
    def async_lock_guest(self, guest_id: str) -> None:
        """Take a guest's approval away; the guest no longer counts."""
        guest = self.data.guests[guest_id]
        self.async_save_guest(replace(guest, approval=Approval()))

    @callback
    def async_delete_guest(self, guest_id: str) -> None:
        """Remove a guest with the device and its entities."""
        self.data.guests.pop(guest_id)
        self.data.presence.pop(guest_id, None)
        registry = dr.async_get(self.hass)
        if (
            device := registry.async_get_device_by_identifier(
                (DOMAIN, guest_id), self.entry.entry_id
            )
        ) is not None:
            registry.async_remove_device(device.id)
        self._watch()
        self._evaluate()

    @callback
    def async_save_settings(self, settings: Settings) -> None:
        """Change the residents and the lockable rooms."""
        self.data.settings = settings
        self._watch()
        self._evaluate()

    def _rename_device(self, guest: Guest) -> None:
        registry = dr.async_get(self.hass)
        if (
            device := registry.async_get_device_by_identifier(
                (DOMAIN, guest.id), self.entry.entry_id
            )
        ) is not None:
            registry.async_update_device(device.id, name=guest.name)
