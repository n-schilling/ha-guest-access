"""Check the page in a real browser against a throwaway Home Assistant.

Starts Home Assistant with made-up guests in a temporary directory, reachable
from this machine only (see run_hass.py), drives the page with Playwright and
checks what the page shows and what reaches the integration. Home Assistant is
stopped through its own stop action at the end, also after a failure.

Usage (from the repository root, with the packages of requirements_panel.txt):

    python -I scripts/panel/check_panel.py [--screenshots DIR] [--keep]
        [--browser chrome|chromium] [--headed]

--screenshots writes the pictures of the README into DIR (docs/screenshots).
--keep leaves the temporary directory for a look at the log.
"""

from __future__ import annotations

import argparse
import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import io
import json
from pathlib import Path
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import Browser, Page, async_playwright

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "guest_access"
TIME_ZONE = ZoneInfo("Europe/Berlin")
# Accounts of the throwaway instance; it listens on 127.0.0.1 only and is deleted afterwards
ADMIN = ("admin", "panel-check-admin")
USER = ("user", "panel-check-user")

TRACKERS = {
    "sam_phone": ("Sam's phone", "home"),
    "robin_phone": ("Robin's phone", "not_home"),
    "anna_phone": ("Anna's phone", "home"),
    "anna_watch": ("Anna's watch", "home"),
    "ben_phone": ("Ben's phone", "home"),
    "cleaner_tag": ("Cleaning service key tag", "not_home"),
    "grandma_phone": ("Grandma's phone", "not_home"),
    "chris_phone": ("Chris's phone", "not_home"),
}


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _configuration(port: int) -> str:
    customize = "".join(
        f'    device_tracker.{dev}:\n      friendly_name: "{name}"\n'
        for dev, (name, _) in TRACKERS.items()
    )
    return f"""homeassistant:
  name: Home
  time_zone: {TIME_ZONE.key}
  unit_system: metric
  country: DE
  language: en
  customize:
{customize}http:
  server_host: 127.0.0.1
  server_port: {port}
frontend:
config:
person:
device_tracker:
logger:
  default: warning
template:
  - binary_sensor:
      - name: Office door
        device_class: door
        state: "off"
      - name: Bedroom door
        device_class: door
        state: "off"
      - name: Kids room door
        device_class: door
        state: "on"
"""


