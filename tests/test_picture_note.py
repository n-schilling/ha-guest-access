"""A guest's photo, an image uploaded to Home Assistant, and a note for administrators."""

from __future__ import annotations

import io
from typing import Any

import aiohttp
from PIL import Image
import pytest
from pytest_homeassistant.common import MockConfigEntry
from pytest_homeassistant.typing import ClientSessionGenerator, WebSocketGenerator

from homeassistant.components.image_upload import DOMAIN as IMAGE_UPLOAD_DOMAIN
from homeassistant.core import HomeAssistant

from custom_components.guest_access.engine import GuestEngine

COUNTS = "binary_sensor.guest_anna_counts"
STATUS = "sensor.guest_anna_status"
VISIT_ENDS = "sensor.guest_anna_visit_ends"
GUESTS_HOME = "binary_sensor.guest_access_guests_home"


@pytest.fixture
def hass_config_dir(hass_tmp_config_dir: str) -> str:
    """Uploaded images go to a directory of their own, not into the repository."""
    return hass_tmp_config_dir


async def _upload(hass_client: ClientSessionGenerator) -> str:
    """Upload a small PNG the way the page does; the image's ID."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 50, 50)).save(buffer, format="PNG")
    buffer.seek(0)
    form = aiohttp.FormData()
    form.add_field("file", buffer, filename="anna.png", content_type="image/png")
    client = await hass_client()
    response = await client.post("/api/image/upload", data=form)
    assert response.status == 200, await response.text()
    image_id: str = (await response.json())["id"]
    return image_id


def _images(hass: HomeAssistant) -> set[str]:
    return set(hass.data[IMAGE_UPLOAD_DOMAIN].data)


async def _save(
    hass_ws_client: WebSocketGenerator, hass: HomeAssistant, **changes: Any
) -> dict[str, Any]:
    """Save Anna through the page's command, with these changes."""
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "guest_access/save_guest",
            "guest_id": "anna",
            "name": "Anna",
            "trackers": ["device_tracker.anna_phone"],
            "approval": {"kind": "permanent", "windows": []},
            **changes,
        }
    )
    reply: dict[str, Any] = await client.receive_json()
    await hass.async_block_till_done()
    return reply


def _attribute(hass: HomeAssistant, entity_id: str, name: str) -> Any:
    current = hass.states.get(entity_id)
    assert current is not None
    return current.attributes.get(name)


async def test_photo_on_entities_and_guest_list(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Counts and status show the photo, as does the guest list; other entities do not."""
    image_id = await _upload(hass_client)
    assert (await _save(hass_ws_client, hass, picture=image_id))["success"]

    url = f"/api/image/serve/{image_id}/512x512"
    assert _attribute(hass, COUNTS, "entity_picture") == url
    assert _attribute(hass, STATUS, "entity_picture") == url
    assert _attribute(hass, VISIT_ENDS, "entity_picture") is None
    assert _attribute(hass, GUESTS_HOME, "guest_list")[0]["picture"] == url
    # Home Assistant serves the picture in that size
    response = await (await hass_client()).get(url)
    assert response.status == 200


async def test_photo_replaced_and_removed(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A photo nobody uses any more goes; leaving the photo out keeps it."""
    engine: GuestEngine = entry.runtime_data
    first = await _upload(hass_client)
    second = await _upload(hass_client)
    assert (await _save(hass_ws_client, hass, picture=first))["success"]

    # Without the field, a change keeps photo and note
    assert (await _save(hass_ws_client, hass, note="Brings the dog"))["success"]
    assert (await _save(hass_ws_client, hass))["success"]
    assert engine.data.guests["anna"].picture == first
    assert engine.data.guests["anna"].note == "Brings the dog"

    assert (await _save(hass_ws_client, hass, picture=second))["success"]
    assert _images(hass) == {second}

    assert (await _save(hass_ws_client, hass, picture=None))["success"]
    assert _images(hass) == set()
    assert _attribute(hass, COUNTS, "entity_picture") is None


async def test_photo_goes_with_the_guest(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Deleting a guest deletes the photo."""
    image_id = await _upload(hass_client)
    assert (await _save(hass_ws_client, hass, picture=image_id))["success"]
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "guest_access/delete_guest", "guest_id": "anna"})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    assert _images(hass) == set()


async def test_only_uploaded_images(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """A photo is an uploaded image, never an address or an unknown ID."""
    for picture in ("https://example.com/anna.jpg", "0123456789abcdef0123456789abcdef"):
        reply = await _save(hass_ws_client, hass, picture=picture)
        assert not reply["success"]
        assert reply["error"]["code"] == "invalid_format"


async def test_note_stays_on_the_page(
    hass: HomeAssistant, entry: MockConfigEntry, hass_ws_client: WebSocketGenerator
) -> None:
    """The note is in the page's data, in no entity; it has a limit."""
    assert (await _save(hass_ws_client, hass, note="  Allergic to cats  "))["success"]
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "guest_access/subscribe"})
    assert (await client.receive_json())["success"]
    page = (await client.receive_json())["event"]
    assert page["guests"][0]["note"] == "Allergic to cats"
    for state in hass.states.async_all():
        assert "Allergic" not in str(state.attributes)

    reply = await _save(hass_ws_client, hass, note="x" * 2001)
    assert not reply["success"]
