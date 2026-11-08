"""Triggers: what happens to a guest, and a door of a locked room that opens."""

from __future__ import annotations

from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GuestAccessConfigEntry
from .const import EVENT_OPENED, GUEST_EVENT_TYPES
from .engine import GuestEngine
from .entity import GuestEntity, HubEntity, add_guest_entities

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GuestAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the room violation and the event entity of every guest."""
    async_add_entities([RoomViolationEvent(entry.runtime_data)])

    def _create(engine: GuestEngine, guest_id: str) -> list[Entity]:
        return [GuestEvent(engine, guest_id)]

    add_guest_entities(entry, async_add_entities, _create)


class GuestEvent(GuestEntity, EventEntity):
    """Arrived, left, time up, approval expired or changed."""

    _attr_event_types = GUEST_EVENT_TYPES

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the entity."""
        super().__init__(engine, guest_id, "activity")

    async def async_added_to_hass(self) -> None:
        """Follow the events of this guest."""
        await super().async_added_to_hass()
        self.async_on_remove(self.engine.async_add_event_listener(self._event))

    @callback
    def _changed(self) -> None:
        """Only events change this entity."""

    @callback
    def _event(self, guest_id: str | None, event_type: str, data: dict[str, Any]) -> None:
        if guest_id == self.guest_id and event_type in GUEST_EVENT_TYPES:
            self._trigger_event(event_type, data)
            self.async_write_ha_state()


class RoomViolationEvent(HubEntity, EventEntity):
    """The door of a locked room opened while only guests are home."""

    _attr_event_types = [EVENT_OPENED]

    def __init__(self, engine: GuestEngine) -> None:
        """Initialize the entity."""
        super().__init__(engine, "room_violation")

    async def async_added_to_hass(self) -> None:
        """Follow the room violations."""
        await super().async_added_to_hass()
        self.async_on_remove(self.engine.async_add_event_listener(self._event))

    @callback
    def _changed(self) -> None:
        """Only events change this entity."""

    @callback
    def _event(self, guest_id: str | None, event_type: str, data: dict[str, Any]) -> None:
        if guest_id is None and event_type == EVENT_OPENED:
            self._trigger_event(event_type, data)
            self.async_write_ha_state()