def _store(areas: dict[str, str], now: datetime) -> dict[str, Any]:
    """Five made-up guests, and a visit log for Anna and the cleaning service."""

    def window(days: list[int], start: str, end: str) -> dict[str, Any]:
        return {"weekdays": days, "start": start, "end": end}

    def hour(moment: datetime) -> str:
        return moment.replace(minute=0, second=0, microsecond=0).isoformat()

    guests = [
        {
            "id": "g_anna",
            "name": "Anna",
            "trackers": ["device_tracker.anna_phone", "device_tracker.anna_watch"],
            "approval": {"kind": "permanent", "until": None, "windows": []},
            "rooms": [areas["Office"]],
            "all_rooms": False,
            "visit_minutes": None,
            "grace_minutes": 15,
            "log_visits": True,
        },
        {
            "id": "g_ben",
            "name": "Ben",
            "trackers": ["device_tracker.ben_phone"],
            "approval": {"kind": "once", "until": hour(now + timedelta(hours=5)), "windows": []},
            "rooms": [],
            "all_rooms": False,
            "visit_minutes": 180,
            "grace_minutes": 15,
            "log_visits": False,
        },
        {
            "id": "g_clean",
            "name": "Cleaning service",
            "trackers": ["device_tracker.cleaner_tag"],
            "approval": {
                "kind": "permanent",
                "until": None,
                # Two days after today and later: outside every window whenever the check runs
                "windows": [
                    window([(now.weekday() + 2) % 7], "09:00", "12:00"),
                    window([(now.weekday() + 4) % 7], "14:00", "16:00"),
                ],
            },
            "rooms": [],
            "all_rooms": True,
            "visit_minutes": 240,
            "grace_minutes": 10,
            "log_visits": True,
        },
        {
            "id": "g_grandma",
            "name": "Grandma",
            "trackers": ["device_tracker.grandma_phone"],
            "approval": {
                "kind": "until",
                "until": hour((now + timedelta(days=40)).replace(hour=0)),
                "windows": [],
            },
            "rooms": [areas["Kids room"]],
            "all_rooms": False,
            "visit_minutes": None,
            "grace_minutes": 30,
            "log_visits": False,
        },
        {
            "id": "g_chris",
            "name": "Chris",
            "trackers": ["device_tracker.chris_phone"],
            "approval": {"kind": "off", "until": None, "windows": []},
            "rooms": [],
            "all_rooms": False,
            "visit_minutes": 60,
            "grace_minutes": 15,
            "log_visits": False,
        },
    ]
    rng = random.Random(7)
    visits: list[dict[str, Any]] = []
    months: dict[str, dict[str, dict[str, int]]] = {}

    def add(guest_id: str, start: datetime, minutes: int) -> None:
        visits.append({"guest_id": guest_id, "start": start.isoformat(), "minutes": minutes})
        total = months.setdefault(guest_id, {}).setdefault(
            start.strftime("%Y-%m"), {"visits": 0, "minutes": 0}
        )
        total["visits"] += 1
        total["minutes"] += minutes

    day = now - timedelta(days=75)
    while day.date() < now.date():
        if day.weekday() in (2, 5) and rng.random() < 0.8:
            start = day.replace(
                hour=rng.choice([10, 14, 15, 16]),
                minute=rng.choice([0, 15, 30, 45]),
                second=0,
                microsecond=0,
            )
            add("g_anna", start, rng.choice([90, 120, 150, 180, 240]))
        if day.weekday() == 1:
            add(
                "g_clean",
                day.replace(hour=9, minute=0, second=0, microsecond=0),
                rng.choice([150, 165, 180]),
            )
        day += timedelta(days=1)
    return {
        "version": 1,
        "minor_version": 1,
        "key": "guest_access",
        "data": {
            "settings": {
                "residents": ["person.sam", "person.robin"],
                "rooms": [
                    {"area_id": areas["Office"], "door": "binary_sensor.office_door"},
                    {"area_id": areas["Bedroom"], "door": "binary_sensor.bedroom_door"},
                    {"area_id": areas["Kids room"], "door": "binary_sensor.kids_room_door"},
                ],
            },
            "guests": guests,
            "presence": {},
            "lock": {},
            "visits": visits,
            "months": months,
        },
    }


def _avatar(initial: str, color: tuple[int, int, int]) -> bytes:
    """A made-up photo: an initial on a colour, as PNG."""
    image = Image.new("RGB", (256, 256), color)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=150)
    draw.text((128, 128), initial, fill=(255, 255, 255), font=font, anchor="mm")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class Api:
    """REST and WebSocket access to the throwaway instance."""

    def __init__(self, session: aiohttp.ClientSession, base: str) -> None:
        self.session = session
        self.base = base
        self.client_id = f"{base}/"

    async def login(self, username: str, password: str) -> str:
        """An access token for a user, through the login flow the page uses."""
        flow = await self._json(
            "post",
            "/auth/login_flow",
            json={
                "client_id": self.client_id,
                "handler": ["homeassistant", None],
                "redirect_uri": self.client_id,
            },
        )
        step = await self._json(
            "post",
            f"/auth/login_flow/{flow['flow_id']}",
            json={"client_id": self.client_id, "username": username, "password": password},
        )
        token = await self._json(
            "post",
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": step["result"],
                "client_id": self.client_id,
            },
        )
        return str(token["access_token"])

    async def _json(self, method: str, path: str, **kwargs: Any) -> Any:
        async with self.session.request(method, self.base + path, **kwargs) as response:
            response.raise_for_status()
            return await response.json()

    async def post(self, token: str, path: str, body: dict[str, Any] | None = None) -> Any:
        """A REST call as the user of the token."""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._json("post", path, headers=headers, json=body or {})

    async def upload(self, token: str, png: bytes) -> str:
        """Upload an image as the page does; its ID."""
        form = aiohttp.FormData()
        form.add_field("file", png, filename="photo.png", content_type="image/png")
        headers = {"Authorization": f"Bearer {token}"}
        async with self.session.post(
            self.base + "/api/image/upload", data=form, headers=headers
        ) as response:
            response.raise_for_status()
            return str((await response.json())["id"])

    async def ws(self, token: str, message: dict[str, Any]) -> dict[str, Any]:
        """One WebSocket command; the whole result message, success or not."""
        async with self.session.ws_connect(self.base + "/api/websocket") as ws:
            await ws.receive_json()
            await ws.send_json({"type": "auth", "access_token": token})
            if (await ws.receive_json())["type"] != "auth_ok":
                raise RuntimeError("WebSocket login failed")
            await ws.send_json({"id": 1, **message})
            while True:
                reply = await ws.receive_json()
                if reply.get("id") == 1 and reply.get("type") == "result":
                    return dict(reply)


