"""Guests, approvals, rooms and the runtime state: plain data, stored as JSON."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
from typing import Any

from homeassistant.util import dt as dt_util

from .const import DEFAULT_GRACE_MINUTES, DEFAULT_VISIT_MINUTES, MAX_GRACE_MINUTES, VISIT_CHOICES


class ApprovalKind(StrEnum):
    """How a guest is approved."""

    OFF = "off"
    # One visit, ending at the latest at `until`
    ONCE = "once"
    # Any number of visits until `until`
    UNTIL = "until"
    # Any number of visits, no end
    PERMANENT = "permanent"


@dataclass(frozen=True, slots=True)
class Window:
    """Weekdays (0 is Monday) and a local time range; an end before the start runs past midnight."""

    weekdays: frozenset[int]
    start: time
    end: time

    def __post_init__(self) -> None:
        """Reject an empty or impossible window."""
        if not self.weekdays or not self.weekdays <= set(range(7)):
            raise ValueError("a time window needs weekdays between 0 and 6")
        if self.start == self.end:
            raise ValueError("a time window needs a start different from its end")

    def contains(self, moment: datetime) -> bool:
        """Whether the window applies at that moment, in local time."""
        local = dt_util.as_local(moment)
        now = local.time().replace(tzinfo=None)
        day = local.weekday()
        if self.start < self.end:
            return day in self.weekdays and self.start <= now < self.end
        # Past midnight: the evening of a listed day and the morning after it
        return (day in self.weekdays and now >= self.start) or (
            (day - 1) % 7 in self.weekdays and now < self.end
        )

    def next_change(self, moment: datetime) -> datetime:
        """The next start or end of the range after that moment, on any day."""
        local = dt_util.as_local(moment)
        # Compared in UTC: in the hour repeated when clocks go back, wall times
        # of one time zone would compare wrong; both passes of it are candidates
        candidates = (
            datetime.combine(
                local.date() + timedelta(days=offset), clock.replace(fold=fold), local.tzinfo
            ).astimezone(UTC)
            for offset in range(3)
            for clock in (self.start, self.end)
            for fold in (0, 1)
        )
        return min(candidate for candidate in candidates if candidate > moment)

    def as_dict(self) -> dict[str, Any]:
        """The window as JSON."""
        return {
            "weekdays": sorted(self.weekdays),
            "start": self.start.strftime("%H:%M"),
            "end": self.end.strftime("%H:%M"),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Window:
        """A window from JSON."""
        return cls(
            frozenset(int(day) for day in data["weekdays"]),
            time.fromisoformat(data["start"]),
            time.fromisoformat(data["end"]),
        )


@dataclass(frozen=True, slots=True)
class Approval:
    """Whether and when a guest counts; with time windows, only within one of them."""

    kind: ApprovalKind = ApprovalKind.OFF
    until: datetime | None = None
    windows: tuple[Window, ...] = ()

    def __post_init__(self) -> None:
        """Reject combinations the kinds do not allow."""
        if self.kind in (ApprovalKind.ONCE, ApprovalKind.UNTIL) and self.until is None:
            raise ValueError(f"an approval {self.kind} needs an end")
        if self.kind in (ApprovalKind.OFF, ApprovalKind.PERMANENT) and self.until is not None:
            raise ValueError(f"an approval {self.kind} has no end")
        if self.kind in (ApprovalKind.OFF, ApprovalKind.ONCE) and self.windows:
            raise ValueError(f"an approval {self.kind} has no time window")
        if self.until is not None and self.until.tzinfo is None:
            raise ValueError("the end of an approval needs a time zone")

    def valid(self, moment: datetime) -> bool:
        """Whether the approval lets the guest count at that moment."""
        if self.kind is ApprovalKind.OFF:
            return False
        if self.until is not None and moment >= self.until:
            return False
        return not self.windows or any(window.contains(moment) for window in self.windows)

    def next_change(self, moment: datetime) -> datetime | None:
        """The next moment the approval may turn valid or invalid, or None."""
        if self.kind is ApprovalKind.OFF:
            return None
        candidates = []
        if self.until is not None and self.until > moment:
            candidates.append(self.until)
        candidates.extend(window.next_change(moment) for window in self.windows)
        return min(candidates, default=None)

    def as_dict(self) -> dict[str, Any]:
        """The approval as JSON."""
        return {
            "kind": self.kind.value,
            "until": None if self.until is None else self.until.isoformat(),
            "windows": [window.as_dict() for window in self.windows],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Approval:
        """An approval from JSON."""
        until = data.get("until")
        return cls(
            ApprovalKind(data["kind"]),
            None if until is None else datetime.fromisoformat(until),
            tuple(Window.from_dict(window) for window in data.get("windows", ())),
        )


@dataclass(frozen=True, slots=True)
class Guest:
    """A guest: trackers, approval, rooms and time per visit."""

    id: str
    name: str
    trackers: tuple[str, ...]
    approval: Approval = Approval()
    # Lockable rooms (area ids) the guest may enter; all_rooms lets the guest everywhere
    rooms: tuple[str, ...] = ()
    all_rooms: bool = False
    # None is unlimited
    visit_minutes: int | None = DEFAULT_VISIT_MINUTES
    grace_minutes: int = DEFAULT_GRACE_MINUTES

    def __post_init__(self) -> None:
        """Reject a guest the rules do not allow."""
        if not self.name.strip():
            raise ValueError("a guest needs a name")
        if not self.trackers:
            raise ValueError("a guest needs at least one tracker")
        if self.visit_minutes not in VISIT_CHOICES:
            raise ValueError(f"the time per visit is one of {VISIT_CHOICES}")
        if not 1 <= self.grace_minutes <= MAX_GRACE_MINUTES:
            raise ValueError(f"the grace time is between 1 and {MAX_GRACE_MINUTES} minutes")

    @property
    def visit(self) -> timedelta | None:
        """The time per visit, or None when unlimited."""
        return None if self.visit_minutes is None else timedelta(minutes=self.visit_minutes)

    @property
    def grace(self) -> timedelta:
        """How long all trackers of a once guest may be away."""
        return timedelta(minutes=self.grace_minutes)

    def as_dict(self) -> dict[str, Any]:
        """The guest as JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "trackers": list(self.trackers),
            "approval": self.approval.as_dict(),
            "rooms": list(self.rooms),
            "all_rooms": self.all_rooms,
            "visit_minutes": self.visit_minutes,
            "grace_minutes": self.grace_minutes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Guest:
        """A guest from JSON."""
        return cls(
            id=data["id"],
            name=data["name"],
            trackers=tuple(data["trackers"]),
            approval=Approval.from_dict(data["approval"]),
            rooms=tuple(data.get("rooms", ())),
            all_rooms=bool(data.get("all_rooms", False)),
            visit_minutes=data.get("visit_minutes", DEFAULT_VISIT_MINUTES),
            grace_minutes=data.get("grace_minutes", DEFAULT_GRACE_MINUTES),
        )


