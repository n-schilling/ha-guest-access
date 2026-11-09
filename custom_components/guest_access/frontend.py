"""Serves the page and adds it to the sidebar of administrators."""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components import panel_custom
from homeassistant.components.frontend import async_panel_exists, async_remove_panel
from homeassistant.components.http.server import StaticPathConfig
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from .const import (
    DOMAIN,
    FRONTEND_URL_BASE,
    PANEL_ELEMENT,
    PANEL_FILENAME,
    PANEL_ICON,
    PANEL_URL_PATH,
    TITLE,
)

DATA_STATIC: HassKey[bool] = HassKey(f"{DOMAIN}_static")


async def async_register_panel(hass: HomeAssistant) -> None:
    """Serve the page once per run and add it to the sidebar of administrators.

    It stays through a reload of the entry, so an open page is not thrown out.
    """
    if DATA_STATIC not in hass.data:
        hass.data[DATA_STATIC] = True
        await hass.http.async_register_static_paths(
            [StaticPathConfig(FRONTEND_URL_BASE, str(Path(__file__).parent / "frontend"), False)]
        )
    if async_panel_exists(hass, PANEL_URL_PATH):
        return
    script = Path(__file__).parent / "frontend" / PANEL_FILENAME
    digest = await hass.async_add_executor_job(_digest, script)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_ELEMENT,
        sidebar_title=TITLE,
        sidebar_icon=PANEL_ICON,
        # The content hash makes browsers fetch every changed page, also within a version
        module_url=f"{FRONTEND_URL_BASE}/{PANEL_FILENAME}?v={digest}",
        require_admin=True,
    )


def _digest(path: Path) -> str:
    """A short hash of the page's script."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    """Take the page off the sidebar."""
    async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
