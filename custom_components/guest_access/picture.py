"""The upload of a guest's photo: into Home Assistant's images, noted as the integration's own.

Only photos uploaded here can become a guest's photo, and only these are ever
deleted by the integration; an image of a person or an area stays untouched.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from aiohttp import web
import probatio

from homeassistant.components.http import KEY_HASS, KEY_HASS_USER, HomeAssistantView
from homeassistant.components.image_upload import DOMAIN as IMAGE_UPLOAD_DOMAIN, MAX_SIZE
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN

PICTURE_URL = f"/api/{DOMAIN}/picture"
DATA_VIEW: HassKey[bool] = HassKey(f"{DOMAIN}_picture_view")


class GuestPictureView(HomeAssistantView):
    """Upload a guest's photo; administrators only."""

    url = PICTURE_URL
    name = f"api:{DOMAIN}:picture"

    async def post(self, request: web.Request) -> web.Response:
        """Store the image and answer with its ID."""
        hass: HomeAssistant = request.app[KEY_HASS]
        if not request[KEY_HASS_USER].is_admin:
            return self.json_message("Only administrators", HTTPStatus.UNAUTHORIZED)
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            return self.json_message("Guest Access is not set up", HTTPStatus.NOT_FOUND)
        # As Home Assistant's own image upload allows
        request._client_max_size = MAX_SIZE
        data = await request.post()
        try:
            item: dict[str, Any] = await hass.data[IMAGE_UPLOAD_DOMAIN].async_create_item(
                dict(data)
            )
        except probatio.Invalid as err:
            return self.json_message(str(err), HTTPStatus.BAD_REQUEST)
        entries[0].runtime_data.async_add_picture(item["id"])
        return self.json({"id": item["id"]})


@callback
def async_register_picture_view(hass: HomeAssistant) -> None:
    """Register the upload once per run."""
    if DATA_VIEW in hass.data:
        return
    hass.data[DATA_VIEW] = True
    hass.http.register_view(GuestPictureView())
