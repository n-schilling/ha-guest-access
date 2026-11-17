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
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp
from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import Browser, Page, async_playwright

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "custom_components" / "guest_access"
TIME_ZONE = ZoneInfo("Europe/Berlin")
# Every wait has a limit, so a hang shows as a failed check with the line it hung
# on instead of a CI job killed without a word: one check, one WebSocket reply,
# closing a browser context, and all checks together (CI stops the step after 10 min)
CHECK_SECONDS = 150
WS_SECONDS = 30
CLOSE_SECONDS = 30
ALL_SECONDS = 420
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
            self.base + "/api/guest_access/picture", data=form, headers=headers
        ) as response:
            response.raise_for_status()
            return str((await response.json())["id"])

    async def ws(self, token: str, message: dict[str, Any]) -> dict[str, Any]:
        """One WebSocket command; the whole result message, success or not."""
        async with (
            asyncio.timeout(WS_SECONDS),
            self.session.ws_connect(self.base + "/api/websocket") as ws,
        ):
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
        (self.config / ".storage" / "guest_access").write_text(json.dumps(store))
        flow = await api.post(
            self.token, "/api/config/config_entries/flow", {"handler": "guest_access"}
        )
        result = await api.post(self.token, f"/api/config/config_entries/flow/{flow['flow_id']}")
        if result.get("type") != "create_entry" or result["result"]["state"] != "loaded":
            raise RuntimeError(f"Guest Access did not load: {result}")
        self.entry_id = result["result"]["entry_id"]
        # Made-up photos, uploaded as the page does once the integration runs
        photos = {"g_anna": ("A", (94, 129, 172)), "g_ben": ("B", (191, 97, 106))}
        for guest in store["data"]["guests"]:
            if guest["id"] in photos:
                picture = await api.upload(self.token, _avatar(*photos[guest["id"]]))
                profile = {key: value for key, value in guest.items() if key != "id"}
                saved = await api.ws(
                    self.token,
                    {
                        "type": "guest_access/save_guest",
                        **profile,
                        "guest_id": guest["id"],
                        "picture": picture,
                    },
                )
                if not saved["success"]:
                    raise RuntimeError(f"Photo not saved: {saved}")
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
                async with (
                    asyncio.timeout(WS_SECONDS),
                    session.post(
                        self.base + "/api/services/homeassistant/stop",
                        headers={"Authorization": f"Bearer {self.token}"},
                    ),
                ):
                    pass
        except aiohttp.ClientError, TimeoutError:
            pass
        try:
            await asyncio.to_thread(self.process.wait, 60)
        except subprocess.TimeoutExpired:
            self.process.kill()
            await asyncio.to_thread(self.process.wait, 30)


@dataclass
class Checks:
    """The checks that ran and the ones that failed."""

    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    before: Callable[[], Awaitable[None]] | None = None

    async def run(self, name: str, check: Callable[[], Awaitable[None]]) -> None:
        try:
            async with asyncio.timeout(CHECK_SECONDS):
                if self.before is not None:
                    await self.before()
                await check()
        except TimeoutError as err:
            # Where it waited: the innermost lines of the check
            where = "".join(traceback.format_tb(err.__traceback__)[-3:])
            self.failed.append(f"{name}: no end after {CHECK_SECONDS} s")
            print(f"FAIL {name}: no end after {CHECK_SECONDS} s, waiting at\n{where}")
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
STAMP = re.compile(r"^As of \d\d:\d\d:\d\d$")
INTEGRATION_PAGE = "/config/integrations/integration/guest_access"
VERSION = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))["version"]
# The pages of the two areas, and the tab each one marks below the header (None: no tabs)
PAGES = {
    "guests/list": None,
    "setup/overview": "overview",
    "setup/residents": "residents",
    "setup/rooms": "rooms",
    "setup/timings": "timings",
}
ROW = f"{PANEL} .item[data-act='open']"
# What each page sent over its WebSocket, for the refresh check
SENT: dict[Page, list[dict[str, Any]]] = {}


