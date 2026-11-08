"""The data: windows, approvals, guests, settings and their JSON form."""

from __future__ import annotations

from datetime import UTC, datetime, time

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.guest_access.model import (
    AccessData,
    Approval,
    ApprovalKind,
    Guest,
    Lock,
    Presence,
    Room,
    Settings,
    Window,
)


def local(hass: HomeAssistant, text: str) -> datetime:
    """A local time of the test instance."""
    return datetime.fromisoformat(text).replace(tzinfo=dt_util.get_default_time_zone())


WEEKDAYS = frozenset(range(5))


async def test_window_daytime(hass: HomeAssistant) -> None:
    """A window during the day applies on its weekdays between start and end."""
    window = Window(WEEKDAYS, time(8), time(18))
    # 2026-11-09 is a Monday
    assert window.contains(local(hass, "2026-11-09T08:00"))
    assert window.contains(local(hass, "2026-11-09T17:59"))
    assert not window.contains(local(hass, "2026-11-09T18:00"))
    assert not window.contains(local(hass, "2026-11-09T07:59"))
    assert not window.contains(local(hass, "2026-11-14T12:00"))
    assert window.next_change(local(hass, "2026-11-09T12:00")) == local(hass, "2026-11-09T18:00")
    assert window.next_change(local(hass, "2026-11-09T19:00")) == local(hass, "2026-11-10T08:00")


async def test_window_overnight(hass: HomeAssistant) -> None:
    """A window past midnight covers the evening of a listed day and the morning after it."""
    window = Window(frozenset({4}), time(20), time(2))
    assert window.contains(local(hass, "2026-11-13T21:00"))
    assert window.contains(local(hass, "2026-11-14T01:00"))
    assert not window.contains(local(hass, "2026-11-14T03:00"))
    assert not window.contains(local(hass, "2026-11-12T21:00"))


@pytest.mark.parametrize(
    ("weekdays", "start", "end"),
    [
        (frozenset(), time(8), time(9)),
        (frozenset({7}), time(8), time(9)),
        (WEEKDAYS, time(8), time(8)),
    ],
)
def test_window_invalid(weekdays: frozenset[int], start: time, end: time) -> None:
    """Empty weekdays, unknown weekdays and an empty range are rejected."""
    with pytest.raises(ValueError):
        Window(weekdays, start, end)


UNTIL = datetime(2026, 12, 1, 11, tzinfo=UTC)


@pytest.mark.parametrize(
    ("kind", "until", "windows"),
    [
        (ApprovalKind.ONCE, None, ()),
        (ApprovalKind.UNTIL, None, ()),
        (ApprovalKind.OFF, UNTIL, ()),
        (ApprovalKind.PERMANENT, UNTIL, ()),
        (ApprovalKind.ONCE, UNTIL, (Window(WEEKDAYS, time(8), time(9)),)),
        (ApprovalKind.UNTIL, datetime(2026, 12, 1), ()),
    ],
)
def test_approval_invalid(
    kind: ApprovalKind, until: datetime | None, windows: tuple[Window, ...]
) -> None:
    """Combinations the kinds do not allow are rejected."""
    with pytest.raises(ValueError):
        Approval(kind, until, windows)


async def test_approval_valid(hass: HomeAssistant) -> None:
    """Off never applies, an end stops it, a window limits it."""
    before = datetime(2026, 11, 30, tzinfo=UTC)
    assert not Approval().valid(before)
    assert Approval().next_change(before) is None
    assert Approval(ApprovalKind.PERMANENT).valid(before)
    assert Approval(ApprovalKind.PERMANENT).next_change(before) is None
    until = Approval(ApprovalKind.UNTIL, UNTIL)
    assert until.valid(before)
    assert not until.valid(UNTIL)
    assert until.next_change(before) == UNTIL
    assert until.next_change(UNTIL) is None
    windowed = Approval(ApprovalKind.PERMANENT, None, (Window(WEEKDAYS, time(8), time(18)),))
    assert windowed.valid(local(hass, "2026-11-09T09:00"))
    assert not windowed.valid(local(hass, "2026-11-09T19:00"))
    assert windowed.next_change(local(hass, "2026-11-09T09:00")) == local(hass, "2026-11-09T18:00")


def test_guest_invalid() -> None:
    """A guest needs a name, a tracker, a known time per visit and a sane grace time."""
    with pytest.raises(ValueError):
        Guest("a", " ", ("device_tracker.a",))
    with pytest.raises(ValueError):
        Guest("a", "Anna", ())
    with pytest.raises(ValueError):
        Guest("a", "Anna", ("device_tracker.a",), visit_minutes=45)
    with pytest.raises(ValueError):
        Guest("a", "Anna", ("device_tracker.a",), grace_minutes=0)
    assert Guest("a", "Anna", ("device_tracker.a",), visit_minutes=None).visit is None


def test_settings_invalid() -> None:
    """An area or a door is used once only."""
    with pytest.raises(ValueError):
        Settings((), (Room("bedroom", "binary_sensor.a"), Room("bedroom", "binary_sensor.b")))
    with pytest.raises(ValueError):
        Settings((), (Room("bedroom", "binary_sensor.a"), Room("office", "binary_sensor.a")))
    settings = Settings((), (Room("bedroom", "binary_sensor.a"),))
    assert settings.room("bedroom") == Room("bedroom", "binary_sensor.a")
    assert settings.room("office") is None


def test_round_trip() -> None:
    """Everything comes back from its JSON form unchanged."""
    data = AccessData(
        settings=Settings(("person.sam",), (Room("bedroom", "binary_sensor.door"),)),
        guests={
            "a": Guest(
                "a",
                "Anna",
                ("device_tracker.a",),
                Approval(ApprovalKind.UNTIL, UNTIL, (Window(WEEKDAYS, time(8), time(18)),)),
                rooms=("bedroom",),
                visit_minutes=None,
                grace_minutes=20,
            )
        },
        presence={
            "a": Presence(True, UNTIL, UNTIL, None, UNTIL, True, False),
            "gone": Presence(),
        },
        lock=Lock(True, frozenset({"bedroom"})),
    )
    stored = data.as_dict()
    assert "gone" not in stored["presence"]
    again = AccessData.from_dict(stored)
    assert again.as_dict() == stored
    assert AccessData.from_dict({}).as_dict() == AccessData().as_dict()


async def test_window_next_change_when_clocks_go_back(hass: HomeAssistant) -> None:
    """In the repeated hour the next end is still ahead, not behind."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    window = Window(frozenset(range(7)), time(1), time(2, 30))
    # 2026-10-25 02:10 CET, the second pass of the hour, is 01:10 UTC
    moment = datetime(2026, 10, 25, 1, 10, tzinfo=UTC)
    assert window.contains(moment)
    assert window.next_change(moment) == datetime(2026, 10, 25, 1, 30, tzinfo=UTC)


async def test_approval_several_windows(hass: HomeAssistant) -> None:
    """Several windows: the approval applies within any of them (Mon-Fri 8-18 and Sat 10-14)."""
    approval = Approval(
        ApprovalKind.PERMANENT,
        None,
        (Window(WEEKDAYS, time(8), time(18)), Window(frozenset({5}), time(10), time(14))),
    )
    assert approval.valid(local(hass, "2026-11-09T09:00"))
    assert approval.valid(local(hass, "2026-11-14T11:00"))
    assert not approval.valid(local(hass, "2026-11-14T15:00"))
    assert not approval.valid(local(hass, "2026-11-15T11:00"))
    assert approval.next_change(local(hass, "2026-11-14T11:00")) == local(hass, "2026-11-14T14:00")
