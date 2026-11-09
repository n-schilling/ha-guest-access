"""The rules, without Home Assistant: counting, expiry, once approvals, restart, room lock."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, time, timedelta

from homeassistant.util import dt as dt_util

from custom_components.guest_access.logic import (
    GuestStatus,
    Observed,
    evaluate,
    forget_log,
    free_rooms,
    guest_status,
    home_since,
    locked_rooms,
    month_key,
    month_minutes,
    next_wake,
    only_guests_home,
    prepare_restart,
    prune_log,
)
from custom_components.guest_access.model import (
    AccessData,
    Approval,
    ApprovalKind,
    Guest,
    MonthTotal,
    Presence,
    Room,
    Settings,
    Window,
)

T0 = datetime(2026, 11, 9, 12, tzinfo=UTC)
ROOMS = (Room("bedroom", "binary_sensor.bedroom"), Room("kids", "binary_sensor.kids"))
PERMANENT = Approval(ApprovalKind.PERMANENT)


def make(*guests: Guest) -> AccessData:
    """Data with the rooms and these guests."""
    return AccessData(Settings(("person.sam",), ROOMS), {guest.id: guest for guest in guests})


def guest(guest_id: str = "a", **kwargs: object) -> Guest:
    """A guest with a permanent approval unless given otherwise."""
    fields: dict[str, object] = {"approval": PERMANENT, **kwargs}
    return Guest(guest_id, guest_id.upper(), (f"device_tracker.{guest_id}",), **fields)  # type: ignore[arg-type]


def seen(*home: str, residents: bool = False, doors: frozenset[str] = frozenset()) -> Observed:
    """These guests are home."""
    return Observed({guest_id: True for guest_id in home}, residents, doors)


def types(raised: list[object]) -> list[str]:
    """The event types raised."""
    return [item.event_type for item in raised]  # type: ignore[attr-defined]


def test_arrive_time_up_leave() -> None:
    """A guest arrives, the time runs out once, the guest leaves."""
    data = make(guest())
    assert types(evaluate(data, seen("a"), T0)) == ["arrived"]
    presence = data.presence["a"]
    assert presence.counting
    assert presence.visit_ends == T0 + timedelta(minutes=60)
    assert next_wake(data, T0) == presence.visit_ends
    assert evaluate(data, seen("a"), T0 + timedelta(minutes=30)) == []
    assert types(evaluate(data, seen("a"), T0 + timedelta(minutes=60))) == ["time_up"]
    assert evaluate(data, seen("a"), T0 + timedelta(minutes=61)) == []
    assert presence.counting
    assert types(evaluate(data, seen(), T0 + timedelta(minutes=70))) == ["left"]
    assert not presence.counting
    assert presence.away_since == T0 + timedelta(minutes=70)
    # Away longer than the grace time: the visit is forgotten
    assert evaluate(data, seen(), T0 + timedelta(minutes=85)) == []
    assert presence.away_since is None
    assert presence.arrived is None


def test_no_approval_no_count() -> None:
    """Without a valid approval a guest at home does not count."""
    data = make(guest(approval=Approval()))
    assert evaluate(data, seen("a"), T0) == []
    assert not data.presence["a"].counting


def test_approval_expires_while_home() -> None:
    """The end of an approval keeps the guest counting, raised once."""
    until = T0 + timedelta(minutes=10)
    data = make(guest(approval=Approval(ApprovalKind.UNTIL, until), visit_minutes=None))
    evaluate(data, seen("a"), T0)
    assert next_wake(data, T0) == until
    assert types(evaluate(data, seen("a"), until)) == ["approval_expired"]
    assert evaluate(data, seen("a"), until + timedelta(minutes=1)) == []
    assert data.presence["a"].counting
    evaluate(data, seen(), until + timedelta(minutes=2))
    assert evaluate(data, seen("a"), until + timedelta(minutes=3)) == []
    assert not data.presence["a"].counting


def test_window_closes_while_home() -> None:
    """A window that closes counts as an expiry; arriving outside it does not count."""
    today = dt_util.as_local(T0)
    window = Window(frozenset({today.weekday()}), time(0), time(23, 59))
    data = make(guest(approval=Approval(ApprovalKind.PERMANENT, None, (window,))))
    late = datetime.combine(today.date(), time(23, 59, 30), tzinfo=today.tzinfo)
    assert types(evaluate(data, seen("a"), T0)) == ["arrived"]
    assert "approval_expired" in types(evaluate(data, seen("a"), late))
    data = make(guest(approval=Approval(ApprovalKind.PERMANENT, None, (window,))))
    assert evaluate(data, seen("a"), late) == []


def test_locked_guest_stops_counting() -> None:
    """An administrator's lock ends the count at once, without an event."""
    data = make(guest())
    evaluate(data, seen("a"), T0)
    data.guests["a"] = guest(approval=Approval())
    assert evaluate(data, seen("a"), T0) == []
    assert not data.presence["a"].counting


