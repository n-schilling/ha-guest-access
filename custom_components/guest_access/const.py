"""Constants of Guest Access."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "guest_access"
TITLE: Final = "Guest Access"

STORAGE_KEY: Final = DOMAIN
STORAGE_VERSION: Final = 1

# How long all trackers of a once guest may be away before the approval ends
DEFAULT_GRACE_MINUTES: Final = 15
MAX_GRACE_MINUTES: Final = 240
# Time per visit, None is unlimited
VISIT_CHOICES: Final = (30, 60, 120, None)
DEFAULT_VISIT_MINUTES: Final = 60
# After a restart a guest who counted before keeps the visit when a tracker
# reports home within this time; otherwise the guest has left
RESUME_WINDOW: Final = timedelta(minutes=10)

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
WS_LOCK_GUEST: Final = f"{DOMAIN}/lock_guest"
WS_SAVE_SETTINGS: Final = f"{DOMAIN}/save_settings"
# Sent after every change, for the page
SIGNAL_CHANGED: Final = f"{DOMAIN}_changed"