# Home Assistant's frame on the page, found through the shadow roots: where it sits, how high
# its header is and where its tab bar (at the bottom on a phone) starts and ends, in px
SAFE_AREA_MEASURE = """() => {
  const find = (root) => {
    for (const el of root.querySelectorAll('*')) {
      if (el.localName === 'hass-tabs-subpage') return el;
      const inner = el.shadowRoot && find(el.shadowRoot);
      if (inner) return inner;
    }
    return null;
  };
  const frame = find(document);
  if (!frame) return { viewport: innerHeight, frame: null, toolbar: null, tabbar: null };
  const span = (el) => {
    if (!el) return null;
    const box = el.getBoundingClientRect();
    return [Math.round(box.top), Math.round(box.bottom)];
  };
  const toolbar = frame.shadowRoot.querySelector('.toolbar');
  const bar = frame.shadowRoot.querySelector('#tabbar.bottom-bar');
  return {
    viewport: innerHeight,
    frame: span(frame),
    toolbar: toolbar ? Math.round(toolbar.getBoundingClientRect().height) : null,
    tabbar: span(bar),
  };
}"""


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
    sent: list[dict[str, Any]] = []
    SENT[page] = sent

    def on_frame(payload: str | bytes) -> None:
        try:
            message = json.loads(payload)
        except ValueError:
            return
        sent.extend(message if isinstance(message, list) else [message])

    page.on("websocket", lambda ws: ws.on("framesent", on_frame))
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


async def _goto(page: Page, instance: Instance, path: str) -> None:
    """A page of the panel, with its content drawn and Home Assistant's loading screen gone."""
    await page.goto(f"{instance.base}/guest-access/{path}")
    # The first load of the frontend takes a while on a slow CI machine
    await page.locator(f"{PANEL} hass-tabs-subpage").first.wait_for(timeout=90000)
    await page.locator("#ha-launch-screen").wait_for(state="detached")
    await _ready(page)


async def _ready(page: Page) -> None:
    """The content of the page in the address is drawn."""
    if "?key=" in page.url:
        await page.locator(f"{PANEL} .subname").wait_for()
        await page.locator(f"{PANEL} #sheet ha-card").first.wait_for()
    elif "/guests/list" in page.url:
        await page.locator(ROW).first.wait_for(timeout=60000)
    else:
        await page.locator(f"{PANEL} #sheet ha-card").first.wait_for(timeout=60000)


async def _headlines(page: Page) -> list[str]:
    return [text.strip() for text in await page.locator(f"{ROW} .headline").all_inner_texts()]


async def _snapshot(api: Api, instance: Instance) -> dict[str, Any]:
    """What the page gets: guests, settings and state."""
    async with (
        asyncio.timeout(WS_SECONDS),
        api.session.ws_connect(api.base + "/api/websocket") as ws,
    ):
        await ws.receive_json()
        await ws.send_json({"type": "auth", "access_token": instance.token})
        await ws.receive_json()
        await ws.send_json({"id": 1, "type": "guest_access/subscribe"})
        while True:
            reply = await ws.receive_json()
            if reply.get("type") == "event":
                return dict(reply["event"])
            # A refused subscription sends no event: fail instead of waiting for one
            if reply.get("type") == "result" and not reply.get("success"):
                raise RuntimeError(f"subscription refused: {reply}")


def _guest(snapshot: dict[str, Any], guest_id: str) -> dict[str, Any] | None:
    return next((guest for guest in snapshot["guests"] if guest["id"] == guest_id), None)


async def _frame(page: Page, *, sub: bool, page_id: str | None = None) -> dict[str, Any]:
    """Home Assistant's frame: the two areas as tabs and the menu, or a back arrow and a name."""
    info: dict[str, Any] = await page.locator(PANEL).evaluate(
        """el => {
          const frame = el.shadowRoot.getElementById('frame');
          const bar = frame.shadowRoot.getElementById('tabbar');
          const tabs = bar ? [...bar.querySelectorAll('ha-tab')] : [];
          const active = el.shadowRoot.querySelector('#subtabs ha-tab-group-tab[active]');
          return {
            tabs: tabs.length,
            names: tabs.map((t) => t.textContent.trim()),
            active: tabs.filter((t) => t.active).length,
            bottom: !!bar && bar.classList.contains('bottom-bar'),
            back: !!frame.shadowRoot.querySelector('ha-icon-button-arrow-prev'),
            menu: !!frame.shadowRoot.querySelector('ha-menu-button'),
            name: el.shadowRoot.querySelector('.subname')?.textContent.trim() || null,
            page: active ? active.getAttribute('panel') : null,
            views: el.shadowRoot.querySelectorAll('#views ha-tab-group-tab').length,
          };
        }"""
    )
    if sub:
        expect(info["tabs"] == 0 and info["back"] and not info["menu"], f"subpage frame {info}")
        expect(bool(info["name"]), f"no name in the header {info}")
        expect(info["views"] == 4, f"the views of a guest {info}")
    else:
        expect(
            info["tabs"] == 2 and info["active"] == 1 and info["menu"] and not info["back"],
            f"frame {info}",
        )
        expect(info["page"] == page_id, f"tab of the page: {info['page']} for {page_id}")
    return info


