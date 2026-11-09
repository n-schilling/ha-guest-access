"""A guest's photo, uploaded through Guest Access, and a note for administrators."""

from __future__ import annotations

from datetime import timedelta
import io
from typing import Any

import aiohttp
from freezegun.api import FrozenDateTimeFactory
from PIL import Image
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import ClientSessionGenerator, WebSocketGenerator

from homeassistant.components.image_upload import DOMAIN as IMAGE_UPLOAD_DOMAIN
from homeassistant.core import HomeAssistant

from custom_components.guest_access.engine import GuestEngine

COUNTS = "binary_sensor.guest_anna_counts"
STATUS = "sensor.guest_anna_status"
VISIT_ENDS = "sensor.guest_anna_visit_ends"
GUESTS_HOME = "binary_sensor.guest_access_guests_home"
UPLOAD = "/api/guest_access/picture"


@pytest.fixture
def hass_config_dir(hass_tmp_config_dir: str) -> str:
    """Uploaded images go to a directory of their own, not into the repository."""
    return hass_tmp_config_dir


def _png() -> io.BytesIO:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), (200, 50, 50)).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


async def _post(
    hass_client: ClientSessionGenerator, url: str, token: str | None = None
) -> aiohttp.ClientResponse:
    form = aiohttp.FormData()
    form.add_field("file", _png(), filename="anna.png", content_type="image/png")
    client = await hass_client(token) if token else await hass_client()
    return await client.post(url, data=form)


async def _upload(hass_client: ClientSessionGenerator, url: str = UPLOAD) -> str:
    """Upload a small PNG the way the page does (or elsewhere); the image's ID."""
    response = await _post(hass_client, url)
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


async def test_foreign_image_never_taken_or_deleted(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """An image uploaded elsewhere, a person's picture say, is no guest photo."""
    foreign = await _upload(hass_client, "/api/image/upload")
    reply = await _save(hass_ws_client, hass, picture=foreign)
    assert not reply["success"]
    assert reply["error"]["code"] == "invalid_format"
    own = await _upload(hass_client)
    assert (await _save(hass_ws_client, hass, picture=own))["success"]
    assert (await _save(hass_ws_client, hass, picture=None))["success"]
    assert _images(hass) == {foreign}


async def test_upload_for_administrators_only(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_read_only_access_token: str,
) -> None:
    """A user without administrator rights cannot upload a guest photo."""
    response = await _post(hass_client, UPLOAD, hass_read_only_access_token)
    assert response.status == 401
    assert _images(hass) == set()


async def test_upload_needs_an_image(
    hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    """A file that is no image is refused and nothing is noted."""
    engine: GuestEngine = entry.runtime_data
    form = aiohttp.FormData()
    form.add_field("file", io.BytesIO(b"not an image"), filename="x.png", content_type="text/plain")
    response = await (await hass_client()).post(UPLOAD, data=form)
    assert response.status == 400
    assert engine.data.pictures == {}


async def test_unsaved_upload_is_collected(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A photo uploaded but never saved with a guest is deleted after an hour."""
    engine: GuestEngine = entry.runtime_data
    image_id = await _upload(hass_client)
    assert image_id in engine.data.pictures
    freezer.tick(timedelta(minutes=30))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _images(hass) == {image_id}
    freezer.tick(timedelta(minutes=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _images(hass) == set()
    assert engine.data.pictures == {}


async def test_photo_deleted_elsewhere(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A photo deleted outside Guest Access leaves the guest without one; saving still works."""
    engine: GuestEngine = entry.runtime_data
    image_id = await _upload(hass_client)
    assert (await _save(hass_ws_client, hass, picture=image_id))["success"]
    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "image/delete", "image_id": image_id})
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()
    assert engine.data.guests["anna"].picture is None
    assert _attribute(hass, COUNTS, "entity_picture") is None
    # A page opened before still sends the old photo: it is dropped, the rest is saved
    assert (await _save(hass_ws_client, hass, picture=image_id, note="Still here"))["success"]
    assert engine.data.guests["anna"].picture is None
    assert engine.data.guests["anna"].note == "Still here"


async def test_shared_photo_stays_with_the_other_guest(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A photo two guests show stays until neither does."""
    engine: GuestEngine = entry.runtime_data
    image_id = await _upload(hass_client)
    assert (await _save(hass_ws_client, hass, picture=image_id))["success"]
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "guest_access/save_guest",
            "name": "Ben",
            "trackers": ["device_tracker.ben"],
            "approval": {"kind": "permanent", "windows": []},
            "picture": image_id,
        }
    )
    ben = (await client.receive_json())["result"]["guest_id"]
    await hass.async_block_till_done()
    assert (await _save(hass_ws_client, hass, picture=None))["success"]
    assert _images(hass) == {image_id}
    engine.async_delete_guest(ben)
    await hass.async_block_till_done()
    assert _images(hass) == set()


async def test_photos_go_with_the_entry(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """Removing the integration deletes its photos, and only those."""
    foreign = await _upload(hass_client, "/api/image/upload")
    image_id = await _upload(hass_client)
    assert (await _save(hass_ws_client, hass, picture=image_id))["success"]
    unsaved = await _upload(hass_client)
    assert _images(hass) == {foreign, image_id, unsaved}
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert _images(hass) == {foreign}


async def test_picture_not_recorded(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """The photo's address is left out of the history."""
    for entity_id in (COUNTS, STATUS):
        entity = hass.data["entity_components"][entity_id.split(".")[0]].get_entity(entity_id)
        assert entity is not None
        assert "entity_picture" in entity._Entity__combined_unrecorded_attributes
