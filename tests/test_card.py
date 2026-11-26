"""The dashboard card: served, loaded on every page and kept as a dashboard resource."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.components.lovelace.const import LOVELACE_DATA, MODE_STORAGE, MODE_YAML
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.core import HomeAssistant

from custom_components.guest_access import frontend
from custom_components.guest_access.const import DOMAIN, TITLE
from custom_components.guest_access.frontend import CARD_PATH, DATA_CARD

CARD = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "guest_access"
    / "frontend"
    / "guest-access-card.js"
)


def _lovelace(mode: str, resources: Any) -> MagicMock:
    data = MagicMock()
    data.resource_mode = mode
    data.resources = resources
    return data


def _collection(items: list[dict[str, Any]]) -> MagicMock:
    collection = MagicMock(spec=ResourceStorageCollection)
    collection.async_get_info = AsyncMock()
    collection.async_items = MagicMock(return_value=items)
    collection.async_create_item = AsyncMock()
    collection.async_update_item = AsyncMock()
    collection.async_delete_item = AsyncMock()
    return collection


async def test_card_loaded_and_resource_created(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """With the frontend there the card is loaded on every page and added to the resources."""
    hass.data.pop(DATA_CARD)
    collection = _collection([{"id": "1", "url": "/local/other.js", "type": "module"}])
    hass.data[LOVELACE_DATA] = _lovelace(MODE_STORAGE, collection)
    hass.data[DATA_EXTRA_MODULE_URL] = MagicMock()
    with patch("custom_components.guest_access.frontend.add_extra_js_url") as add_url:
        await frontend.async_register_card(hass)
    url = hass.data[DATA_CARD]
    assert url.startswith(f"{CARD_PATH}?v=")
    add_url.assert_called_once_with(hass, url)
    collection.async_create_item.assert_awaited_once_with({"res_type": "module", "url": url})
    collection.async_update_item.assert_not_awaited()

    # Loaded once per run: a second setup adds nothing to the pages
    with patch("custom_components.guest_access.frontend.add_extra_js_url") as add_url:
        await frontend.async_register_card(hass)
    add_url.assert_not_called()


async def test_card_resource_updated(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """An entry of an earlier version is pointed to this one; a current one is left alone."""
    url = hass.data[DATA_CARD]
    collection = _collection([{"id": "7", "url": f"{CARD_PATH}?v=old", "type": "module"}])
    hass.data[LOVELACE_DATA] = _lovelace(MODE_STORAGE, collection)
    await frontend.async_register_card(hass)
    collection.async_update_item.assert_awaited_once_with("7", {"url": url})
    collection.async_create_item.assert_not_awaited()

    collection = _collection([{"id": "7", "url": url, "type": "module"}])
    hass.data[LOVELACE_DATA] = _lovelace(MODE_STORAGE, collection)
    await frontend.async_register_card(hass)
    collection.async_update_item.assert_not_awaited()
    collection.async_create_item.assert_not_awaited()


async def test_card_resource_left_alone(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Resources in YAML are the user's; a collection of another kind is left alone."""
    collection = _collection([{"id": "3", "url": hass.data[DATA_CARD], "type": "module"}])
    hass.data[LOVELACE_DATA] = _lovelace(MODE_YAML, collection)
    await frontend.async_register_card(hass)
    await frontend.async_remove_card_resource(hass)
    collection.async_create_item.assert_not_awaited()
    collection.async_delete_item.assert_not_awaited()

    hass.data[LOVELACE_DATA] = _lovelace(MODE_STORAGE, MagicMock())
    await frontend.async_register_card(hass)
    await frontend.async_remove_card_resource(hass)


async def test_remove_takes_the_resource_away_and_a_new_entry_brings_it_back(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """Removing the entry removes the card's dashboard resource; a new entry adds it again."""
    url = hass.data[DATA_CARD]
    items: list[dict[str, Any]] = [
        {"id": "1", "url": "/local/other.js", "type": "module"},
        {"id": "2", "url": url, "type": "module"},
    ]
    collection = _collection(items)
    hass.data[LOVELACE_DATA] = _lovelace(MODE_STORAGE, collection)
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    collection.async_delete_item.assert_awaited_once_with("2")

    items.pop()
    again = MockConfigEntry(domain=DOMAIN, title=TITLE)
    again.add_to_hass(hass)
    assert await hass.config_entries.async_setup(again.entry_id)
    await hass.async_block_till_done()
    collection.async_create_item.assert_awaited_once_with({"res_type": "module", "url": url})


def _language_keys(code: str, language: str) -> list[str]:
    """The keys of one language of the card's texts, in order."""
    start = code.index(f"\n    {language}: {{\n")
    end = code.index("\n    },", start)
    return re.findall(r"^\s+([A-Za-z_][A-Za-z0-9_]*): \"", code[start:end], re.MULTILINE)


def test_card_texts_have_each_key_once_in_both_languages() -> None:
    """A key written twice silently takes the later text; both languages have the same keys."""
    code = CARD.read_text(encoding="utf-8")
    english = _language_keys(code, "en")
    german = _language_keys(code, "de")
    assert len(english) > 50
    for keys in (english, german):
        twice = sorted({key for key in keys if keys.count(key) > 1})
        assert not twice, twice
    assert english == german


def test_card_changes_nothing() -> None:
    """The card reads entities only: no command of the page, no action, no fetch."""
    code = CARD.read_text(encoding="utf-8")
    for call in ("callWS", "callService", "callApi", "fetch(", "guest_access/", "sendMessage"):
        assert call not in code, call
    # Every option the card reads has a field in its editor, and a text in both languages
    options = set(re.findall(r"\bc\.(\w+)", code))
    for option in options - {"title", "size", "mode"}:
        assert f'"{option}"' in code, option