async def _header(page: Page) -> None:
    """The header's actions on every page and subpage: stamp, refresh, integration."""
    order = await page.locator(PANEL).evaluate(
        "el => [...el.shadowRoot.querySelector('[slot=toolbar-icon]').children].map(e => e.id)"
    )
    expect(order == ["stamp", "refresh", "integration"], f"header actions {order}")
    stamp = page.locator(f"{PANEL} #stamp")
    await _until(lambda: _stamp_ok(stamp), "the stamp 'As of HH:MM:SS' in the header")
    for button, path, label in (
        ("refresh", "M17.65,6.35", "Refresh"),
        ("integration", "M12,8A4,4", "Integration in Home Assistant"),
    ):
        el = page.locator(f"{PANEL} ha-icon-button#{button}")
        expect(await el.is_visible(), f"{button} button not visible")
        expect((await el.get_attribute("path") or "").startswith(path), f"{button}: wrong icon")
        expect(await el.get_attribute("label") == label, f"{button}: label")


async def _stamp_ok(stamp: Any) -> bool:
    return await stamp.is_visible() and bool(STAMP.match((await stamp.inner_text()).strip()))


async def _refresh(page: Page) -> None:
    """The refresh button subscribes again, spins meanwhile and moves the stamp on."""
    stamp = page.locator(f"{PANEL} #stamp")
    before = (await stamp.inner_text()).strip()
    # The stamp has seconds; a refresh in the same second would not move it
    await page.wait_for_timeout(1100)
    sent = SENT[page]
    count = len(sent)
    url = page.url
    await page.evaluate("window.__noReload = true")
    # Clicked from the page itself, so the spinning is seen before the data are back
    spinning = await page.locator(f"{PANEL} ha-icon-button#refresh").evaluate(
        "el => { el.click(); return el.classList.contains('loading'); }"
    )
    expect(spinning, "the refresh button does not spin while loading")
    await page.locator(f"{PANEL} ha-icon-button#refresh:not(.loading)").wait_for()
    after = (await stamp.inner_text()).strip()
    expect(bool(STAMP.match(after)) and after != before, f"stamp {before!r} -> {after!r}")
    types = [message.get("type") for message in sent[count:]]
    expect("unsubscribe_events" in types, f"old subscription not ended: {types}")
    expect("guest_access/subscribe" in types, f"data not fetched again: {types}")
    expect(page.url == url, f"refresh left the page: {page.url}")
    expect(await page.evaluate("window.__noReload === true"), "Refresh reloaded the page")


async def _integration_button(page: Page, instance: Instance) -> None:
    """The integration button opens the integration's page inside the app, no reload."""
    await page.evaluate("window.__noReload = true")
    await page.locator(f"{PANEL} ha-icon-button#integration").click()
    await page.wait_for_url(f"{instance.base}{INTEGRATION_PAGE}")
    await page.locator(PANEL).wait_for(state="detached")
    expect(await page.evaluate("window.__noReload === true"), "the page was loaded anew")


async def _until(check: Callable[[], Awaitable[bool]], what: str, seconds: float = 10) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if await check():
            return
        await asyncio.sleep(0.2)
    raise AssertionError(f"timed out waiting for {what}")


async def _close(page: Page) -> None:
    """Close the page's browser context; one that does not close is left to the browser."""
    try:
        async with asyncio.timeout(CLOSE_SECONDS):
            await page.context.close()
    except TimeoutError:
        print(f"note: a browser context did not close within {CLOSE_SECONDS} s")


async def _fab_hidden(page: Page) -> bool:
    return bool(await page.locator(f"{PANEL} ha-button#save").is_hidden())


async def _settle(page: Page) -> None:
    """Let animations end and the pointer leave before a picture."""
    await page.mouse.move(0, 0)
    await page.wait_for_timeout(500)


