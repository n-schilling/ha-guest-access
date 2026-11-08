"""A guest's status and when the visit ends."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GuestAccessConfigEntry
from .engine import GuestEngine
from .entity import GuestEntity, add_guest_entities
from .logic import GuestStatus

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GuestAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the sensors of every guest."""

    def _create(engine: GuestEngine, guest_id: str) -> list[Entity]:
        return [GuestStatusSensor(engine, guest_id), VisitEndsSensor(engine, guest_id)]

    add_guest_entities(entry, async_add_entities, _create)


class VisitEndsSensor(GuestEntity, SensorEntity):
    """The end of the visit; unknown while the guest does not count or the time is unlimited."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(engine, guest_id, "visit_ends")

    @property
    def native_value(self) -> datetime | None:
        """The end of the visit."""
        presence = self.engine.data.presence_of(self.guest_id)
        return presence.visit_ends if presence.counting else None


class GuestStatusSensor(GuestEntity, SensorEntity):
    """Counts, time up, approval expired, home without approval, resuming or away."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [status.value for status in GuestStatus]

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(engine, guest_id, "status")

    @property
    def native_value(self) -> str:
        """The status of the guest."""
        return self.engine.status(self.guest_id).value
