"""Guest Access: which guests count as present, the rooms they may enter and their time."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION
from .engine import GuestEngine
from .frontend import async_register_panel, async_unregister_panel
from .issues import async_clear_issues
from .websocket import async_register_websocket

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.EVENT, Platform.SENSOR]

type GuestAccessConfigEntry = ConfigEntry[GuestEngine]


async def async_setup_entry(hass: HomeAssistant, entry: GuestAccessConfigEntry) -> bool:
    """Load the guests, start watching, add the entities and the page."""
    engine = GuestEngine(hass, entry)
    await engine.async_start()
    entry.runtime_data = engine
    async_register_websocket(hass)
    await async_register_panel(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    engine.async_begin()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GuestAccessConfigEntry) -> bool:
    """Unload the entities and save the state; the page stays until the entry is removed."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_stop()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: GuestAccessConfigEntry) -> None:
    """Remove the page and the stored guests with the entry."""
    async_unregister_panel(hass)
    async_clear_issues(hass)
    store: Store[dict[str, object]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    await store.async_remove()