async def check_page(
    browser: Browser, instance: Instance, api: Api, shots: Path | None, checks: Checks
) -> None:
    """Run the checks into `checks`, so the ones done count also when time runs out."""
    page = await _open(browser, instance, ADMIN)

    async def from_list() -> None:
        """Every check starts on the list of guests, whatever the one before left behind."""
        await _goto(page, instance, "guests/list")

    checks.before = from_list

    async def list_shows_guests() -> None:
        headlines = await _headlines(page)
        expect(len(headlines) == 5, f"5 guests expected, got {headlines}")
        expect(headlines[0].startswith("Anna · Counts as home"), headlines[0])
        expect(any(line.startswith("Chris · No approval") for line in headlines), str(headlines))
        expect(
            await page.locator(f"{PANEL} [data-act='lock'][data-key='g_chris']").count() == 0,
            "locked guest has a lock button",
        )
        # The room lock in one line, its why behind the (i)
        alert = page.locator(f"{PANEL} ha-alert", has_text="Room lock")
        expect(await alert.count() == 1, "the room lock line is missing")
        expect(await alert.locator("ha-icon-button.help").count() == 1, "the lock line has no (i)")
        clean = page.locator(f"{PANEL} .item[data-key='g_clean'] .supporting").first
        text = await clean.inner_text()
        expect(text.endswith(" (outside the time windows)"), text)
        if shots is not None:
            await _settle(page)
            await page.screenshot(path=str(shots / "guests.png"))

    await checks.run(
        "the guests with their state, the room lock in one line, windows not expiry",
        list_shows_guests,
    )

    async def header_on_every_page() -> None:
        for path, tab in PAGES.items():
            await _goto(page, instance, path)
            try:
                await _header(page)
                await _frame(page, sub=False, page_id=tab)
            except AssertionError as err:
                raise AssertionError(f"{path}: {err}") from err
        for path in ("guests/list?key=g_anna", "guests/list?key=new"):
            await _goto(page, instance, path)
            try:
                await _header(page)
                await _frame(page, sub=True)
            except AssertionError as err:
                raise AssertionError(f"{path}: {err}") from err

    await checks.run(
        "every page: the two areas as Home Assistant's tabs, its own tab, stamp, refresh, "
        "integration; a guest with back arrow, name and views",
        header_on_every_page,
    )

    async def setup_overview() -> None:
        await _goto(page, instance, "setup/overview")
        steps = page.locator(f"{PANEL} .item[data-act='go']")
        expect(await steps.count() == 3, f"{await steps.count()} steps")
        done = await page.locator(f"{PANEL} .lead.step.done").count()
        expect(done == 3, f"{done} steps done in the made-up home")
        labels = await page.locator(f"{PANEL} .lead.step").evaluate_all(
            "els => els.map(e => e.getAttribute('aria-label'))"
        )
        expect(labels == ["done"] * 3, f"the state of the steps without text: {labels}")
        about = (await page.locator(f"{PANEL} .about").inner_text()).strip()
        expect(about.startswith(f"Guest Access {VERSION}") and "commit" in about, about)
        await _goto(page, instance, "guests/list")
        expect(await page.locator(f"{PANEL} .about").count() == 0, "the version on the list")
        await _goto(page, instance, "setup/overview")
        await steps.nth(1).focus()
        await page.keyboard.press("Enter")
        await page.wait_for_url("**/guest-access/setup/rooms")
        if shots is not None:
            await _ready(page)
            await _settle(page)
            await page.screenshot(path=str(shots / "rooms.png"))

    await checks.run("the setup overview: three steps, the version line", setup_overview)

    async def old_addresses() -> None:
        # Bookmarks and links of before: to the page that took the place
        for old, new in (
            ("rooms", "/guest-access/setup/rooms"),
            ("guests", "/guest-access/guests/list"),
            ("", "/guest-access/guests/list"),
            ("setup", "/guest-access/setup/overview"),
        ):
            await page.goto(f"{instance.base}/guest-access/{old}")
            await page.wait_for_url(f"**{new}")
        # A change of the query alone opens the guest it names
        await _goto(page, instance, "guests/list")
        await page.evaluate(
            """() => {
              history.pushState(null, '', '/guest-access/guests/list?key=g_ben');
              window.dispatchEvent(new CustomEvent('location-changed', { detail: { replace: false } }));
            }"""
        )
        await _until(
            lambda: page.locator(f"{PANEL} .subname").filter(has_text="Ben").count(),
            "Ben's page after a change of the query alone",
        )
        await page.go_back()
        await page.locator(ROW).first.wait_for()

    await checks.run(
        "old addresses and a change of the query alone lead to the right page", old_addresses
    )

    async def views_in_the_url() -> None:
        await page.locator(f"{PANEL} .item[data-key='g_anna']").click()
        await page.wait_for_url("**/guest-access/guests/list?key=g_anna")
        await _frame(page, sub=True)
        expect((await page.locator(f"{PANEL} .subname").inner_text()).strip() == "Anna", "name")
        await page.locator(f"{PANEL} #views ha-tab-group-tab[panel='approval']").click()
        await page.wait_for_url("**/guest-access/guests/list?key=g_anna&view=approval")
        await page.locator(f"{PANEL} ha-settings-row.num", has_text="Grace time").wait_for()
        await page.reload()
        await _ready(page)
        active = await page.locator(f"{PANEL} #views ha-tab-group-tab[active]").get_attribute(
            "panel"
        )
        expect(active == "approval", f"the reload left the view: {active}")
        # The back arrow returns to the list
        await page.locator(PANEL).evaluate(
            "el => el.shadowRoot.getElementById('frame').shadowRoot"
            ".querySelector('ha-icon-button-arrow-prev').click()"
        )
        await page.wait_for_url("**/guest-access/guests/list")
        await page.locator(ROW).first.wait_for()

    await checks.run("a guest's views in the address, the back arrow to the list", views_in_the_url)

    async def header_on_list() -> None:
        await _refresh(page)
        await _header(page)
        # A refresh on a guest keeps what was typed
        await _goto(page, instance, "guests/list?key=g_ben")
        name = page.get_by_role("textbox", name="Name")
        await name.fill("Ben typed")
        await _refresh(page)
        expect(await name.input_value() == "Ben typed", "the refresh dropped the typed name")
        await _goto(page, instance, "setup/timings")
        await _integration_button(page, instance)

    await checks.run(
        "Refresh fetches the data again, spins, sets the stamp; the integration button",
        header_on_list,
    )

    async def edit_shows_windows() -> None:
        await _goto(page, instance, "guests/list?key=g_clean")
        await page.get_by_text("Cleaning service key tag").first.wait_for()
        await _goto(page, instance, "guests/list?key=g_clean&view=approval")
        await page.locator(f"{PANEL} .card-header", has_text="Time windows").wait_for()
        weekday = (datetime.now(TIME_ZONE) + timedelta(days=2)).strftime("%A")
        await page.get_by_text(weekday, exact=True).first.wait_for()
        if shots is not None:
            await page.set_viewport_size({"width": 1000, "height": 1000})
            await _settle(page)
            await page.screenshot(path=str(shots / "guest.png"))
            await page.set_viewport_size({"width": 1000, "height": 760})

    await checks.run("a guest's approval with its time windows", edit_shows_windows)

    async def visit_log() -> None:
        await _goto(page, instance, "guests/list?key=g_anna&view=log")
        await page.get_by_text("Visit running since", exact=False).first.wait_for()
        text = await page.locator(f"{PANEL} #sheet").inner_text()
        expect("Last month:" in text and "visits" in text, "monthly total missing")
        expect(" 1 visits" not in text, "plural for one visit")
        if shots is not None:
            await _settle(page)
            await page.locator(f"{PANEL} #sheet").screenshot(path=str(shots / "visit-log.png"))
        async with page.expect_download() as download:
            await page.get_by_role("button", name="Export as CSV").click()
        path = await (await download.value).path()
        csv = await asyncio.to_thread(Path(path).read_text, encoding="utf-8-sig")
        expect(csv.count("\n") > 10, "CSV has too few rows")

    await checks.run("visit log with totals and CSV export", visit_log)

    async def settings_saved() -> None:
        await _goto(page, instance, "setup/timings")
        rows = page.locator(f"{PANEL} ha-settings-row")
        helps = page.locator(f"{PANEL} ha-settings-row ha-icon-button.help")
        expect(await rows.count() == await helps.count() == 4, "a settings row without its (i)")
        expect(await _fab_hidden(page), "a save button with nothing changed")
        resume = page.get_by_role("textbox", name="Time to be seen again after a restart")
        await resume.wait_for()
        expect(await resume.input_value() == "10", await resume.input_value())
        # The (i) beside a setting: a tap shows its explanation in Home Assistant's tooltip
        row = rows.filter(has_text="Keep single visits")
        await row.locator("ha-icon-button.help").click()
        tip = row.locator("ha-tooltip")
        await _until(lambda: tip.evaluate("el => el.open === true"), "the explanation")
        expect("3650" in await tip.evaluate("el => el.textContent"), "wrong explanation")
        await resume.fill("12")
        await page.locator(f"{PANEL} ha-button#save:not([hidden])").wait_for()
        await resume.fill("10")
        await _until(lambda: _fab_hidden(page), "the save button to go with the old value")
        await resume.fill("12")
        if shots is not None:
            await _settle(page)
            await page.screenshot(path=str(shots / "settings.png"))
        await page.locator(f"{PANEL} ha-button#save:not([hidden])").click()

        async def saved() -> bool:
            return bool((await _snapshot(api, instance))["settings"]["resume_minutes"] == 12)

        await _until(saved, "the new resume time in the integration")
        await _until(lambda: _fab_hidden(page), "the save button to go after saving")
        # Every guest's setting is a row with its (i) as well
        for view in ("details", "approval", "rooms", "log"):
            await _goto(page, instance, f"guests/list?key=g_anna&view={view}")
            rows = page.locator(f"{PANEL} ha-settings-row")
            count = await rows.count()
            expect(count > 0, f"{view}: no settings rows")
            expect(
                await page.locator(f"{PANEL} ha-settings-row ha-icon-button.help").count() == count,
                f"{view}: a row without its (i)",
            )

    await checks.run(
        "settings: rows with their (i), one save button while changed, reaches the integration",
        settings_saved,
    )

    async def rename_guest() -> None:
        await _goto(page, instance, "guests/list?key=g_ben")
        expect(await _fab_hidden(page), "a save button on a guest not changed")
        name = page.get_by_role("textbox", name="Name")
        await name.fill("Ben Example")
        await page.locator(f"{PANEL} ha-button#save:not([hidden])").click()

        async def renamed() -> bool:
            guest = _guest(await _snapshot(api, instance), "g_ben")
            # The photo, not touched here, stays
            return guest is not None and guest["name"] == "Ben Example" and bool(guest["picture"])

        await _until(renamed, "the new name in the integration")
        await _until(lambda: _fab_hidden(page), "the save button to go after saving")
        await _goto(page, instance, "guests/list")
        expect(
            any(line.startswith("Ben Example ·") for line in await _headlines(page)),
            "list shows the old name",
        )

    await checks.run("renaming a guest reaches the integration", rename_guest)

    async def lock_guest() -> None:
        await page.locator(f"{PANEL} [data-act='lock'][data-key='g_grandma']").click()
        await page.locator(f"{PANEL} ha-alert", has_text="Lock Grandma?").wait_for()
        await page.locator(f"{PANEL} #confirm-ok").click()

        async def locked() -> bool:
            guest = _guest(await _snapshot(api, instance), "g_grandma")
            return guest is not None and guest["approval"]["kind"] == "off"

        await _until(locked, "the lock in the integration")
        await page.locator(f"{PANEL} [data-act='lock'][data-key='g_grandma']").wait_for(
            state="detached"
        )

    await checks.run("locking a guest after confirming", lock_guest)

    async def keyboard_on_lock_button() -> None:
        button = page.locator(f"{PANEL} [data-act='lock'][data-key='g_anna']")
        await button.focus()
        await page.keyboard.press("Enter")
        await page.locator(f"{PANEL} ha-alert", has_text="Lock Anna?").wait_for()
        expect("?key=" not in page.url, "Enter opened the guest")
        await page.locator(f"{PANEL} #confirm-cancel").click()
        guest = _guest(await _snapshot(api, instance), "g_anna")
        expect(
            guest is not None and guest["approval"]["kind"] == "permanent",
            "cancel locked the guest",
        )
        # A row opens its guest with Enter, as a button would
        await page.locator(f"{PANEL} .item[data-key='g_chris']").focus()
        await page.keyboard.press("Enter")
        await page.wait_for_url("**/guest-access/guests/list?key=g_chris")

    await checks.run(
        "Enter on the lock button asks, Cancel keeps the guest; Enter on a row opens it",
        keyboard_on_lock_button,
    )

    async def delete_log() -> None:
        await _goto(page, instance, "guests/list?key=g_clean&view=log")
        await page.get_by_role("button", name="Delete log").click()
        await page.locator(f"{PANEL} #confirm-ok").click()

        async def emptied() -> bool:
            guest = _guest(await _snapshot(api, instance), "g_clean")
            return guest is not None and not guest["log"]["visits"] and not guest["log"]["months"]

        await _until(emptied, "an empty visit log")

    await checks.run("deleting a visit log after confirming", delete_log)

    async def images() -> set[str]:
        listed = await api.ws(instance.token, {"type": "image/list"})
        return {item["id"] for item in listed["result"]}

    async def errors_read_alike() -> None:
        # A guest without trackers: one line by its kind, Home Assistant's message behind the (i)
        before = len((await _snapshot(api, instance))["guests"])
        await page.get_by_role("button", name="Add guest").click()
        await page.wait_for_url("**/guest-access/guests/list?key=new")
        expect(await _fab_hidden(page), "a save button on an empty new guest")
        await page.get_by_role("textbox", name="Name").fill("Nobody")
        await page.locator(f"{PANEL} ha-button#save:not([hidden])").click()
        alert = page.locator(
            f"{PANEL} ha-alert[alert-type='error']", has_text="The input does not fit."
        )
        await alert.wait_for()
        said = await alert.locator("ha-tooltip").evaluate("el => el.textContent")
        expect(said.strip().startswith("Message: "), said)
        expect(
            len((await _snapshot(api, instance))["guests"]) == before, "an empty guest was saved"
        )
        # The photo upload is HTTP: its answer reads the same
        files = await images()
        await page.locator(f"{PANEL} input[type=file]").set_input_files(
            {"name": "x.png", "mimeType": "image/png", "buffer": b"not an image"}
        )

        async def told() -> bool:
            said = await alert.locator("ha-tooltip").evaluate("el => el.textContent")
            return "image" in said.lower()

        await _until(told, "the upload's error behind the (i)")
        expect(await images() == files, "a broken photo was kept")

    await checks.run(
        "an error reads one line by its kind, the message behind its (i)", errors_read_alike
    )

    async def photo_and_note() -> None:
        before = await images()
        await _goto(page, instance, "guests/list?key=g_clean")
        await page.locator(f"{PANEL} input[type=file]").set_input_files(
            {"name": "c.png", "mimeType": "image/png", "buffer": _avatar("C", (163, 190, 140))}
        )
        await page.locator(f"{PANEL} .media img.avatar").wait_for()
        await page.get_by_role("textbox", name="Note").fill("Key is in the mailbox")
        await page.locator(f"{PANEL} ha-button#save:not([hidden])").click()

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
        await _goto(page, instance, "guests/list")
        await page.locator(f"{PANEL} .item[data-key='g_clean'] img.lead").wait_for()
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

    async def left_upload_leaves_nothing() -> None:
        before = await images()
        await _goto(page, instance, "guests/list?key=g_grandma")
        await page.locator(f"{PANEL} input[type=file]").set_input_files(
            {"name": "g.png", "mimeType": "image/png", "buffer": _avatar("G", (180, 142, 173))}
        )
        await page.locator(f"{PANEL} .media img.avatar").wait_for()
        expect(len(await images()) == len(before) + 1, "the upload did not arrive")
        await page.locator(PANEL).evaluate(
            "el => el.shadowRoot.getElementById('frame').shadowRoot"
            ".querySelector('ha-icon-button-arrow-prev').click()"
        )
        await page.locator(ROW).first.wait_for()

        async def cleaned() -> bool:
            return await images() == before

        await _until(cleaned, "the upload not saved to be deleted")

    await checks.run(
        "a photo uploaded and the guest left without saving is deleted again",
        left_upload_leaves_nothing,
    )

    async def numbers_in_the_language() -> None:
        # A German page writes numbers as elsewhere in German, and takes a comma back
        anna = _guest(await _snapshot(api, instance), "g_anna")
        assert anna is not None
        odd = next((v for v in anna["log"]["visits"][:10] if v["minutes"] % 60), None)
        await page.evaluate("localStorage.setItem('selectedLanguage', JSON.stringify('de'))")
        try:
            await _goto(page, instance, "guests/list?key=g_anna&view=log")
            await page.get_by_text("Besuch läuft seit", exact=False).first.wait_for()
            if odd is not None:
                hours = f"{odd['minutes'] / 60:.2f}".rstrip("0").rstrip(".").replace(".", ",")
                text = await page.locator(f"{PANEL} .visits").inner_text()
                expect(f"{hours} h" in text, f"{hours} h not in {text!r}")
            await _goto(page, instance, "setup/timings")
            grid = page.get_by_role("textbox", name="Raster des Besuchsprotokolls")
            await grid.wait_for()
            expect(await grid.input_value() == "15", await grid.input_value())
            await grid.fill("20,0")
            await page.locator(f"{PANEL} ha-button#save:not([hidden])").click()

            async def saved() -> bool:
                return bool((await _snapshot(api, instance))["settings"]["log_grid_minutes"] == 20)

            await _until(saved, "20,0 saved as 20")
        finally:
            await page.evaluate("localStorage.setItem('selectedLanguage', JSON.stringify('en'))")

    await checks.run(
        "German: numbers in the number format, a comma typed into a field", numbers_in_the_language
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
            await _goto(phone, instance, "guests/list")
            info = await _frame(phone, sub=False)
            expect(info["bottom"], f"{scheme}: the areas are not at the bottom")
            overflow = await phone.evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            expect(overflow <= 0, f"{scheme}: page scrolls sideways by {overflow} px")
            expect(
                not await phone.locator(f"{PANEL} #stamp").is_visible(),
                f"{scheme}: the stamp shows on phone width",
            )
            for button in ("refresh", "integration"):
                expect(
                    await phone.locator(f"{PANEL} ha-icon-button#{button}").is_visible(),
                    f"{scheme}: {button} button missing on phone width",
                )
            if shots is not None and scheme == "dark":
                await _settle(phone)
                await phone.screenshot(path=str(shots / "phone-dark.png"))
            for path in ("guests/list?key=g_anna", "setup/timings"):
                await _goto(phone, instance, path)
                overflow = await phone.evaluate(
                    "() => document.documentElement.scrollWidth"
                    " - document.documentElement.clientWidth"
                )
                expect(overflow <= 0, f"{scheme} {path}: scrolls sideways by {overflow} px")
            background = await phone.locator(PANEL).evaluate(
                "el => getComputedStyle(el).backgroundColor"
            )
            if scheme == "dark":
                channels = [
                    int(part) for part in background[background.index("(") + 1 : -1].split(",")[:3]
                ]
                expect(sum(channels) < 200, f"dark mode background is {background}")
            SENT.pop(phone, None)
            await _close(phone)

    await checks.run(
        "phone width and dark mode: areas at the bottom, no sideways scrolling", phone_and_dark
    )

    async def safe_area() -> None:
        phone = await _open(
            browser,
            instance,
            ADMIN,
            viewport={"width": 390, "height": 844},
            color_scheme="dark",
        )
        try:
            found: dict[str, dict[str, Any]] = {}
            for name, path in (
                ("Guest Access", "/guest-access/guests/list"),
                ("Automations", "/config/automation/dashboard"),
            ):
                await phone.goto(instance.base + path)
                await phone.locator("hass-tabs-subpage").first.wait_for(timeout=90000)
                await phone.locator("#ha-launch-screen").wait_for(state="detached")
                await phone.wait_for_load_state("networkidle")
                # An iPhone's safe area, set as Home Assistant's own debug setting sets it
                await phone.evaluate(
                    """() => {
                      const style = document.createElement('style');
                      style.textContent = ':root{--app-safe-area-inset-top:47px !important;'
                        + '--app-safe-area-inset-bottom:34px !important;}';
                      document.head.append(style);
                    }"""
                )
                await phone.wait_for_timeout(800)
                info: dict[str, Any] = await phone.evaluate(SAFE_AREA_MEASURE)
                height = info["viewport"]
                expect(
                    info["frame"] == [0, height],
                    f"{name}: frame at {info['frame']} instead of [0, {height}]",
                )
                expect(info["toolbar"] == 56 + 47, f"{name}: header {info['toolbar']} px high")
                tabbar = info["tabbar"]
                expect(
                    tabbar is not None and tabbar[1] == height and tabbar[0] >= 0,
                    f"{name}: tab bar at {tabbar}, viewport {height}",
                )
                found[name] = info
            expect(
                found["Guest Access"] == found["Automations"],
                f"Guest Access and Automations differ: {found}",
            )
        finally:
            SENT.pop(phone, None)
            await _close(phone)

    await checks.run(
        "phone with a safe area: header and bottom areas fit as on Home Assistant's own pages",
        safe_area,
    )

    async def recovers_once_loaded() -> None:
        async def entry(disabled_by: str | None) -> None:
            reply = await api.ws(
                instance.token,
                {
                    "type": "config_entries/disable",
                    "entry_id": instance.entry_id,
                    "disabled_by": disabled_by,
                },
            )
            expect(reply["success"], str(reply))

        await entry("user")
        try:
            await page.goto(f"{instance.base}/guest-access/guests/list")
            alert = page.locator(
                f"{PANEL} ha-alert[alert-type='error']", has_text="Guest Access is not set up."
            )
            await alert.wait_for(timeout=30000)
            said = await alert.locator("ha-tooltip").evaluate("el => el.textContent")
            expect(said.strip().startswith("Message: "), said)
        finally:
            await entry(None)
        # The page subscribes again by itself, without a reload
        await page.locator(ROW).first.wait_for(timeout=30000)
        expect(
            await page.locator(f"{PANEL} ha-alert[alert-type='error']").count() == 0,
            "the error stays after loading",
        )

    await checks.run(
        "the page recovers by itself once the integration is loaded again", recovers_once_loaded
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

    async def starts_at_setup() -> None:
        # Last, as it empties the made-up home: with nothing set up the page starts at the setup
        for guest in (await _snapshot(api, instance))["guests"]:
            reply = await api.ws(
                instance.token, {"type": "guest_access/delete_guest", "guest_id": guest["id"]}
            )
            expect(reply["success"], str(reply))
        reply = await api.ws(
            instance.token, {"type": "guest_access/save_settings", "residents": [], "rooms": []}
        )
        expect(reply["success"], str(reply))
        await page.goto(f"{instance.base}/guest-access")
        await page.wait_for_url("**/guest-access/setup/overview")
        await _ready(page)
        expect(await page.locator(f"{PANEL} .lead.step.done").count() == 0, "a step done")
        await page.locator(f"{PANEL} ha-button#next").click()
        await page.wait_for_url("**/guest-access/setup/residents")

    checks.before = None
    await checks.run(
        "with nothing set up the page starts at the setup overview, Continue leads on",
        starts_at_setup,
    )
    await _close(page)


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
                    async with asyncio.timeout(ALL_SECONDS):
                        await check_page(browser, instance, api, args.screenshots, checks)
                except TimeoutError:
                    checks.failed.append(f"all checks: no end after {ALL_SECONDS} s")
                    print(f"FAIL all checks: no end after {ALL_SECONDS} s")
                finally:
                    try:
                        async with asyncio.timeout(CLOSE_SECONDS):
                            await browser.close()
                    except TimeoutError:
                        print(f"note: the browser did not close within {CLOSE_SECONDS} s")
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