@dataclass(frozen=True, slots=True)
class Room:
    """A lockable room: a Home Assistant area and the contact of its door."""

    area_id: str
    door: str

    def as_dict(self) -> dict[str, Any]:
        """The room as JSON."""
        return {"area_id": self.area_id, "door": self.door}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Room:
        """A room from JSON."""
        return cls(data["area_id"], data["door"])


@dataclass(frozen=True, slots=True)
class Settings:
    """What is set once: the residents and the lockable rooms."""

    residents: tuple[str, ...] = ()
    rooms: tuple[Room, ...] = ()

    def __post_init__(self) -> None:
        """Reject a room twice or a door for two rooms."""
        areas = [room.area_id for room in self.rooms]
        doors = [room.door for room in self.rooms]
        if len(set(areas)) != len(areas):
            raise ValueError("an area is a lockable room only once")
        if len(set(doors)) != len(doors):
            raise ValueError("a door contact belongs to one room only")

    def room(self, area_id: str) -> Room | None:
        """The room of that area, or None."""
        return next((room for room in self.rooms if room.area_id == area_id), None)

    def as_dict(self) -> dict[str, Any]:
        """The settings as JSON."""
        return {
            "residents": list(self.residents),
            "rooms": [room.as_dict() for room in self.rooms],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        """Settings from JSON."""
        return cls(
            tuple(data.get("residents", ())),
            tuple(Room.from_dict(room) for room in data.get("rooms", ())),
        )


def _time_or_none(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _iso_or_none(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


@dataclass(slots=True)
class Presence:
    """The runtime state of a guest."""

    counting: bool = False
    arrived: datetime | None = None
    visit_ends: datetime | None = None
    # When the last tracker of a once guest went away
    away_since: datetime | None = None
    # After a restart: until when a return continues the visit
    resume_until: datetime | None = None
    # Raised already for this visit
    time_up: bool = False
    approval_expired: bool = False

    def end_visit(self) -> None:
        """Forget the visit."""
        self.counting = False
        self.arrived = None
        self.visit_ends = None
        self.resume_until = None
        self.time_up = False
        self.approval_expired = False

    def as_dict(self) -> dict[str, Any]:
        """The state as JSON."""
        return {
            "counting": self.counting,
            "arrived": _iso_or_none(self.arrived),
            "visit_ends": _iso_or_none(self.visit_ends),
            "away_since": _iso_or_none(self.away_since),
            "resume_until": _iso_or_none(self.resume_until),
            "time_up": self.time_up,
            "approval_expired": self.approval_expired,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Presence:
        """The state from JSON."""
        return cls(
            counting=bool(data.get("counting", False)),
            arrived=_time_or_none(data.get("arrived")),
            visit_ends=_time_or_none(data.get("visit_ends")),
            away_since=_time_or_none(data.get("away_since")),
            resume_until=_time_or_none(data.get("resume_until")),
            time_up=bool(data.get("time_up", False)),
            approval_expired=bool(data.get("approval_expired", False)),
        )


@dataclass(slots=True)
class Lock:
    """The room lock: active while only guests are home."""

    active: bool = False
    # Rooms whose door was open when the lock started: free for this lock
    exempt: frozenset[str] = frozenset()

    def as_dict(self) -> dict[str, Any]:
        """The lock as JSON."""
        return {"active": self.active, "exempt": sorted(self.exempt)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lock:
        """The lock from JSON."""
        return cls(bool(data.get("active", False)), frozenset(data.get("exempt", ())))


@dataclass(slots=True)
class AccessData:
    """Everything that is stored."""

    settings: Settings = Settings()
    guests: dict[str, Guest] = field(default_factory=dict)
    presence: dict[str, Presence] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)

    def presence_of(self, guest_id: str) -> Presence:
        """The runtime state of a guest, created when missing."""
        return self.presence.setdefault(guest_id, Presence())

    def as_dict(self) -> dict[str, Any]:
        """Everything as JSON."""
        return {
            "settings": self.settings.as_dict(),
            "guests": [guest.as_dict() for guest in self.guests.values()],
            "presence": {
                guest_id: presence.as_dict()
                for guest_id, presence in self.presence.items()
                if guest_id in self.guests
            },
            "lock": self.lock.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AccessData:
        """Everything from JSON."""
        guests = [Guest.from_dict(guest) for guest in data.get("guests", ())]
        return cls(
            settings=Settings.from_dict(data.get("settings", {})),
            guests={guest.id: guest for guest in guests},
            presence={
                guest_id: Presence.from_dict(presence)
                for guest_id, presence in data.get("presence", {}).items()
            },
            lock=Lock.from_dict(data.get("lock", {})),
        )
