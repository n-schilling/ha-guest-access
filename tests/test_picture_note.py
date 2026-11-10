"""A guest's photo, uploaded through Guest Access, and a note for administrators."""

from __future__ import annotations

from datetime import timedelta
import io
import shutil
from typing import Any

import aiohttp
from freezegun.api import FrozenDateTimeFactory
from PIL import Image
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant.typing import ClientSessionGenerator, WebSocketGenerator

from homeassistant.components.image_upload import DOMAIN as IMAGE_UPLOAD_DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.guest_access.const import DOMAIN, STORAGE_KEY
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
    assert response.status == 403
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
    """A photo uploaded but never saved with a guest is deleted after a day."""
    engine: GuestEngine = entry.runtime_data
    image_id = await _upload(hass_client)
    assert image_id in engine.data.pictures
    freezer.tick(timedelta(hours=23))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert _images(hass) == {image_id}
    freezer.tick(timedelta(hours=2))
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


async def test_upload_is_cleaned(
    hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    """The stored photo has no metadata, a fixed file name and a limited size."""
    exif = Image.Exif()
    exif[0x010F] = "Camera maker"
    exif[0x0132] = "2026:11:09 12:00:00"
    buffer = io.BytesIO()
    Image.new("RGB", (3000, 1500), (10, 120, 200)).save(buffer, format="JPEG", exif=exif)
    form = aiohttp.FormData()
    form.add_field(
        "file", buffer.getvalue(), filename="Anna at home.jpg", content_type="image/jpeg"
    )
    response = await (await hass_client()).post(UPLOAD, data=form)
    assert response.status == 200, await response.text()
    image_id = (await response.json())["id"]

    item = hass.data[IMAGE_UPLOAD_DOMAIN].data[image_id]
    assert item["name"] == "guest"
    assert item["content_type"] == "image/jpeg"
    original = await (await hass_client()).get(f"/api/image/serve/{image_id}/original")
    assert original.status == 200
    with Image.open(io.BytesIO(await original.read())) as stored:
        assert stored.size == (1024, 512)
        assert not stored.getexif()


async def test_upload_refuses_huge_image(
    hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    """A small file that unpacks to a huge image is refused before it is decoded."""
    buffer = io.BytesIO()
    # 48 megapixels, a few kilobytes as a file
    Image.new("1", (8000, 6000)).save(buffer, format="PNG")
    form = aiohttp.FormData()
    form.add_field("file", buffer.getvalue(), filename="big.png", content_type="image/png")
    response = await (await hass_client()).post(UPLOAD, data=form)
    assert response.status == 400
    assert _images(hass) == set()


async def test_upload_keeps_transparency(
    hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    """A transparent picture stays a PNG."""
    buffer = io.BytesIO()
    Image.new("RGBA", (16, 16), (0, 0, 0, 0)).save(buffer, format="PNG")
    form = aiohttp.FormData()
    form.add_field("file", buffer.getvalue(), filename="a.png", content_type="image/png")
    response = await (await hass_client()).post(UPLOAD, data=form)
    image_id = (await response.json())["id"]
    assert hass.data[IMAGE_UPLOAD_DOMAIN].data[image_id]["content_type"] == "image/png"


async def test_upload_refuses_other_content(
    hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    """No file, another type or a broken image: refused, nothing stored."""
    client = await hass_client()
    assert (await client.post(UPLOAD, data={"file": "text"})).status == 400
    for content, content_type in ((b"<svg/>", "image/svg+xml"), (b"broken", "image/png")):
        form = aiohttp.FormData()
        form.add_field("file", content, filename="x", content_type=content_type)
        assert (await client.post(UPLOAD, data=form)).status == 400
    assert _images(hass) == set()


async def test_upload_without_the_integration(
    hass: HomeAssistant, entry: MockConfigEntry, hass_client: ClientSessionGenerator
) -> None:
    """With the entry unloaded there is no upload."""
    assert await hass.config_entries.async_unload(entry.entry_id)
    response = await _post(hass_client, UPLOAD)
    assert response.status == 404
    assert _images(hass) == set()


async def test_photo_deleted_while_unloaded(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A photo deleted while the integration did not listen is forgotten at the next start."""
    image_id = await _upload(hass_client)
    assert (await _save(hass_ws_client, hass, picture=image_id))["success"]
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.data[IMAGE_UPLOAD_DOMAIN].async_delete_item(image_id)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    engine: GuestEngine = entry.runtime_data
    assert engine.data.guests["anna"].picture is None
    assert engine.data.pictures == {}
    assert _attribute(hass, COUNTS, "entity_picture") is None


async def test_stored_photo_that_is_not_owned(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    stored: dict[str, Any],
    hass_client: ClientSessionGenerator,
) -> None:
    """A stored photo that is not one of the integration's is dropped, the image stays."""
    assert await async_setup_component(hass, "image_upload", {})
    foreign = await _upload(hass_client, "/api/image/upload")
    stored["guests"][0]["picture"] = foreign
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": stored,
    }
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    engine: GuestEngine = entry.runtime_data
    assert engine.data.guests["anna"].picture is None
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert _images(hass) == {foreign}


async def test_removal_survives_a_missing_file(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    hass_client: ClientSessionGenerator,
    hass_storage: dict[str, Any],
) -> None:
    """A photo whose folder is gone does not keep the store or the other photos."""
    first = await _upload(hass_client)
    second = await _upload(hass_client)
    await hass.async_add_executor_job(shutil.rmtree, hass.config.path("image", first))
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert second not in _images(hass)
    assert STORAGE_KEY not in hass_storage


async def test_long_stored_name_still_loads(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    stored: dict[str, Any],
    hass_ws_client: WebSocketGenerator,
) -> None:
    """A name longer than today's limit, stored by an older version, loads; input is limited."""
    stored["guests"][0]["name"] = "A" * 300
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "minor_version": 1,
        "key": STORAGE_KEY,
        "data": stored,
    }
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.data.guests["anna"].name == "A" * 300

    assert not (await _save(hass_ws_client, hass, name="B" * 101))["success"]
    assert (await _save(hass_ws_client, hass, name="B" * 100))["success"]