def test_once_grace() -> None:
    """A once guest may return within the grace time; after it the approval is off."""
    once = Approval(ApprovalKind.ONCE, T0 + timedelta(days=1))
    data = make(guest(approval=once, grace_minutes=15))
    evaluate(data, seen("a"), T0)
    evaluate(data, seen(), T0 + timedelta(minutes=5))
    assert data.presence["a"].away_since == T0 + timedelta(minutes=5)
    assert next_wake(data, T0 + timedelta(minutes=5)) == T0 + timedelta(minutes=20)
    # Back within the grace time: the same visit goes on, no new arrival
    assert evaluate(data, seen("a"), T0 + timedelta(minutes=10)) == []
    assert data.presence["a"].counting
    assert data.presence["a"].visit_ends == T0 + timedelta(minutes=60)
    assert data.presence["a"].away_since is None
    evaluate(data, seen(), T0 + timedelta(minutes=12))
    assert evaluate(data, seen(), T0 + timedelta(minutes=20)) == []
    raised = evaluate(data, seen(), T0 + timedelta(minutes=27))
    assert types(raised) == ["approval_changed"]
    assert raised[0].data == {
        "kind": "off",
        "until": None,
        "windows": [],
        "reason": "visit_over",
        "by": None,
    }
    assert data.guests["a"].approval == Approval()
    assert evaluate(data, seen("a"), T0 + timedelta(minutes=30)) == []


def test_restart_resume() -> None:
    """After a restart a guest who counted keeps the visit when a tracker returns soon."""
    data = make(guest())
    evaluate(data, seen("a"), T0)
    ends = data.presence["a"].visit_ends
    start = T0 + timedelta(minutes=20)
    prepare_restart(data, start)
    presence = data.presence["a"]
    assert not presence.counting
    assert presence.resume_until == start + Settings().resume_window
    assert next_wake(data, start) == presence.resume_until
    assert evaluate(data, seen(), start) == []
    assert evaluate(data, seen("a"), start + timedelta(minutes=2)) == []
    assert presence.counting
    assert presence.visit_ends == ends
    assert presence.resume_until is None


def test_restart_resume_with_time_up() -> None:
    """A visit whose time ran out during the restart raises it on return."""
    data = make(guest())
    evaluate(data, seen("a"), T0)
    start = T0 + timedelta(minutes=59)
    prepare_restart(data, start)
    assert types(evaluate(data, seen("a"), T0 + timedelta(minutes=61))) == ["time_up"]


def test_restart_not_back() -> None:
    """Not back within the resume window: the guest left; a once guest's grace starts."""
    once = Approval(ApprovalKind.ONCE, T0 + timedelta(days=1))
    data = make(guest(approval=once))
    evaluate(data, seen("a"), T0)
    prepare_restart(data, T0)
    end = T0 + Settings().resume_window
    assert types(evaluate(data, seen(), end)) == ["left"]
    presence = data.presence["a"]
    assert presence.resume_until is None
    # The grace time counts from the restart, not from the end of the resume window
    assert presence.away_since == T0


