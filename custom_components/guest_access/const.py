"""Constants of Guest Access."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "guest_access"
TITLE: Final = "Guest Access"

STORAGE_KEY: Final = DOMAIN
STORAGE_VERSION: Final = 1

# Defaults and limits; the values themselves are settings of the entry or of a guest
# A return within the grace time continues the visit
DEFAULT_GRACE_MINUTES: Final = 15
MAX_GRACE_MINUTES: Final = 240
# Time per visit, None is unlimited
DEFAULT_VISIT_MINUTES: Final = 60
MAX_VISIT_MINUTES: Final = 24 * 60
# After a restart a guest who counted before keeps the visit when a tracker
# reports home within this time; otherwise the guest has left
DEFAULT_RESUME_MINUTES: Final = 10
MAX_RESUME_MINUTES: Final = 60
# Visit log: grid, how long single visits and monthly totals are kept
DEFAULT_LOG_GRID_MINUTES: Final = 15
MAX_LOG_GRID_MINUTES: Final = 60
DEFAULT_LOG_KEEP_DAYS: Final = 90
MAX_LOG_KEEP_DAYS: Final = 3650
DEFAULT_LOG_KEEP_MONTHS: Final = 13
MAX_LOG_KEEP_MONTHS: Final = 120
# A guest's name: shown on the page, as device name and in attributes
MAX_NAME_LENGTH: Final = 100
# A guest's note, for administrators on the page only
MAX_NOTE_LENGTH: Final = 2000
# A guest's photo is an image uploaded to Home Assistant, served in this size
PICTURE_SIZE: Final = "512x512"
# A photo uploaded on the page but not saved with a guest is deleted after this
# time; long enough for a form left open, checked every PICTURE_CHECK_INTERVAL
PICTURE_UNUSED_KEEP: Final = timedelta(hours=24)
PICTURE_CHECK_INTERVAL: Final = timedelta(hours=1)
# A photo is stored at most this wide and high
PICTURE_MAX_EDGE: Final = 1024
# Larger images are refused before they are decoded; any phone photo is smaller
PICTURE_MAX_PIXELS: Final = 40_000_000
# Written by scripts/deploy.sh: the commit the deployed files come from
BUILD_FILE: Final = "BUILD"

# Event types of a guest's event entity
EVENT_ARRIVED: Final = "arrived"
EVENT_LEFT: Final = "left"
EVENT_TIME_UP: Final = "time_up"
EVENT_APPROVAL_EXPIRED: Final = "approval_expired"
EVENT_APPROVAL_CHANGED: Final = "approval_changed"
GUEST_EVENT_TYPES: Final = [
    EVENT_ARRIVED,
    EVENT_LEFT,
    EVENT_TIME_UP,
    EVENT_APPROVAL_EXPIRED,
    EVENT_APPROVAL_CHANGED,
]
# Event type of the room violation entity
EVENT_OPENED: Final = "opened"

# The page in the sidebar, for administrators
FRONTEND_URL_BASE: Final = "/guest_access_static"
PANEL_FILENAME: Final = "guest-access-panel.js"
PANEL_URL_PATH: Final = "guest-access"
PANEL_ELEMENT: Final = "guest-access-panel"
PANEL_ICON: Final = "mdi:account-key"

# WebSocket commands
WS_SUBSCRIBE: Final = f"{DOMAIN}/subscribe"
WS_SAVE_GUEST: Final = f"{DOMAIN}/save_guest"
WS_DELETE_GUEST: Final = f"{DOMAIN}/delete_guest"
WS_DELETE_VISITS: Final = f"{DOMAIN}/delete_visits"
WS_LOCK_GUEST: Final = f"{DOMAIN}/lock_guest"
WS_SAVE_SETTINGS: Final = f"{DOMAIN}/save_settings"
# Sent after every change, for the page
SIGNAL_CHANGED: Final = f"{DOMAIN}_changed"