class Instance:
    """A throwaway Home Assistant with made-up guests."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.config = directory / "config"
        self.port = _free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.process: subprocess.Popen[bytes] | None = None
        self.token = ""
        self.entry_id = ""

    def _launch(self) -> None:
        """Copy the integration and start Home Assistant in the background."""
        (self.config / "custom_components").mkdir(parents=True)
        shutil.copytree(
            INTEGRATION,
            self.config / "custom_components" / "guest_access",
            ignore=shutil.ignore_patterns("__pycache__", "BUILD"),
        )
        commit = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        (self.config / "custom_components" / "guest_access" / "BUILD").write_text(
            commit or "panel-check"
        )
        (self.config / "configuration.yaml").write_text(_configuration(self.port))
        log = (self.directory / "hass.log").open("wb")
        self.process = subprocess.Popen(
            [
                sys.executable,
                "-I",
                str(Path(__file__).with_name("run_hass.py")),
                "-c",
                str(self.config),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    async def start(self, session: aiohttp.ClientSession) -> Api:
        """Start, onboard and set up Guest Access with the made-up guests."""
        await asyncio.to_thread(self._launch)
        api = Api(session, self.base)
        await self._wait_ready(session)
        self.token = await self._onboard(api)
        await self._seed(api)
        return api

    async def _wait_ready(self, session: aiohttp.ClientSession) -> None:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(f"Home Assistant ended, see {self.directory / 'hass.log'}")
            try:
                async with session.get(self.base + "/api/onboarding") as response:
                    if response.status == 200:
                        return
            except aiohttp.ClientError:
                pass
            await asyncio.sleep(1)
        raise RuntimeError("Home Assistant did not start within 3 minutes")

    async def _onboard(self, api: Api) -> str:
        user = await api._json(
            "post",
            "/api/onboarding/users",
            json={
                "client_id": api.client_id,
                "name": "Sam",
                "username": ADMIN[0],
                "password": ADMIN[1],
                "language": "en",
            },
        )
        token = await api._json(
            "post",
            "/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": user["auth_code"],
                "client_id": api.client_id,
            },
        )
        access = str(token["access_token"])
        await api.post(access, "/api/onboarding/core_config")
        await api.post(access, "/api/onboarding/analytics")
        await api.post(
            access,
            "/api/onboarding/integration",
            {"client_id": api.client_id, "redirect_uri": api.client_id},
        )
        # The HTTP settings of configuration.yaml start as a trial that the page
        # asks to confirm and that reverts after five minutes; keep them
        promoted = await api.ws(access, {"type": "http/config/promote"})
        if not promoted["success"]:
            raise RuntimeError(f"HTTP settings not kept: {promoted}")
        return access

    async def _seed(self, api: Api) -> None:
        listed = await api.ws(self.token, {"type": "config/area_registry/list"})
        areas = {area["name"].capitalize(): area["area_id"] for area in listed["result"]}
        for name in ("Office", "Bedroom", "Kids room"):
            if name not in areas:
                created = await api.ws(
                    self.token, {"type": "config/area_registry/create", "name": name}
                )
                areas[name] = created["result"]["area_id"]
        for dev, (_, location) in TRACKERS.items():
            await api.post(
                self.token,
                "/api/services/device_tracker/see",
                {"dev_id": dev, "location_name": location},
            )
        await api.ws(
            self.token,
            {
                "type": "person/create",
                "name": "Robin",
                "device_trackers": ["device_tracker.robin_phone"],
            },
        )
        persons = await api.ws(self.token, {"type": "person/list"})
        for person in persons["result"]["storage"]:
            if person["name"] == "Sam":
                await api.ws(
                    self.token,
                    {
                        "type": "person/update",
                        "person_id": person["id"],
                        "name": "Sam",
                        "user_id": person.get("user_id"),
                        "device_trackers": ["device_tracker.sam_phone"],
                    },
                )
        store = _store(areas, datetime.now(TIME_ZONE))
        photos = {"g_anna": ("A", (94, 129, 172)), "g_ben": ("B", (191, 97, 106))}
        for guest in store["data"]["guests"]:
            if guest["id"] in photos:
                guest["picture"] = await api.upload(self.token, _avatar(*photos[guest["id"]]))
        (self.config / ".storage" / "guest_access").write_text(json.dumps(store))
        flow = await api.post(
            self.token, "/api/config/config_entries/flow", {"handler": "guest_access"}
        )
        result = await api.post(self.token, f"/api/config/config_entries/flow/{flow['flow_id']}")
        if result.get("type") != "create_entry" or result["result"]["state"] != "loaded":
            raise RuntimeError(f"Guest Access did not load: {result}")
        self.entry_id = result["result"]["entry_id"]
        # A user without administrator rights, for the access check
        created = await api.ws(
            self.token,
            {"type": "config/auth/create", "name": "Visitor", "group_ids": ["system-users"]},
        )
        await api.ws(
            self.token,
            {
                "type": "config/auth_provider/homeassistant/create",
                "user_id": created["result"]["user"]["id"],
                "username": USER[0],
                "password": USER[1],
            },
        )

    async def stop(self, session: aiohttp.ClientSession) -> None:
        """Stop through Home Assistant's own stop action; force only if that fails."""
        if self.process is None or self.process.poll() is not None:
            return
        try:
            if self.token:
                async with session.post(
                    self.base + "/api/services/homeassistant/stop",
                    headers={"Authorization": f"Bearer {self.token}"},
                ):
                    pass
        except aiohttp.ClientError:
            pass
        try:
            self.process.wait(timeout=60)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=30)


