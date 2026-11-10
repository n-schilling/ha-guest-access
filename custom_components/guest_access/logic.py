"""The rules: who counts, when a visit or an approval ends, which rooms are locked.

Pure functions over the stored data and what Home Assistant reports right now;
the engine feeds them and turns what they raise into entity events.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    EVENT_APPROVAL_CHANGED,
    EVENT_APPROVAL_EXPIRED,
    EVENT_ARRIVED,
    EVENT_LEFT,
    EVENT_TIME_UP,
)
from .model import AccessData, Approval, ApprovalKind, Guest, Lock, MonthTotal, Presence, Visit


class GuestStatus(StrEnum):
    """What a guest's status sensor shows."""

    # Counts, nothing has run out
    COUNTING = "counting"
    # Counts, the time per visit is up
    TIME_UP = "time_up"
    # Counts, the approval ended while the guest was home
    APPROVAL_EXPIRED = "approval_expired"
    # A tracker is home, but the approval does not let the guest count
    NOT_APPROVED = "not_approved"
    # After a restart: waiting for a tracker to continue the visit
    RESUMING = "resuming"
    # Approved, but not home
    AWAY = "away"
    # Not home and no approval (locked, or its end has passed)
    INACTIVE = "inactive"


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


def iso_seconds(moment: datetime | None) -> str | None:
    """A time for events and attributes: ISO 8601 to the second, as the sensors show it."""
    return None if moment is None else moment.replace(microsecond=0).isoformat()


def prepare_restart(data: AccessData, now: datetime) -> None:
    """After a start: guests who counted keep their visit if a tracker returns soon.

    Until then they do not count, as nothing is known about their trackers yet.
    """
    for guest_id in data.guests:
        presence = data.presence_of(guest_id)
        if presence.counting:
            presence.counting = False
            presence.resume_until = now + data.settings.resume_window
            presence.restarted = now


def _restarted(data: AccessData, presence: Presence) -> datetime:
    """When Home Assistant started, for a guest waiting to resume."""
    if presence.restarted is not None:
        return presence.restarted
    # Stored by a version that did not keep the start
    assert presence.resume_until is not None
    return presence.resume_until - data.settings.resume_window


def _grid(moment: datetime, grid: timedelta) -> datetime:
    """The nearest point on the grid, counted from local midnight, so 14:00 stays 14:00."""
    local = dt_util.as_local(moment)
    midnight = dt_util.start_of_local_day(local)
    step = grid.total_seconds()
    since = round((local - midnight).total_seconds() / step) * step
    return dt_util.as_utc(midnight + timedelta(seconds=since))


def month_key(moment: datetime) -> str:
    """The local month of a moment, as the visit log keys it."""
    return dt_util.as_local(moment).strftime("%Y-%m")


def _finish(data: AccessData, guest: Guest, presence: Presence, end: datetime) -> None:
    """End the visit; log it, rounded, when the guest keeps a visit log."""
    if guest.log_visits and presence.arrived is not None:
        grid = data.settings.log_grid
        start = _grid(presence.arrived, grid)
        # A visit takes at least one step of the grid
        minutes = max(round((end - presence.arrived) / grid), 1) * data.settings.log_grid_minutes
        data.visits.append(Visit(guest.id, start, minutes))
        totals = data.months.setdefault(guest.id, {})
        month = month_key(start)
        total = totals.get(month, MonthTotal())
        totals[month] = MonthTotal(total.visits + 1, total.minutes + minutes)
    presence.end_visit()


def end_absent_visit(data: AccessData, guest: Guest, presence: Presence) -> None:
    """End a visit whose guest is away within the grace time, where the guest left.

    For a change of the approval, which starts afresh: a return afterwards is a
    new visit, and the one before is logged as it was.
    """
    if not presence.counting and presence.away_since is not None and presence.arrived is not None:
        _finish(data, guest, presence, presence.away_since)
    presence.away_since = None


def prune_log(data: AccessData, now: datetime) -> None:
    """Forget single visits and monthly totals once they are older than the settings keep them."""
    keep = timedelta(days=data.settings.log_keep_days)
    data.visits = [visit for visit in data.visits if now - visit.start < keep]
    local = dt_util.as_local(now)
    oldest = local.year * 12 + local.month - 1 - (data.settings.log_keep_months - 1)
    oldest_key = f"{oldest // 12:04d}-{oldest % 12 + 1:02d}"
    for guest_id in list(data.months):
        kept = {
            month: total for month, total in data.months[guest_id].items() if month >= oldest_key
        }
        if kept:
            data.months[guest_id] = kept
        else:
            del data.months[guest_id]


def forget_log(data: AccessData, guest_id: str) -> None:
    """Delete the visit log of a guest."""
    data.visits = [visit for visit in data.visits if visit.guest_id != guest_id]
    data.months.pop(guest_id, None)


def month_minutes(data: AccessData, guest_id: str, now: datetime) -> int:
    """The minutes of the guest's finished visits in the current month."""
    return data.months.get(guest_id, {}).get(month_key(now), MonthTotal()).minutes


def _arrive(data: AccessData, guest: Guest, presence: Presence, now: datetime) -> Raised:
    if presence.arrived is not None:
        # A visit whose grace time ran out unnoticed ends where the guest left
        _finish(data, guest, presence, presence.away_since or now)
    presence.counting = True
    presence.arrived = now
    presence.visit_ends = None if guest.visit is None else now + guest.visit
    return Raised(guest.id, EVENT_ARRIVED, {"visit_ends": iso_seconds(presence.visit_ends)})


