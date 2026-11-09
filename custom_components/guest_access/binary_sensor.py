"""Who counts: per guest, all guests, and whether only guests are home."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GuestAccessConfigEntry
from .engine import GuestEngine
from .entity import GuestEntity, HubEntity, add_guest_entities
from .logic import counting_guests

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GuestAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the sensors of the Guest Access device and of every guest."""
    engine = entry.runtime_data
    async_add_entities([GuestsHomeSensor(engine), OnlyGuestsHomeSensor(engine)])

    def _create(engine: GuestEngine, guest_id: str) -> list[Entity]:
        return [GuestCountsSensor(engine, guest_id)]

    add_guest_entities(entry, async_add_entities, _create)


class GuestCountsSensor(GuestEntity, BinarySensorEntity):
    """On while the guest counts as present."""

    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(engine, guest_id, "counts", Platform.BINARY_SENSOR)

    @property
    def is_on(self) -> bool:
        """Whether the guest counts."""
        return self.engine.data.presence_of(self.guest_id).counting


class GuestsHomeSensor(HubEntity, BinarySensorEntity):
    """On while any guest counts: what other parts of Home Assistant read to treat guests as home."""

    # Names and rooms are for automations now, not for the history
    _unrecorded_attributes = frozenset({"guests", "free_rooms", "locked_rooms", "guest_list"})

    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    def __init__(self, engine: GuestEngine) -> None:
        """Initialize the sensor."""
        super().__init__(engine, "guests_home")

    @property
    def is_on(self) -> bool:
        """Whether any guest counts."""
        return bool(counting_guests(self.engine.data))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The guests who count, the free and locked rooms, and the guests to show."""
        return self.engine.summary()


class OnlyGuestsHomeSensor(HubEntity, BinarySensorEntity):
    """On while guests count and no resident is home."""

    def __init__(self, engine: GuestEngine) -> None:
        """Initialize the sensor."""
        super().__init__(engine, "only_guests_home")

    @property
    def is_on(self) -> bool:
        """Whether only guests are home."""
        return self.engine.only_guests_home