@dataclass
class Checks:
    """The checks that ran and the ones that failed."""

    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    before: Callable[[], Awaitable[None]] | None = None

    async def run(self, name: str, check: Callable[[], Awaitable[None]]) -> None:
        try:
            if self.before is not None:
                await self.before()
            await check()
        except Exception as err:
            self.failed.append(f"{name}: {err!r}")
            print(f"FAIL {name}: {err!r}")
        else:
            self.passed.append(name)
            print(f"ok   {name}")


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


# The page lives in shadow roots; Playwright's CSS selectors pierce them
PANEL = "guest-access-panel"


async def _open(
    browser: Browser, instance: Instance, user: tuple[str, str], **options: Any
) -> Page:
    """A new page, logged in, on the Guest Access page."""
    context = await browser.new_context(
        viewport=options.pop("viewport", {"width": 1000, "height": 760}),
        device_scale_factor=2,
        locale="en-US",
        timezone_id=TIME_ZONE.key,
        color_scheme=options.pop("color_scheme", "light"),
    )
    page = await context.new_page()
    await page.goto(f"{instance.base}/guest-access")
    await page.get_by_label("Username").fill(user[0])
    await page.get_by_label("Password", exact=True).fill(user[1])
    await page.keyboard.press("Enter")
    await page.wait_for_load_state("networkidle")
    # Keep the sidebar out of the pictures
    await page.evaluate("localStorage.setItem('dockedSidebar', JSON.stringify('always_hidden'))")
    await page.reload()
    await page.wait_for_load_state("networkidle")
    return page


async def _list(page: Page) -> None:
    """The list is there and Home Assistant's loading screen has faded out."""
    # The first load of the frontend takes a while on a slow CI machine
    await page.locator(f"{PANEL} [data-edit]").first.wait_for(timeout=90000)
    await page.locator("#ha-launch-screen").wait_for(state="detached")


async def _headlines(page: Page) -> list[str]:
    return [
        text.strip() for text in await page.locator(f"{PANEL} .item .headline").all_inner_texts()
    ]


async def _snapshot(api: Api, instance: Instance) -> dict[str, Any]:
    """What the page gets: guests, settings and state."""
    async with api.session.ws_connect(api.base + "/api/websocket") as ws:
        await ws.receive_json()
        await ws.send_json({"type": "auth", "access_token": instance.token})
        await ws.receive_json()
        await ws.send_json({"id": 1, "type": "guest_access/subscribe"})
        while True:
            reply = await ws.receive_json()
            if reply.get("type") == "event":
                return dict(reply["event"])


def _guest(snapshot: dict[str, Any], guest_id: str) -> dict[str, Any] | None:
    return next((guest for guest in snapshot["guests"] if guest["id"] == guest_id), None)


async def _until(check: Callable[[], Awaitable[bool]], what: str, seconds: float = 10) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if await check():
            return
        await asyncio.sleep(0.2)
    raise AssertionError(f"timed out waiting for {what}")


