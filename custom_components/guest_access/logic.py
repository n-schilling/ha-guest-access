"""The rules: who counts, when a visit or an approval ends, which rooms are locked.

Pure functions over the stored data and what Home Assistant reports right now;
the engine feeds them and turns what they raise into entity events.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from .const import (
    EVENT_APPROVAL_CHANGED,
    EVENT_APPROVAL_EXPIRED,
    EVENT_ARRIVED,
    EVENT_LEFT,
    EVENT_TIME_UP,
    RESUME_WINDOW,
)
from .model import AccessData, Approval, ApprovalKind, Guest, Lock, Presence


@dataclass(frozen=True, slots=True)
class Observed:
    """What Home Assistant reports right now."""

    # Guest id: one of the guest's trackers is home
    home: Mapping[str, bool]
    residents_home: bool
    # Areas of lockable rooms whose door is open
    open_doors: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class Raised:
    """An event for a guest's event entity."""

    guest_id: str
    event_type: str
    data: dict[str, Any] = field(default_factory=dict)


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.isoformat()


def prepare_restart(data: AccessData, now: datetime) -> None:
    """After a start: guests who counted keep their visit if a tracker returns soon.

    Until then they do not count, as nothing is known about their trackers yet.
    """
    for guest_id in data.guests:
        presence = data.presence_of(guest_id)
        if presence.counting:
            presence.counting = False
            presence.resume_until = now + RESUME_WINDOW


def _arrive(guest: Guest, presence: Presence, now: datetime) -> Raised:
    presence.end_visit()
    presence.counting = True
    presence.arrived = now
    presence.visit_ends = None if guest.visit is None else now + guest.visit
    return Raised(guest.id, EVENT_ARRIVED, {"visit_ends": _iso(presence.visit_ends)})


def _leave(guest: Guest, presence: Presence, now: datetime) -> Raised:
    presence.end_visit()
    if guest.approval.kind is ApprovalKind.ONCE:
        presence.away_since = now
    return Raised(guest.id, EVENT_LEFT)


def _check_counting(guest: Guest, presence: Presence, now: datetime) -> list[Raised]:
    """A guest who counts keeps counting until leaving; raise expiries once."""
    raised = []
    if presence.visit_ends is not None and now >= presence.visit_ends and not presence.time_up:
        presence.time_up = True
        raised.append(Raised(guest.id, EVENT_TIME_UP, {"visit_ends": _iso(presence.visit_ends)}))
    if not guest.approval.valid(now) and not presence.approval_expired:
        presence.approval_expired = True
        raised.append(Raised(guest.id, EVENT_APPROVAL_EXPIRED, guest.approval.as_dict()))
    return raised


def _evaluate_guest(data: AccessData, guest: Guest, home: bool, now: datetime) -> list[Raised]:
    presence = data.presence_of(guest.id)
    if home:
        presence.away_since = None
    if presence.counting:
        if guest.approval.kind is ApprovalKind.OFF:
            # Locked by an administrator: no longer counts, wherever the guest is
            presence.end_visit()
            return []
        if not home:
            return [_leave(guest, presence, now)]
        return _check_counting(guest, presence, now)
    resuming = presence.resume_until is not None and now < presence.resume_until
    if home and resuming and guest.approval.kind is not ApprovalKind.OFF:
        # Back after a restart: the visit goes on, its end stays
        presence.counting = True
        presence.resume_until = None
        return _check_counting(guest, presence, now)
    if home and guest.approval.valid(now):
        return [_arrive(guest, presence, now), *_check_counting(guest, presence, now)]
    raised = []
    if presence.resume_until is not None and not resuming:
        # Not back after a restart: the guest left in the meantime
        raised.append(_leave(guest, presence, now))
    if (
        guest.approval.kind is ApprovalKind.ONCE
        and presence.away_since is not None
        and now >= presence.away_since + guest.grace
    ):
        # One visit, and it is over
        data.guests[guest.id] = replace(guest, approval=Approval())
        presence.away_since = None
        raised.append(
            Raised(
                guest.id,
                EVENT_APPROVAL_CHANGED,
                {**Approval().as_dict(), "reason": "visit_over"},
            )
        )
    return raised


def counting_guests(data: AccessData) -> list[Guest]:
    """The guests who count right now."""
    return [guest for guest in data.guests.values() if data.presence_of(guest.id).counting]


def free_rooms(data: AccessData) -> frozenset[str]:
    """The lockable rooms the guests who count may enter together."""
    configured = frozenset(room.area_id for room in data.settings.rooms)
    free: set[str] = set()
    for guest in counting_guests(data):
        if guest.all_rooms:
            return configured
        free.update(guest.rooms)
    return frozenset(free) & configured


def locked_rooms(data: AccessData) -> frozenset[str]:
    """The rooms that are locked right now."""
    if not data.lock.active:
        return frozenset()
    configured = frozenset(room.area_id for room in data.settings.rooms)
    return configured - free_rooms(data) - data.lock.exempt


def _update_lock(data: AccessData, observed: Observed) -> None:
    counting = bool(counting_guests(data))
    resuming = any(data.presence_of(guest_id).resume_until is not None for guest_id in data.guests)
    if observed.residents_home or not (counting or resuming):
        data.lock = Lock()
    elif counting and not data.lock.active:
        configured = frozenset(room.area_id for room in data.settings.rooms)
        data.lock = Lock(True, observed.open_doors & configured)


def evaluate(data: AccessData, observed: Observed, now: datetime) -> list[Raised]:
    """Apply the rules to the data, in place; return what to raise."""
    raised: list[Raised] = []
    for guest in list(data.guests.values()):
        raised.extend(_evaluate_guest(data, guest, observed.home.get(guest.id, False), now))
    _update_lock(data, observed)
    return raised


def only_guests_home(data: AccessData, observed: Observed) -> bool:
    """Whether guests count and no resident is home."""
    return bool(counting_guests(data)) and not observed.residents_home


def next_wake(data: AccessData, now: datetime) -> datetime | None:
    """The next moment the rules may come to another result without a state change."""
    candidates: list[datetime] = []
    for guest in data.guests.values():
        presence = data.presence_of(guest.id)
        if (change := guest.approval.next_change(now)) is not None:
            candidates.append(change)
        if presence.counting and presence.visit_ends is not None and not presence.time_up:
            candidates.append(presence.visit_ends)
        if presence.resume_until is not None:
            candidates.append(presence.resume_until)
        if guest.approval.kind is ApprovalKind.ONCE and presence.away_since is not None:
            candidates.append(presence.away_since + guest.grace)
    return min((moment for moment in candidates if moment > now), default=None)