def _leave(guest: Guest, presence: Presence, at: datetime) -> Raised:
    """The guest no longer counts; the visit is kept for a return within the grace time."""
    presence.counting = False
    presence.resume_until = None
    presence.restarted = None
    presence.away_since = at
    return Raised(guest.id, EVENT_LEFT)


def _check_counting(guest: Guest, presence: Presence, now: datetime) -> list[Raised]:
    """A guest who counts keeps counting until leaving; raise expiries once."""
    raised = []
    if presence.visit_ends is not None and now >= presence.visit_ends and not presence.time_up:
        presence.time_up = True
        raised.append(
            Raised(guest.id, EVENT_TIME_UP, {"visit_ends": iso_seconds(presence.visit_ends)})
        )
    valid = guest.approval.valid(now)
    if not valid and not presence.approval_expired:
        presence.approval_expired = True
        raised.append(Raised(guest.id, EVENT_APPROVAL_EXPIRED, guest.approval.as_dict()))
    elif valid:
        # The time window opened again: the next close is a new expiry
        presence.approval_expired = False
    return raised


def _evaluate_guest(data: AccessData, guest: Guest, home: bool, now: datetime) -> list[Raised]:
    presence = data.presence_of(guest.id)
    locked = guest.approval.kind is ApprovalKind.OFF
    if presence.counting:
        if locked:
            # Locked by an administrator: no longer counts, wherever the guest is
            _finish(data, guest, presence, now)
            presence.away_since = None
            return []
        if not home:
            return [_leave(guest, presence, now)]
        return _check_counting(guest, presence, now)
    if locked and (presence.resume_until is not None or presence.away_since is not None):
        # Locked while away or waiting to resume: the visit is over, the rooms lock
        left = presence.away_since
        if left is None and presence.resume_until is not None:
            left = _restarted(data, presence)
        _finish(data, guest, presence, left or now)
        presence.away_since = None
    resuming = presence.resume_until is not None and now < presence.resume_until
    if home and resuming:
        # Back after a restart: the visit goes on, its end stays
        presence.counting = True
        presence.resume_until = None
        presence.restarted = None
        return _check_counting(guest, presence, now)
    in_grace = (
        presence.away_since is not None
        and now < presence.away_since + guest.grace
        and presence.arrived is not None
    )
    if home and guest.approval.valid(now):
        if in_grace:
            # Back within the grace time: the same visit goes on, its end stays
            presence.counting = True
            presence.away_since = None
            return _check_counting(guest, presence, now)
        arrived = _arrive(data, guest, presence, now)
        presence.away_since = None
        return [arrived, *_check_counting(guest, presence, now)]
    raised = []
    if presence.resume_until is not None and not resuming:
        # Not back after a restart: the guest left in the meantime, at the
        # latest when Home Assistant started; the grace time counts from there
        raised.append(_leave(guest, presence, _restarted(data, presence)))
    if presence.away_since is not None and now >= presence.away_since + guest.grace:
        # Away longer than the grace time: the visit is over, it ended on leaving
        _finish(data, guest, presence, presence.away_since)
        presence.away_since = None
        if guest.approval.kind is ApprovalKind.ONCE:
            # One visit, and it is over
            data.guests[guest.id] = replace(guest, approval=Approval())
            raised.append(
                Raised(
                    guest.id,
                    EVENT_APPROVAL_CHANGED,
                    {**Approval().as_dict(), "reason": "visit_over", "by": None},
                )
            )
    return raised


def counting_guests(data: AccessData) -> list[Guest]:
    """The guests who count right now."""
    return [guest for guest in data.guests.values() if data.presence_of(guest.id).counting]


def home_since(data: AccessData) -> datetime | None:
    """The earliest arrival of the guests who count; a visit continued within the grace time keeps it."""
    arrivals = [
        arrived
        for guest in counting_guests(data)
        if (arrived := data.presence_of(guest.id).arrived) is not None
    ]
    return min(arrivals, default=None)


def free_rooms(data: AccessData) -> frozenset[str]:
    """The lockable rooms the guests who count may enter together.

    Guests waiting to resume after a restart keep their rooms, so their own
    rooms do not turn into locked ones while their trackers come back.
    """
    configured = frozenset(room.area_id for room in data.settings.rooms)
    free: set[str] = set()
    for guest in data.guests.values():
        presence = data.presence_of(guest.id)
        resuming = presence.resume_until is not None and guest.approval.kind is not ApprovalKind.OFF
        if not (presence.counting or resuming):
            continue
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
    prune_log(data, now)
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
        if presence.away_since is not None:
            candidates.append(presence.away_since + guest.grace)
    return min((moment for moment in candidates if moment > now), default=None)


def guest_status(guest: Guest, presence: Presence, home: bool, now: datetime) -> GuestStatus:
    """One state per guest that a dashboard shows as it is."""
    if presence.counting:
        if presence.approval_expired:
            return GuestStatus.APPROVAL_EXPIRED
        if presence.time_up:
            return GuestStatus.TIME_UP
        return GuestStatus.COUNTING
    if presence.resume_until is not None:
        return GuestStatus.RESUMING
    if home:
        return GuestStatus.NOT_APPROVED
    if presence.away_since is None and not guest.approval.active(now):
        # Away within the grace time still counts as an approved guest away
        return GuestStatus.INACTIVE
    return GuestStatus.AWAY
