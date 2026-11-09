"""Guests, approvals, rooms and the runtime state: plain data, stored as JSON."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from enum import StrEnum
import re
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_GRACE_MINUTES,
    DEFAULT_LOG_GRID_MINUTES,
    DEFAULT_LOG_KEEP_DAYS,
    DEFAULT_LOG_KEEP_MONTHS,
    DEFAULT_RESUME_MINUTES,
    DEFAULT_VISIT_MINUTES,
    MAX_GRACE_MINUTES,
    MAX_LOG_GRID_MINUTES,
    MAX_LOG_KEEP_DAYS,
    MAX_LOG_KEEP_MONTHS,
    MAX_NAME_LENGTH,
    MAX_NOTE_LENGTH,
    MAX_RESUME_MINUTES,
    MAX_VISIT_MINUTES,
    PICTURE_SIZE,
)

# The ID Home Assistant gives an uploaded image
_IMAGE_ID = re.compile(r"[0-9a-f]{32}")


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

    def active(self, moment: datetime) -> bool:
        """Whether there is an approval at all: not locked and not past its end.

        Time windows do not matter here: outside them the guest is still approved.
        """
        if self.kind is ApprovalKind.OFF:
            return False
        return self.until is None or moment < self.until

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
        if self.until is not None and moment >= self.until:
            # Past its end the approval stays invalid, whatever its windows say
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
    # Keep a visit log: date, start and length of each visit on a grid; off by default
    log_visits: bool = False
    # A photo: the ID of an image uploaded to Home Assistant, or None
    picture: str | None = None
    # A note for administrators; shown on the page only
    note: str = ""

    def __post_init__(self) -> None:
        """Reject a guest the rules do not allow."""
        if not self.name.strip():
            raise ValueError("a guest needs a name")
        if len(self.name) > MAX_NAME_LENGTH:
            raise ValueError(f"a name has at most {MAX_NAME_LENGTH} characters")
        if not self.trackers:
            raise ValueError("a guest needs at least one tracker")
        if self.visit_minutes is not None and not 1 <= self.visit_minutes <= MAX_VISIT_MINUTES:
            raise ValueError(f"the time per visit is between 1 and {MAX_VISIT_MINUTES} minutes")
        if not 1 <= self.grace_minutes <= MAX_GRACE_MINUTES:
            raise ValueError(f"the grace time is between 1 and {MAX_GRACE_MINUTES} minutes")
        if self.picture is not None and not _IMAGE_ID.fullmatch(self.picture):
            raise ValueError("a photo is the ID of an uploaded image")
        if len(self.note) > MAX_NOTE_LENGTH:
            raise ValueError(f"a note has at most {MAX_NOTE_LENGTH} characters")

    @property
    def picture_url(self) -> str | None:
        """Where Home Assistant serves the photo, or None without one."""
        return None if self.picture is None else f"/api/image/serve/{self.picture}/{PICTURE_SIZE}"

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
            "log_visits": self.log_visits,
            "picture": self.picture,
            "note": self.note,
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
            log_visits=bool(data.get("log_visits", False)),
            picture=data.get("picture"),
            note=str(data.get("note", "")),
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


def _check_range(name: str, value: int, maximum: int) -> None:
    if not 1 <= value <= maximum:
        raise ValueError(f"{name} is between 1 and {maximum}")


@dataclass(frozen=True, slots=True)
class Settings:
    """What is set once: the residents, the lockable rooms and the timings."""

    residents: tuple[str, ...] = ()
    rooms: tuple[Room, ...] = ()
    # After a restart: how long a guest who counted may take to be seen again
    resume_minutes: int = DEFAULT_RESUME_MINUTES
    # Visit log: grid in minutes, days single visits are kept, months totals are kept
    log_grid_minutes: int = DEFAULT_LOG_GRID_MINUTES
    log_keep_days: int = DEFAULT_LOG_KEEP_DAYS
    log_keep_months: int = DEFAULT_LOG_KEEP_MONTHS

    @property
    def resume_window(self) -> timedelta:
        """How long a guest who counted may take to be seen again after a restart."""
        return timedelta(minutes=self.resume_minutes)

    @property
    def log_grid(self) -> timedelta:
        """The grid of the visit log."""
        return timedelta(minutes=self.log_grid_minutes)

    def __post_init__(self) -> None:
        """Reject a room twice, a door for two rooms or a timing out of range."""
        _check_range("the resume time", self.resume_minutes, MAX_RESUME_MINUTES)
        _check_range("the grid of the visit log", self.log_grid_minutes, MAX_LOG_GRID_MINUTES)
        _check_range("the days single visits are kept", self.log_keep_days, MAX_LOG_KEEP_DAYS)
        _check_range("the months totals are kept", self.log_keep_months, MAX_LOG_KEEP_MONTHS)
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
            "resume_minutes": self.resume_minutes,
            "log_grid_minutes": self.log_grid_minutes,
            "log_keep_days": self.log_keep_days,
            "log_keep_months": self.log_keep_months,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Settings:
        """Settings from JSON."""
        return cls(
            tuple(data.get("residents", ())),
            tuple(Room.from_dict(room) for room in data.get("rooms", ())),
            int(data.get("resume_minutes", DEFAULT_RESUME_MINUTES)),
            int(data.get("log_grid_minutes", DEFAULT_LOG_GRID_MINUTES)),
            int(data.get("log_keep_days", DEFAULT_LOG_KEEP_DAYS)),
            int(data.get("log_keep_months", DEFAULT_LOG_KEEP_MONTHS)),
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


@dataclass(frozen=True, slots=True)
class Visit:
    """One logged visit: when it began and how long it took, both on a quarter-hour grid."""

    guest_id: str
    start: datetime
    minutes: int

    def as_dict(self) -> dict[str, Any]:
        """The visit as JSON."""
        return {"guest_id": self.guest_id, "start": self.start.isoformat(), "minutes": self.minutes}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Visit:
        """A visit from JSON."""
        return cls(data["guest_id"], datetime.fromisoformat(data["start"]), int(data["minutes"]))


@dataclass(frozen=True, slots=True)
class MonthTotal:
    """The visits of a guest in one month."""

    visits: int = 0
    minutes: int = 0

    def as_dict(self) -> dict[str, Any]:
        """The total as JSON."""
        return {"visits": self.visits, "minutes": self.minutes}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MonthTotal:
        """A total from JSON."""
        return cls(int(data.get("visits", 0)), int(data.get("minutes", 0)))


@dataclass(slots=True)
class AccessData:
    """Everything that is stored."""

    settings: Settings = Settings()
    guests: dict[str, Guest] = field(default_factory=dict)
    presence: dict[str, Presence] = field(default_factory=dict)
    lock: Lock = field(default_factory=Lock)
    # The visit log: single visits, and per guest the totals per month ("2026-11")
    visits: list[Visit] = field(default_factory=list)
    months: dict[str, dict[str, MonthTotal]] = field(default_factory=dict)
    # The photos this integration uploaded, by image ID, with the time of the upload;
    # only these are guests' photos, and only these are ever deleted
    pictures: dict[str, datetime] = field(default_factory=dict)

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
            "visits": [visit.as_dict() for visit in self.visits if visit.guest_id in self.guests],
            "months": {
                guest_id: {month: total.as_dict() for month, total in totals.items()}
                for guest_id, totals in self.months.items()
                if guest_id in self.guests
            },
            "pictures": {
                image_id: uploaded.isoformat() for image_id, uploaded in self.pictures.items()
            },
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
            visits=[Visit.from_dict(visit) for visit in data.get("visits", ())],
            months={
                guest_id: {month: MonthTotal.from_dict(total) for month, total in totals.items()}
                for guest_id, totals in data.get("months", {}).items()
            },
            pictures={
                image_id: datetime.fromisoformat(uploaded)
                for image_id, uploaded in data.get("pictures", {}).items()
            },
        )