def test_room_lock() -> None:
    """Only guests home: rooms of all counting guests are free, open doors are exempt."""
    data = make(guest("a", rooms=("bedroom",)), guest("b"))
    evaluate(data, seen("a", "b", doors=frozenset({"kids"})), T0)
    assert data.lock.active
    assert data.lock.exempt == frozenset({"kids"})
    assert free_rooms(data) == frozenset({"bedroom"})
    assert locked_rooms(data) == frozenset()
    assert only_guests_home(data, seen("a", "b"))
    # Guest a leaves: the bedroom is locked now, kids stays exempt for this lock
    evaluate(data, seen("b"), T0 + timedelta(minutes=1))
    assert locked_rooms(data) == frozenset({"bedroom"})
    # A resident comes home: no lock
    evaluate(data, seen("b", residents=True), T0 + timedelta(minutes=2))
    assert not data.lock.active
    assert locked_rooms(data) == frozenset()
    assert not only_guests_home(data, seen("b", residents=True))


def test_all_rooms_and_unknown_rooms() -> None:
    """A guest with all rooms frees every lockable room; rooms no longer lockable are ignored."""
    data = make(guest("a", all_rooms=True), guest("b", rooms=("office",)))
    evaluate(data, seen("a", "b"), T0)
    assert free_rooms(data) == frozenset({"bedroom", "kids"})
    data = make(guest("b", rooms=("office",)))
    evaluate(data, seen("b"), T0)
    assert free_rooms(data) == frozenset()
    assert locked_rooms(data) == frozenset({"bedroom", "kids"})


def test_lock_held_while_resuming() -> None:
    """During the resume window the lock and its exempt rooms stay."""
    data = make(guest())
    evaluate(data, seen("a", doors=frozenset({"kids"})), T0)
    prepare_restart(data, T0)
    evaluate(data, seen(), T0 + timedelta(minutes=1))
    assert data.lock.active
    assert data.lock.exempt == frozenset({"kids"})
    evaluate(data, seen(), T0 + Settings().resume_window)
    assert not data.lock.active


def test_next_wake_none() -> None:
    """Nothing pending, nothing to wake for."""
    data = make(guest(visit_minutes=None))
    evaluate(data, seen("a"), T0)
    assert next_wake(data, T0) is None


def test_guest_status() -> None:
    """Expired approval before time up before counting; then resuming, home, away."""
    presence = Presence(counting=True)
    approved, locked = guest(), guest(approval=Approval())
    ended = guest(approval=Approval(ApprovalKind.UNTIL, T0))
    assert guest_status(approved, presence, True, T0) is GuestStatus.COUNTING
    presence.time_up = True
    assert guest_status(approved, presence, True, T0) is GuestStatus.TIME_UP
    presence.approval_expired = True
    assert guest_status(approved, presence, True, T0) is GuestStatus.APPROVAL_EXPIRED
    assert guest_status(approved, Presence(resume_until=T0), True, T0) is GuestStatus.RESUMING
    assert guest_status(locked, Presence(), True, T0) is GuestStatus.NOT_APPROVED
    assert guest_status(approved, Presence(), False, T0) is GuestStatus.AWAY
    # Without an approval and not home: inactive; within the grace time still away
    assert guest_status(locked, Presence(), False, T0) is GuestStatus.INACTIVE
    assert guest_status(ended, Presence(), False, T0) is GuestStatus.INACTIVE
    assert guest_status(ended, Presence(), False, T0 - timedelta(minutes=1)) is GuestStatus.AWAY
    assert guest_status(locked, Presence(away_since=T0), False, T0) is GuestStatus.AWAY


def test_resuming_guest_keeps_rooms() -> None:
    """During the resume window a guest's own rooms stay free."""
    data = make(guest("a", rooms=("bedroom",)))
    evaluate(data, seen("a"), T0)
    prepare_restart(data, T0)
    evaluate(data, seen(), T0 + timedelta(minutes=1))
    assert data.lock.active
    assert free_rooms(data) == frozenset({"bedroom"})
    assert locked_rooms(data) == frozenset({"kids"})


