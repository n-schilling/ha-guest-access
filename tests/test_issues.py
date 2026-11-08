"""Repairs for trackers, residents, doors and areas that are gone."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, entity_registry as er, issue_registry as ir

from custom_components.guest_access.const import DOMAIN
from custom_components.guest_access.engine import GuestEngine
from custom_components.guest_access.model import Room, Settings

from .conftest import DOOR, RESIDENT, TRACKER


def issues(hass: HomeAssistant) -> dict[str, ir.IssueEntry]:
    """The open issues of Guest Access."""
    return {
        issue_id: issue
        for (domain, issue_id), issue in ir.async_get(hass).issues.items()
        if domain == DOMAIN
    }


async def test_missing_tracker(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """A tracker without entity or state is reported until it shows up."""
    issue = issues(hass)[f"missing_tracker_anna_{TRACKER}"]
    assert issue.translation_key == "missing_tracker"
    assert issue.translation_placeholders == {"guest": "Anna", "entity": TRACKER}
    assert issue.severity is ir.IssueSeverity.WARNING
    hass.states.async_set(TRACKER, "not_home")
    await hass.async_block_till_done()
    assert issues(hass) == {}


async def test_registered_tracker_without_state(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    """A registered tracker whose integration has not loaded yet is no problem."""
    er.async_get(hass).async_get_or_create(
        "device_tracker", "test", "anna", suggested_object_id="anna_phone"
    )
    await hass.async_block_till_done()
    assert issues(hass) == {}


async def test_missing_resident_door_and_area(
    hass: HomeAssistant, entry: MockConfigEntry, bedroom: str
) -> None:
    """Residents, door contacts and areas that disappear are reported, doors and areas as errors."""
    hass.states.async_set(TRACKER, "home")
    hass.states.async_remove(RESIDENT)
    hass.states.async_remove(DOOR)
    await hass.async_block_till_done()
    found = issues(hass)
    assert found[f"missing_resident_{RESIDENT}"].translation_placeholders == {"entity": RESIDENT}
    door = found[f"missing_door_{DOOR}"]
    assert door.severity is ir.IssueSeverity.ERROR
    assert door.translation_placeholders == {"room": "Bedroom", "entity": DOOR}

    ar.async_get(hass).async_delete(bedroom)
    await hass.async_block_till_done()
    area = issues(hass)[f"missing_area_{bedroom}"]
    assert area.translation_placeholders == {"area": bedroom, "entity": DOOR}
    assert f"missing_door_{DOOR}" not in issues(hass)

    engine: GuestEngine = entry.runtime_data
    engine.async_save_settings(Settings((), ()))
    await hass.async_block_till_done()
    assert set(issues(hass)) == set()


async def test_issues_removed_with_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Removing the entry closes its issues; a new door added later is checked again."""
    engine: GuestEngine = entry.runtime_data
    area = ar.async_get(hass).async_create("Office")
    engine.async_save_settings(Settings((RESIDENT,), (Room(area.id, "binary_sensor.office_door"),)))
    await hass.async_block_till_done()
    assert "missing_door_binary_sensor.office_door" in issues(hass)
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert issues(hass) == {}
