"""The upload of a guest's photo: into Home Assistant's images, noted as the integration's own.

Only photos uploaded here can become a guest's photo, and only these are ever
deleted by the integration; an image of a person or an area stays untouched.

Home Assistant serves an uploaded image, the original included, without a
login and lists its file name to every user. So the photo is not stored as it
comes: it is encoded anew, which drops its metadata (where and when it was
taken, the device), made smaller and given a fixed file name.
"""

from __future__ import annotations

from http import HTTPStatus
import io
from typing import IO, Any

from aiohttp import web
from aiohttp.web_request import FileField
from multidict import CIMultiDict, CIMultiDictProxy
from PIL import Image, ImageOps, UnidentifiedImageError
import probatio

from homeassistant.components.http import KEY_HASS, KEY_HASS_USER, HomeAssistantView
from homeassistant.components.image_upload import DOMAIN as IMAGE_UPLOAD_DOMAIN, MAX_SIZE
from homeassistant.core import HomeAssistant, callback
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN, PICTURE_MAX_EDGE, PICTURE_MAX_PIXELS

PICTURE_URL = f"/api/{DOMAIN}/picture"
DATA_VIEW: HassKey[bool] = HassKey(f"{DOMAIN}_picture_view")
# What Home Assistant's images accept
CONTENT_TYPES = ("image/gif", "image/jpeg", "image/png")


def _clean(file: IO[bytes]) -> tuple[bytes, str]:
    """The picture encoded anew: upright, no metadata, at most PICTURE_MAX_EDGE wide and high.

    Read and decoded in the executor. The size is checked before decoding, so a
    small file that unpacks to a huge image is refused before it takes memory.
    """
    with Image.open(io.BytesIO(file.read())) as image:
        if image.width * image.height > PICTURE_MAX_PIXELS:
            raise ValueError("The image is too large")
        # A JPEG is scaled down while it is decoded
        image.draft("RGB", (PICTURE_MAX_EDGE, PICTURE_MAX_EDGE))
        image.load()
        upright = ImageOps.exif_transpose(image)
    transparent = upright.mode in ("RGBA", "LA", "PA") or "transparency" in upright.info
    picture = upright.convert("RGBA" if transparent else "RGB")
    picture.thumbnail((PICTURE_MAX_EDGE, PICTURE_MAX_EDGE))
    buffer = io.BytesIO()
    if transparent:
        picture.save(buffer, format="PNG")
        return buffer.getvalue(), "image/png"
    picture.save(buffer, format="JPEG", quality=88)
    return buffer.getvalue(), "image/jpeg"


class GuestPictureView(HomeAssistantView):
    """Upload a guest's photo; administrators only."""

    url = PICTURE_URL
    name = f"api:{DOMAIN}:picture"

    async def post(self, request: web.Request) -> web.Response:
        """Store the image, cleaned, and answer with its ID."""
        hass: HomeAssistant = request.app[KEY_HASS]
        if not request[KEY_HASS_USER].is_admin:
            return self.json_message("Only administrators", HTTPStatus.FORBIDDEN)
        if not hass.config_entries.async_loaded_entries(DOMAIN):
            return self.json_message("Guest Access is not set up", HTTPStatus.NOT_FOUND)
        # As Home Assistant's own image upload allows
        request._client_max_size = MAX_SIZE
        uploaded = (await request.post()).get("file")
        if not isinstance(uploaded, FileField) or uploaded.content_type not in CONTENT_TYPES:
            return self.json_message(
                "A photo is a JPEG, PNG or GIF image in the field file", HTTPStatus.BAD_REQUEST
            )
        try:
            content, content_type = await hass.async_add_executor_job(_clean, uploaded.file)
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            MemoryError,
            Image.DecompressionBombError,
        ):
            return self.json_message("Unable to read the image", HTTPStatus.BAD_REQUEST)
        images = hass.data[IMAGE_UPLOAD_DOMAIN]
        headers: CIMultiDictProxy[str] = CIMultiDictProxy(CIMultiDict())
        try:
            item: dict[str, Any] = await images.async_create_item(
                {"file": FileField("file", "guest", io.BytesIO(content), content_type, headers)}
            )
        except probatio.Invalid as err:
            return self.json_message(str(err), HTTPStatus.BAD_REQUEST)
        # The entry may have been unloaded or removed while the photo came in
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if not entries:
            await images.async_delete_item(item["id"])
            return self.json_message("Guest Access is not set up", HTTPStatus.NOT_FOUND)
        entries[0].runtime_data.async_add_picture(item["id"])
        return self.json({"id": item["id"]})


@callback
def async_register_picture_view(hass: HomeAssistant) -> None:
    """Register the upload once per run."""
    if DATA_VIEW in hass.data:
        return
    hass.data[DATA_VIEW] = True
    hass.http.register_view(GuestPictureView())
