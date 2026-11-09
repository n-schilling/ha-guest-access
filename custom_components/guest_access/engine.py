"""Runs the rules: watches trackers, residents and doors, keeps the state, raises the events."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
import logging
from pathlib import Path
from typing import Any
import uuid

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_HOME, STATE_OFF, STATE_ON, Platform
from homeassistant.core import (
    CALLBACK_TYPE,
    Context,
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_state_change_event,
)
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.storage import Store
from homeassistant.helpers.translation import async_get_translations
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from .const import (
    BUILD_FILE,
    DOMAIN,
    EVENT_APPROVAL_CHANGED,
    EVENT_OPENED,
    SIGNAL_CHANGED,
    STORAGE_KEY,
    STORAGE_VERSION,
)
from .issues import async_update_issues
from .logic import (
    GuestStatus,
    Observed,
    counting_guests,
    evaluate,
    forget_log,
    free_rooms,
    guest_status,
    locked_rooms,
    month_key,
    next_wake,
    only_guests_home,
    prepare_restart,
)
from .model import AccessData, Approval, Guest, Settings

_LOGGER = logging.getLogger(__name__)

# Guest id (None for the room lock), event type, event data, and the context of
# the administrator's change when one caused it
type EventListener = Callable[[str | None, str, dict[str, Any], Context | None], None]

SAVE_DELAY = 1
# Events kept for an event entity that is not there yet, per guest
QUEUE_LIMIT = 10


class GuestEngine:
    """The guests, their state and the room lock of one config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the engine; async_start loads and starts it."""
        self.hass = hass
        self.entry = entry
        self.data = AccessData()
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._listeners: list[CALLBACK_TYPE] = []
        # Per guest id, None for the room violation
        self._event_listeners: dict[str | None, list[EventListener]] = {}
        self._queued: dict[str | None, list[tuple[str, dict[str, Any], Context | None]]] = {}
        self._unsub_states: CALLBACK_TYPE | None = None
        self._unsub_wake: CALLBACK_TYPE | None = None
        self._unsub_other: list[CALLBACK_TYPE] = []
        self._issues_active = False
        # Door contact: its last real state, on or off
        self._doors: dict[str, str] = {}
        # Shown on the page: the version and the commit it was deployed from
        self.about: dict[str, str | None] = {"version": None, "commit": None}
        # Entity names in the language of Home Assistant, for the IDs of new entities
        self._entity_names: dict[str, str] = {}

    # Life cycle

    async def async_start(self) -> None:
        """Load the stored state, carry visits over the restart and evaluate once.

        The evaluation comes before the entities are added, so they start with the
        right state: on a reload a guest who is home never shows as gone. Events
        raised now wait for their entity.
        """
        if (stored := await self._store.async_load()) is not None:
            self.data = AccessData.from_dict(stored)
        self._entity_names = await async_get_translations(
            self.hass, self.hass.config.language, "entity", {DOMAIN}
        )
        integration = await async_get_integration(self.hass, DOMAIN)
        commit = await self.hass.async_add_executor_job(_read_commit)
        self.about = {"version": str(integration.version), "commit": commit}
        prepare_restart(self.data, dt_util.utcnow())
        self._evaluate()

    @callback
    def async_begin(self) -> None:
        """Start watching and evaluating, once the entities are there to raise events.

        Repairs are checked only once Home Assistant has started, when every
        integration had the chance to create its entities.
        """
        self._watch()
        self._evaluate()

        @callback
        def _registry_changed(_event: Event[Any]) -> None:
            self._check_issues()

        @callback
        def _started(_hass: HomeAssistant) -> None:
            self._issues_active = True
            self._check_issues()

        self._unsub_other.extend(
            [
                self.hass.bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, _registry_changed),
                self.hass.bus.async_listen(ar.EVENT_AREA_REGISTRY_UPDATED, _registry_changed),
                async_at_started(self.hass, _started),
            ]
        )

    def _check_issues(self) -> None:
        if self._issues_active:
            async_update_issues(self.hass, self.data)

    async def async_stop(self) -> None:
        """Stop watching and save the state, so the next start reads it."""
        if self._unsub_states is not None:
            self._unsub_states()
            self._unsub_states = None
        if self._unsub_wake is not None:
            self._unsub_wake()
            self._unsub_wake = None
        while self._unsub_other:
            self._unsub_other.pop()()
        self._issues_active = False
        await self._store.async_save(self.data.as_dict())

    # Listeners

    @callback
    def async_add_listener(self, listener: CALLBACK_TYPE) -> CALLBACK_TYPE:
        """Call the listener after every change; returns the function that removes it."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def async_add_event_listener(
        self, listener: EventListener, guest_id: str | None = None
    ) -> CALLBACK_TYPE:
        """Call the listener for the events of a guest, or of the room lock with None.

        Events raised before the first listener of their guest was there, as for a
        guest whose entities are still being added, reach it now.
        """
        self._event_listeners.setdefault(guest_id, []).append(listener)
        for event_type, data, context in self._queued.pop(guest_id, []):
            listener(guest_id, event_type, data, context)

        def _remove() -> None:
            self._event_listeners[guest_id].remove(listener)

        return _remove

    def _notify(self) -> None:
        for listener in list(self._listeners):
            listener()
        async_dispatcher_send(self.hass, SIGNAL_CHANGED)

    def _raise(
        self,
        guest_id: str | None,
        event_type: str,
        data: dict[str, Any],
        context: Context | None = None,
    ) -> None:
        listeners = self._event_listeners.get(guest_id)
        if not listeners:
            queue = self._queued.setdefault(guest_id, [])
            queue.append((event_type, data, context))
            del queue[:-QUEUE_LIMIT]
            return
        for listener in list(listeners):
            listener(guest_id, event_type, data, context)

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
        for room in settings.rooms:
            if (current := self.hass.states.get(room.door)) is not None:
                self._remember_door(room.door, current.state)
        self._unsub_states = async_track_state_change_event(
            self.hass, sorted(entities), self._state_changed
        )

    def _remember_door(self, entity_id: str, state: str) -> None:
        """Keep the last real state of a door; unavailable and unknown keep the one before."""
        if state in (STATE_ON, STATE_OFF):
            self._doors[entity_id] = state

    @callback
    def _state_changed(self, event: Event[EventStateChangedData]) -> None:
        new, old = event.data["new_state"], event.data["old_state"]
        if new is not None and old is not None and new.state == old.state:
            # Only attributes changed, as with a tracker's position: nothing to decide
            return
        self._check_door(event)
        self._evaluate()
        if new is None or old is None:
            # An entity appeared or went away: a repair may open or close. Other
            # state changes cannot change what is missing.
            self._check_issues()

    def _check_door(self, event: Event[EventStateChangedData]) -> None:
        """Raise a room violation when the door of a locked room opens."""
        new = event.data["new_state"]
        entity_id = event.data["entity_id"]
        if new is None:
            return
        # An opening is closed to open against the last known real state, so a
        # door opened while its contact was unavailable counts once it reports,
        # and a contact that returns to the same open door does not
        was = self._doors.get(entity_id)
        self._remember_door(entity_id, new.state)
        if new.state != STATE_ON or was != STATE_OFF:
            return
        room = next(
            (room for room in self.data.settings.rooms if room.door == entity_id),
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
        # The month's hours start again at the first of the month
        wakes = [_next_month(now)]
        if (wake := next_wake(self.data, now)) is not None:
            wakes.append(wake)
        self._unsub_wake = async_track_point_in_utc_time(self.hass, self._wake, min(wakes))

    @callback
    def _wake(self, now: datetime) -> None:
        self._unsub_wake = None
        self._evaluate()

    def _save(self) -> None:
        self._store.async_delay_save(self.data.as_dict, SAVE_DELAY)

    # What the entities and the page read

    def entity_name(self, platform: str, key: str) -> str:
        """The name of an entity in the language of Home Assistant, or its key."""
        return self._entity_names.get(f"component.{DOMAIN}.entity.{platform}.{key}.name", key)

    def guest(self, guest_id: str) -> Guest | None:
        """A guest, or None when there is no such guest."""
        return self.data.guests.get(guest_id)

    def status(self, guest_id: str) -> GuestStatus:
        """The status of a guest."""
        guest = self.data.guests[guest_id]
        home = any(self._is(tracker, STATE_HOME) for tracker in guest.trackers)
        return guest_status(
            self.data.guests[guest_id], self.data.presence_of(guest_id), home, dt_util.utcnow()
        )

    @property
    def only_guests_home(self) -> bool:
        """Whether guests count and no resident is home."""
        return only_guests_home(self.data, self.observe())

    def area_name(self, area_id: str) -> str:
        """The name of an area, or its id when the area is gone."""
        area = ar.async_get(self.hass).async_get_area(area_id)
        return area_id if area is None else area.name

    def summary(self) -> dict[str, Any]:
        """Who counts and which rooms are free or locked, by name; the guests to show."""
        return {
            "guests": [guest.name for guest in counting_guests(self.data)],
            "free_rooms": sorted(self.area_name(area) for area in free_rooms(self.data)),
            "locked_rooms": sorted(self.area_name(area) for area in locked_rooms(self.data)),
            "guest_list": self.guest_list(),
        }

    def guest_list(self) -> list[dict[str, Any]]:
        """Every guest except inactive ones, by name, for a dashboard to show as it is.

        Each entry has the guest's name (as the device is named), the status, the
        status sensor to show the status in the user's language, and the end of the
        visit while the guest counts with time left or time up.
        """
        devices = dr.async_get(self.hass)
        entities = er.async_get(self.hass)
        shown = []
        for guest in self.data.guests.values():
            status = self.status(guest.id)
            if status is GuestStatus.INACTIVE:
                continue
            device = devices.async_get_device_by_identifier((DOMAIN, guest.id), self.entry.entry_id)
            presence = self.data.presence_of(guest.id)
            ends = (
                presence.visit_ends
                if presence.counting and status in (GuestStatus.COUNTING, GuestStatus.TIME_UP)
                else None
            )
            shown.append(
                {
                    "name": device.name_by_user if device and device.name_by_user else guest.name,
                    "status": status.value,
                    "status_entity": entities.async_get_entity_id(
                        Platform.SENSOR, DOMAIN, f"{guest.id}_status"
                    ),
                    # As the visit-end sensor shows it, to the second
                    "visit_ends": None if ends is None else ends.replace(microsecond=0).isoformat(),
                }
            )
        return sorted(shown, key=lambda item: item["name"])

    def snapshot(self) -> dict[str, Any]:
        """Everything the page shows."""
        now = dt_util.utcnow()
        observed = self.observe()
        guests = []
        for guest in self.data.guests.values():
            presence = self.data.presence_of(guest.id)
            visits = sorted(
                (visit for visit in self.data.visits if visit.guest_id == guest.id),
                key=lambda visit: visit.start,
                reverse=True,
            )
            guests.append(
                {
                    **guest.as_dict(),
                    "state": {
                        **presence.as_dict(),
                        "home": observed.home.get(guest.id, False),
                        "approval_valid": guest.approval.valid(now),
                        "status": guest_status(
                            guest, presence, observed.home.get(guest.id, False), now
                        ).value,
                    },
                    "log": {
                        "visits": [
                            {"start": visit.start.isoformat(), "minutes": visit.minutes}
                            for visit in visits
                        ],
                        "months": {
                            month: total.as_dict()
                            for month, total in sorted(self.data.months.get(guest.id, {}).items())
                        },
                        "this_month": month_key(now),
                    },
                }
            )
        return {
            "about": self.about,
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
    def async_save_guest(
        self, guest: Guest, context: Context | None = None, by: str | None = None
    ) -> None:
        """Add or change a guest; context and name of the administrator go with the event."""
        old = self.data.guests.get(guest.id)
        self.data.guests[guest.id] = guest
        presence = self.data.presence_of(guest.id)
        if (
            old is not None
            and old.visit_minutes != guest.visit_minutes
            and presence.arrived is not None
        ):
            # A new time per visit counts from the arrival, also for a visit that
            # goes on after the grace time or a restart
            presence.visit_ends = None if guest.visit is None else presence.arrived + guest.visit
            presence.time_up = False
        if old is not None and old.approval != guest.approval:
            # A new approval starts afresh, also the grace time of a once approval.
            # An expiry already raised for this visit is not raised again; a valid
            # approval clears it in the evaluation.
            presence.away_since = None
        if old is not None and old.name != guest.name:
            self._rename_device(guest)
        if old is not None and old.log_visits and not guest.log_visits:
            # No log means none at all: the one kept so far goes
            forget_log(self.data, guest.id)
        if old is None or old.approval != guest.approval:
            # First the change, then what follows from it (arrived, left); a new
            # guest's event waits until its entity is there
            self._raise(
                guest.id,
                EVENT_APPROVAL_CHANGED,
                {**guest.approval.as_dict(), "reason": "changed", "by": by},
                context,
            )
        self._watch()
        self._evaluate()
        # The evaluation saves only what it changes itself, not this change
        self._save()
        self._check_issues()

    @callback
    def async_lock_guest(
        self, guest_id: str, context: Context | None = None, by: str | None = None
    ) -> None:
        """Take a guest's approval away; the guest no longer counts."""
        guest = self.data.guests[guest_id]
        self.async_save_guest(replace(guest, approval=Approval()), context, by)

    @callback
    def async_delete_guest(self, guest_id: str) -> None:
        """Remove a guest with the device and its entities."""
        self.data.guests.pop(guest_id)
        self.data.presence.pop(guest_id, None)
        self._queued.pop(guest_id, None)
        forget_log(self.data, guest_id)
        registry = dr.async_get(self.hass)
        if (
            device := registry.async_get_device_by_identifier(
                (DOMAIN, guest_id), self.entry.entry_id
            )
        ) is not None:
            registry.async_remove_device(device.id)
        self._watch()
        self._evaluate()
        self._save()
        self._check_issues()

    @callback
    def async_save_settings(self, settings: Settings) -> None:
        """Change the residents and the lockable rooms."""
        before = {room.area_id for room in self.data.settings.rooms}
        self.data.settings = settings
        configured = {room.area_id for room in settings.rooms}
        lock = self.data.lock
        if lock.active:
            # A room that becomes lockable during the lock is treated like one at its
            # start: free for this lock when its door is open now
            opened = {
                room.area_id
                for room in settings.rooms
                if room.area_id not in before and self._is(room.door, STATE_ON)
            }
            self.data.lock = replace(lock, exempt=(lock.exempt | opened) & configured)
        for guest in list(self.data.guests.values()):
            if not set(guest.rooms) <= configured:
                # A room that is no longer lockable leaves the guests' rooms
                kept = tuple(area for area in guest.rooms if area in configured)
                self.data.guests[guest.id] = replace(guest, rooms=kept)
        self._watch()
        self._evaluate()
        self._save()
        self._check_issues()

    @callback
    def async_delete_visits(self, guest_id: str) -> None:
        """Delete a guest's visit log."""
        forget_log(self.data, guest_id)
        self._save()
        self._notify()

    def _rename_device(self, guest: Guest) -> None:
        registry = dr.async_get(self.hass)
        if (
            device := registry.async_get_device_by_identifier(
                (DOMAIN, guest.id), self.entry.entry_id
            )
        ) is not None:
            registry.async_update_device(device.id, name=guest.name)


def _next_month(now: datetime) -> datetime:
    """The start of the next local month, in UTC."""
    local = dt_util.as_local(now)
    year, month = (local.year + 1, 1) if local.month == 12 else (local.year, local.month + 1)
    return dt_util.as_utc(
        local.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
    )


def _read_commit() -> str | None:
    """The commit the integration was deployed from, written by the deploy script."""
    try:
        return (Path(__file__).parent / BUILD_FILE).read_text(encoding="utf-8").strip() or None
    except OSError:
        return None
