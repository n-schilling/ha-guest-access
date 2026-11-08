"""Repairs: trackers, residents, doors and areas the guests or the settings use but that are gone."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, entity_registry as er, issue_registry as ir

from .const import DOMAIN
from .model import AccessData


@dataclass(frozen=True, slots=True)
class Problem:
    """One repair issue."""

    key: str
    severity: ir.IssueSeverity
    placeholders: dict[str, str]


def _missing(hass: HomeAssistant, entity_id: str) -> bool:
    """Gone: neither registered nor with a state."""
    return er.async_get(hass).async_get(entity_id) is None and hass.states.get(entity_id) is None


def find_problems(hass: HomeAssistant, data: AccessData) -> dict[str, Problem]:
    """The issues that should be open now, by issue id."""
    problems: dict[str, Problem] = {}
    for guest in data.guests.values():
        for tracker in guest.trackers:
            if _missing(hass, tracker):
                problems[f"missing_tracker_{guest.id}_{tracker}"] = Problem(
                    "missing_tracker",
                    ir.IssueSeverity.WARNING,
                    {"guest": guest.name, "entity": tracker},
                )
    for person in data.settings.residents:
        if _missing(hass, person):
            problems[f"missing_resident_{person}"] = Problem(
                "missing_resident", ir.IssueSeverity.WARNING, {"entity": person}
            )
    areas = ar.async_get(hass)
    for room in data.settings.rooms:
        area = areas.async_get_area(room.area_id)
        if area is None:
            problems[f"missing_area_{room.area_id}"] = Problem(
                "missing_area",
                ir.IssueSeverity.ERROR,
                {"area": room.area_id, "entity": room.door},
            )
        elif _missing(hass, room.door):
            problems[f"missing_door_{room.door}"] = Problem(
                "missing_door",
                ir.IssueSeverity.ERROR,
                {"room": area.name, "entity": room.door},
            )
    return problems


@callback
def async_update_issues(hass: HomeAssistant, data: AccessData) -> None:
    """Open the issues that apply, close the ones that no longer do."""
    wanted = find_problems(hass, data)
    registry = ir.async_get(hass)
    for domain, issue_id in list(registry.issues):
        if domain == DOMAIN and issue_id not in wanted:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
    for issue_id, problem in wanted.items():
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id,
            is_fixable=False,
            severity=problem.severity,
            translation_key=problem.key,
            translation_placeholders=problem.placeholders,
        )


@callback
def async_clear_issues(hass: HomeAssistant) -> None:
    """Close every issue of Guest Access."""
    for domain, issue_id in list(ir.async_get(hass).issues):
        if domain == DOMAIN:
            ir.async_delete_issue(hass, DOMAIN, issue_id)
