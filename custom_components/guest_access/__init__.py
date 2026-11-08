"""Guest Access: guest profiles, approvals, rooms and visit time for an alarm system.

Scaffold: the entry loads and unloads; profiles, the state machine, the
entities and the page follow (see README, section Design).
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Guest Access from its config entry."""
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the config entry."""
    return True