def test_window_reopens_clears_expiry() -> None:
    """A guest home overnight counts again normally when the window opens."""
    today = dt_util.as_local(T0)
    window = Window(frozenset(range(7)), time(8), time(20))
    data = make(
        guest(approval=Approval(ApprovalKind.PERMANENT, None, (window,)), visit_minutes=None)
    )
    morning = datetime.combine(today.date(), time(9), tzinfo=today.tzinfo)
    evaluate(data, seen("a"), morning)
    assert types(evaluate(data, seen("a"), morning + timedelta(hours=12))) == ["approval_expired"]
    assert (
        guest_status(data.guests["a"], data.presence["a"], True, T0) is GuestStatus.APPROVAL_EXPIRED
    )
    evaluate(data, seen("a"), morning + timedelta(days=1))
    assert guest_status(data.guests["a"], data.presence["a"], True, T0) is GuestStatus.COUNTING
    assert types(evaluate(data, seen("a"), morning + timedelta(days=1, hours=12))) == [
        "approval_expired"
    ]


def test_resuming_guest_locked() -> None:
    """A guest locked while waiting to resume keeps no rooms and does not resume."""
    data = make(guest("a", rooms=("bedroom",)))
    evaluate(data, seen("a"), T0)
    prepare_restart(data, T0)
    data.guests["a"] = guest("a", rooms=("bedroom",), approval=Approval())
    assert free_rooms(data) == frozenset()
    assert evaluate(data, seen("a"), T0 + timedelta(minutes=1)) == []
    assert data.presence["a"].resume_until is None
    assert not data.presence["a"].counting


def test_return_within_grace_keeps_visit() -> None:
    """A flapping tracker neither restarts the time nor hides its end."""
    data = make(guest())
    evaluate(data, seen("a"), T0)
    for minute in range(10, 70, 10):
        assert types(evaluate(data, seen(), T0 + timedelta(minutes=minute))) == ["left"]
        raised = types(evaluate(data, seen("a"), T0 + timedelta(minutes=minute + 1)))
        assert "arrived" not in raised
    presence = data.presence["a"]
    assert presence.visit_ends == T0 + timedelta(minutes=60)
    assert presence.time_up


def test_return_after_grace_is_new_visit() -> None:
    """Back after the grace time: a new arrival with a new end."""
    data = make(guest(grace_minutes=15))
    evaluate(data, seen("a"), T0)
    evaluate(data, seen(), T0 + timedelta(minutes=5))
    later = T0 + timedelta(minutes=30)
    assert types(evaluate(data, seen("a"), later)) == ["arrived"]
    assert data.presence["a"].visit_ends == later + timedelta(minutes=60)


def test_no_return_when_locked_or_invalid() -> None:
    """Locked while away, or the approval no longer valid: no continuation."""
    data = make(guest())
    evaluate(data, seen("a"), T0)
    evaluate(data, seen(), T0 + timedelta(minutes=5))
    data.guests["a"] = guest(approval=Approval())
    assert evaluate(data, seen("a"), T0 + timedelta(minutes=6)) == []
    assert not data.presence["a"].counting
    assert data.presence["a"].away_since is None

    until = T0 + timedelta(minutes=8)
    data = make(guest(approval=Approval(ApprovalKind.UNTIL, until)))
    evaluate(data, seen("a"), T0)
    evaluate(data, seen(), T0 + timedelta(minutes=5))
    assert evaluate(data, seen("a"), T0 + timedelta(minutes=10)) == []
    assert not data.presence["a"].counting


def test_home_since() -> None:
    """The earliest arrival of the guests who count; a return within the grace time keeps it."""
    data = make(guest("a"), guest("b"))
    assert home_since(data) is None
    evaluate(data, seen("a"), T0)
    evaluate(data, seen("a", "b"), T0 + timedelta(minutes=5))
    assert home_since(data) == T0
    evaluate(data, seen("b"), T0 + timedelta(minutes=10))
    assert home_since(data) == T0 + timedelta(minutes=5)
    evaluate(data, seen("a", "b"), T0 + timedelta(minutes=12))
    assert home_since(data) == T0
    evaluate(data, seen(), T0 + timedelta(minutes=20))
    assert home_since(data) is None