async def check_page(browser: Browser, instance: Instance, api: Api, shots: Path | None) -> Checks:
    page = await _open(browser, instance, ADMIN)

    async def from_list() -> None:
        """Every check starts on the list, whatever the one before left behind."""
        await page.goto(f"{instance.base}/guest-access")
        await _list(page)

    checks = Checks(before=from_list)

    async def list_shows_guests() -> None:
        await _list(page)
        headlines = await _headlines(page)
        expect(len(headlines) == 5, f"5 guests expected, got {headlines}")
        expect(headlines[0].startswith("Anna · Counts as home"), headlines[0])
        expect(any(line.startswith("Chris · No approval") for line in headlines), str(headlines))
        text = await page.locator(f"{PANEL} #content").inner_text()
        expect("Sam, Robin" in text, "residents missing")
        expect("Office, Bedroom, Kids room" in text, "lockable rooms missing")
        about = await page.locator(f"{PANEL} .about").inner_text()
        expect(about.startswith("Guest Access ") and "commit" in about.lower(), about)
        expect(
            await page.locator(f"{PANEL} [data-lock='g_chris']").count() == 0,
            "locked guest has a lock button",
        )

    async def window_is_not_expiry() -> None:
        clean = page.locator(f"{PANEL} [data-edit='g_clean'] .supporting").first
        text = await clean.inner_text()
        expect(text.endswith(" (outside the time windows)"), text)

    await checks.run("list shows guests, residents, rooms and version", list_shows_guests)
    await checks.run("a guest outside its windows is not shown as expired", window_is_not_expiry)
    if shots is not None:
        await page.screenshot(path=str(shots / "guests.png"))

    async def edit_shows_windows() -> None:
        await page.locator(f"{PANEL} [data-edit='g_clean']").click()
        await page.get_by_text("Time windows", exact=True).wait_for()
        await page.get_by_text("Cleaning service key tag").first.wait_for()
        weekday = (datetime.now(TIME_ZONE) + timedelta(days=2)).strftime("%A")
        await page.get_by_text(weekday, exact=True).first.wait_for()
        if shots is not None:
            await page.set_viewport_size({"width": 1000, "height": 1240})
            await page.screenshot(path=str(shots / "guest.png"))
            await page.set_viewport_size({"width": 1000, "height": 760})
        await page.locator(f"{PANEL} #back").click()
        await _list(page)

    await checks.run("form of a guest with tracker and time windows", edit_shows_windows)

    async def visit_log() -> None:
        await page.locator(f"{PANEL} [data-edit='g_anna']").click()
        card = page.locator(f"{PANEL} ha-card", has_text="Visit log").first
        await card.wait_for()
        await card.scroll_into_view_if_needed()
        text = await card.inner_text()
        expect("Visit running since" in text, "running visit missing")
        expect("Last month:" in text and "visits" in text, "monthly total missing")
        expect(" 1 visits" not in text, "plural for one visit")
        if shots is not None:
            await page.wait_for_timeout(300)
            await card.screenshot(path=str(shots / "visit-log.png"))
        async with page.expect_download() as download:
            await card.get_by_role("button", name="Export as CSV").click()
        path = await (await download.value).path()
        csv = await asyncio.to_thread(Path(path).read_text, encoding="utf-8-sig")
        expect(csv.count("\n") > 10, "CSV has too few rows")
        await page.locator(f"{PANEL} #back").click()
        await _list(page)

    await checks.run("visit log with totals and CSV export", visit_log)

    async def rename_guest() -> None:
        await page.locator(f"{PANEL} [data-edit='g_ben']").click()
        name = page.get_by_role("textbox", name="Name")
        await name.fill("Ben Example")
        await page.get_by_role("button", name="Save").click()
        await _list(page)

        async def renamed() -> bool:
            guest = _guest(await _snapshot(api, instance), "g_ben")
            return guest is not None and guest["name"] == "Ben Example"

        await _until(renamed, "the new name in the integration")
        expect(
            any(line.startswith("Ben Example ·") for line in await _headlines(page)),
            "list shows the old name",
        )

    await checks.run("renaming a guest reaches the integration", rename_guest)

    async def lock_guest() -> None:
        await page.locator(f"{PANEL} [data-lock='g_grandma']").click()
        alert = page.locator(f"{PANEL} ha-alert", has_text="Lock Grandma?")
        await alert.wait_for()
        await page.locator(f"{PANEL} #confirm-ok").click()

        async def locked() -> bool:
            guest = _guest(await _snapshot(api, instance), "g_grandma")
            return guest is not None and guest["approval"]["kind"] == "off"

        await _until(locked, "the lock in the integration")
        await page.locator(f"{PANEL} [data-lock='g_grandma']").wait_for(state="detached")

    await checks.run("locking a guest after confirming", lock_guest)

    async def keyboard_on_lock_button() -> None:
        button = page.locator(f"{PANEL} [data-lock='g_anna']")
        await button.focus()
        await page.keyboard.press("Enter")
        await page.locator(f"{PANEL} ha-alert", has_text="Lock Anna?").wait_for()
        expect(
            await page.get_by_text("Time windows", exact=True).count() == 0, "Enter opened the form"
        )
        await page.locator(f"{PANEL} #confirm-cancel").click()
        guest = _guest(await _snapshot(api, instance), "g_anna")
        expect(
            guest is not None and guest["approval"]["kind"] == "permanent",
            "cancel locked the guest",
        )

    await checks.run(
        "Enter on the lock button asks, Cancel keeps the guest", keyboard_on_lock_button
    )

    async def delete_log() -> None:
        await page.locator(f"{PANEL} [data-edit='g_clean']").click()
        card = page.locator(f"{PANEL} ha-card", has_text="Visit log").first
        await card.get_by_role("button", name="Delete log").click()
        await page.locator(f"{PANEL} #confirm-ok").click()

        async def emptied() -> bool:
            guest = _guest(await _snapshot(api, instance), "g_clean")
            return guest is not None and not guest["log"]["visits"] and not guest["log"]["months"]

        await _until(emptied, "an empty visit log")
        await page.locator(f"{PANEL} #back").click()
        await _list(page)

    await checks.run("deleting a visit log after confirming", delete_log)

    async def save_error_is_shown() -> None:
        before = len((await _snapshot(api, instance))["guests"])
        await page.get_by_role("button", name="Add guest").click()
        await page.get_by_role("button", name="Save").click()
        await page.locator(f"{PANEL} ha-alert[alert-type='error']").wait_for()
        expect(
            len((await _snapshot(api, instance))["guests"]) == before, "an empty guest was saved"
        )
        await page.locator(f"{PANEL} #back").click()
        await _list(page)

    await checks.run("saving an empty guest shows the error and saves nothing", save_error_is_shown)

    async def images() -> set[str]:
        listed = await api.ws(instance.token, {"type": "image/list"})
        return {item["id"] for item in listed["result"]}

    async def photo_and_note() -> None:
        before = await images()
        await page.locator(f"{PANEL} [data-edit='g_clean']").click()
        await page.locator(f"{PANEL} input[type=file]").set_input_files(
            {"name": "c.png", "mimeType": "image/png", "buffer": _avatar("C", (163, 190, 140))}
        )
        await page.locator(f"{PANEL} .media img.avatar").wait_for()
        await page.get_by_role("textbox", name="Note").fill("Key is in the mailbox")
        await page.get_by_role("button", name="Save").click()
        await _list(page)

        async def saved() -> bool:
            guest = _guest(await _snapshot(api, instance), "g_clean")
            return (
                guest is not None
                and guest["note"] == "Key is in the mailbox"
                and bool(guest["picture"])
            )

        await _until(saved, "photo and note in the integration")
        guest = _guest(await _snapshot(api, instance), "g_clean")
        assert guest is not None
        expect(await images() == before | {guest["picture"]}, "an image too many or too few")
        await page.locator(f"{PANEL} [data-edit='g_clean'] img.photo").wait_for()
        state = await api.ws(instance.token, {"type": "get_states"})
        pictures = {
            item["entity_id"]: item["attributes"].get("entity_picture")
            for item in state["result"]
            if item["entity_id"].startswith(
                ("binary_sensor.guest_cleaning", "sensor.guest_cleaning")
            )
        }
        expect(
            pictures.get("binary_sensor.guest_cleaning_service_counts")
            == f"/api/image/serve/{guest['picture']}/512x512",
            str(pictures),
        )

    await checks.run("a photo and a note reach the integration and the dashboards", photo_and_note)

    async def cancelled_upload_leaves_nothing() -> None:
        before = await images()
        await page.locator(f"{PANEL} [data-edit='g_grandma']").click()
        await page.locator(f"{PANEL} input[type=file]").set_input_files(
            {"name": "g.png", "mimeType": "image/png", "buffer": _avatar("G", (180, 142, 173))}
        )
        await page.locator(f"{PANEL} .media img.avatar").wait_for()
        expect(len(await images()) == len(before) + 1, "the upload did not arrive")
        await page.get_by_role("button", name="Cancel").click()
        await _list(page)

        async def cleaned() -> bool:
            return await images() == before

        await _until(cleaned, "the cancelled upload to be deleted")

    await checks.run(
        "a photo uploaded and then cancelled is deleted again", cancelled_upload_leaves_nothing
    )

    async def phone_and_dark() -> None:
        for scheme in ("light", "dark"):
            phone = await _open(
                browser,
                instance,
                ADMIN,
                viewport={"width": 390, "height": 844},
                color_scheme=scheme,
            )
            await _list(phone)
            overflow = await phone.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            expect(overflow <= 0, f"{scheme}: page scrolls sideways by {overflow} px")
            await phone.locator(f"{PANEL} [data-edit='g_anna']").click()
            await phone.get_by_text("Visit log", exact=True).wait_for()
            overflow = await phone.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            expect(overflow <= 0, f"{scheme}: form scrolls sideways by {overflow} px")
            background = await phone.locator(PANEL).evaluate(
                "el => getComputedStyle(el).backgroundColor"
            )
            if scheme == "dark":
                channels = [
                    int(part) for part in background[background.index("(") + 1 : -1].split(",")[:3]
                ]
                expect(sum(channels) < 200, f"dark mode background is {background}")
            if instance.directory.exists():
                await phone.screenshot(path=str(instance.directory / f"phone-{scheme}.png"))
            await phone.context.close()

    await checks.run(
        "phone width and dark mode: no sideways scrolling, dark background", phone_and_dark
    )

    async def no_page_for_users() -> None:
        token = await api.login(*USER)
        reply = await api.ws(token, {"type": "guest_access/subscribe"})
        expect(not reply["success"] and reply["error"]["code"] == "unauthorized", str(reply))
        reply = await api.ws(token, {"type": "guest_access/lock_guest", "guest_id": "g_anna"})
        expect(not reply["success"] and reply["error"]["code"] == "unauthorized", str(reply))
        panels = await api.ws(token, {"type": "get_panels"})
        expect("guest-access" not in panels["result"], "the page is offered to a user")

    await checks.run(
        "users without administrator rights get neither page nor commands", no_page_for_users
    )
    await page.context.close()
    return checks


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--screenshots", type=Path, help="write the README pictures into this directory"
    )
    parser.add_argument("--keep", action="store_true", help="keep the temporary directory")
    parser.add_argument("--browser", choices=["chrome", "chromium"], default="chromium")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()
    if args.screenshots is not None:
        args.screenshots.mkdir(parents=True, exist_ok=True)

    directory = Path(tempfile.mkdtemp(prefix="guest-access-panel-"))
    instance = Instance(directory)
    checks = Checks()
    async with aiohttp.ClientSession() as session:
        try:
            api = await instance.start(session)
            print(f"Home Assistant on {instance.base}, files in {directory}")
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    channel="chrome" if args.browser == "chrome" else None,
                    headless=not args.headed,
                )
                try:
                    checks = await check_page(browser, instance, api, args.screenshots)
                finally:
                    await browser.close()
        except Exception as err:
            checks.failed.append(f"setup: {err!r}")
            print(f"FAIL setup: {err!r}")
            log = directory / "hass.log"
            if log.exists():
                print("".join(log.read_text(errors="replace").splitlines(keepends=True)[-60:]))
        finally:
            await instance.stop(session)
    errors = (
        [
            line
            for line in (directory / "config" / "home-assistant.log")
            .read_text(errors="replace")
            .splitlines()
            if " ERROR " in line and "guest_access" in line
        ]
        if (directory / "config" / "home-assistant.log").exists()
        else []
    )
    for line in errors:
        checks.failed.append(f"log: {line}")
        print(f"FAIL log: {line}")
    print(f"\n{len(checks.passed)} passed, {len(checks.failed)} failed")
    if args.keep or checks.failed:
        print(f"Files kept in {directory}")
    else:
        shutil.rmtree(directory, ignore_errors=True)
    return 1 if checks.failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