def test_visit_log() -> None:
    """A visit is logged once it is over, rounded to the quarter hour; a return within the grace time is the same visit."""
    data = make(guest(log_visits=True))
    evaluate(data, seen("a"), T0 + timedelta(minutes=2))
    evaluate(data, seen(), T0 + timedelta(minutes=30))
    evaluate(data, seen("a"), T0 + timedelta(minutes=35))
    evaluate(data, seen(), T0 + timedelta(minutes=65))
    assert data.visits == []
    evaluate(data, seen(), T0 + timedelta(minutes=81))
    assert len(data.visits) == 1
    visit = data.visits[0]
    assert visit.start == T0
    assert visit.minutes == 60
    assert month_minutes(data, "a", T0) == 60
    assert data.months["a"][month_key(T0)].visits == 1


def test_visit_log_short_locked_and_off() -> None:
    """A short visit counts a quarter hour; a lock ends and logs it; without a log nothing is kept."""
    data = make(guest(log_visits=True), guest("b"))
    evaluate(data, seen("a", "b"), T0)
    data.guests["a"] = replace(data.guests["a"], approval=Approval())
    evaluate(data, seen("a", "b"), T0 + timedelta(minutes=3))
    evaluate(data, seen(), T0 + timedelta(minutes=10))
    evaluate(data, seen(), T0 + timedelta(hours=1))
    assert [(v.guest_id, v.minutes) for v in data.visits] == [("a", 15)]
    assert "b" not in data.months


def test_visit_log_locked_while_away_and_stale_visit() -> None:
    """A lock while away ends the visit when the guest left; an unnoticed grace expiry too."""
    data = make(guest(log_visits=True), guest("b", log_visits=True))
    evaluate(data, seen("a", "b"), T0)
    evaluate(data, seen(), T0 + timedelta(minutes=30))
    data.guests["a"] = replace(data.guests["a"], approval=Approval())
    evaluate(data, seen(), T0 + timedelta(minutes=31))
    # b's grace time runs out without an evaluation; the next arrival logs the old visit
    evaluate(data, seen("b"), T0 + timedelta(hours=2))
    assert sorted((v.guest_id, v.minutes) for v in data.visits) == [("a", 30), ("b", 30)]


def test_visit_log_after_restart() -> None:
    """A guest locked while waiting to resume ends the visit at the restart."""
    data = make(guest(log_visits=True))
    evaluate(data, seen("a"), T0)
    prepare_restart(data, T0 + timedelta(minutes=45))
    data.guests["a"] = replace(data.guests["a"], approval=Approval())
    evaluate(data, seen(), T0 + timedelta(minutes=46))
    assert [v.minutes for v in data.visits] == [45]


def test_prune_and_forget_log() -> None:
    """Single visits go after 90 days, totals after 13 months; forgetting removes both."""
    data = make(guest(log_visits=True))
    for days in (0, 100):
        evaluate(data, seen("a"), T0 - timedelta(days=days))
        evaluate(data, seen(), T0 - timedelta(days=days) + timedelta(hours=1))
        evaluate(data, seen(), T0 - timedelta(days=days) + timedelta(hours=2))
    data.months["a"]["2020-01"] = data.months["a"][month_key(T0)]
    prune_log(data, T0 + timedelta(hours=3))
    assert len(data.visits) == 1
    assert "2020-01" not in data.months["a"]
    assert month_key(T0 - timedelta(days=100)) in data.months["a"]
    forget_log(data, "a")
    assert data.visits == []
    assert "a" not in data.months
    data.months["a"] = {"2020-01": data.months.get("x", {}).get("y") or MonthTotal(1, 15)}
    prune_log(data, T0)
    assert "a" not in data.months


def test_visit_log_settings() -> None:
    """Grid, keeping and resume time come from the settings."""
    from custom_components.guest_access.model import Settings

    data = make(guest(log_visits=True))
    data.settings = Settings(("person.sam",), ROOMS, 5, 30, 1, 1)
    evaluate(data, seen("a"), T0 + timedelta(minutes=10))
    evaluate(data, seen(), T0 + timedelta(minutes=80))
    evaluate(data, seen(), T0 + timedelta(minutes=96))
    assert [(v.start, v.minutes) for v in data.visits] == [(T0, 60)]
    prepare_restart(data, T0 + timedelta(hours=2))
    evaluate(data, seen(), T0 + timedelta(days=2))
    assert data.visits == []
