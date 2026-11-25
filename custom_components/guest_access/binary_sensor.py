"""Who counts and who is approved, per guest and in all; which rooms are locked; what is unreachable."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar, entity_registry as er
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import GuestAccessConfigEntry
from .const import DOMAIN
from .engine import GuestEngine
from .entity import GuestEntity, HubEntity, add_guest_entities
from .logic import counting_guests, locked_rooms, room_reason

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GuestAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the sensors of the Guest Access device and of every guest."""
    engine = entry.runtime_data
    async_add_entities(
        [GuestsHomeSensor(engine), OnlyGuestsHomeSensor(engine), UnreachableSensor(engine)]
    )

    def _create(engine: GuestEngine, guest_id: str) -> list[Entity]:
        return [GuestCountsSensor(engine, guest_id), GuestApprovedSensor(engine, guest_id)]

    add_guest_entities(entry, async_add_entities, _create)

    rooms: dict[str, RoomLockedSensor] = {}

    @callback
    def _rooms() -> None:
        """One sensor per lockable room, as the rooms are set now."""
        configured = [room.area_id for room in engine.data.settings.rooms]
        for area_id in set(rooms) - set(configured):
            # No longer lockable: the sensor goes for good
            sensor = rooms.pop(area_id)
            if sensor.registry_entry is not None:
                er.async_get(hass).async_remove(sensor.entity_id)
        new = [RoomLockedSensor(engine, area_id) for area_id in configured if area_id not in rooms]
        rooms.update({sensor.area_id: sensor for sensor in new})
        if new:
            async_add_entities(new)

    _rooms()
    entry.async_on_unload(engine.async_add_listener(_rooms))


class GuestCountsSensor(GuestEntity, BinarySensorEntity):
    """On while the guest counts as present."""

    _with_picture = True
    # The photo's address is for dashboards now, not for the history
    _unrecorded_attributes = frozenset({"entity_picture"})

    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(engine, guest_id, "counts", Platform.BINARY_SENSOR)

    @property
    def is_on(self) -> bool:
        """Whether the guest counts."""
        return self.engine.data.presence_of(self.guest_id).counting


class GuestApprovedSensor(GuestEntity, BinarySensorEntity):
    """On while the approval lets the guest count, home or not.

    For what should work only while a guest is welcome: a door code, the guest
    Wi-Fi. It follows the approval's end and its time windows.
    """

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(engine, guest_id, "approved", Platform.BINARY_SENSOR)

    @property
    def is_on(self) -> bool:
        """Whether the approval applies right now."""
        guest = self.engine.guest(self.guest_id)
        return guest is not None and guest.approval.valid(dt_util.utcnow())


class RoomLockedSensor(HubEntity, BinarySensorEntity):
    """On while the room is locked: only guests are home and none of them may enter it."""

    def __init__(self, engine: GuestEngine, area_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(engine, "room_locked")
        self.area_id = area_id
        self._attr_unique_id = f"{engine.entry.entry_id}_room_locked_{area_id}"
        self._attr_name = self._name()

    def _name(self) -> str:
        """ "<room> locked" in the language of Home Assistant, with the area's name of now."""
        template = self.engine.entity_name(Platform.BINARY_SENSOR, "room_locked")
        return template.format(room=self.engine.area_name(self.area_id))

    async def async_added_to_hass(self) -> None:
        """Follow the area too: the sensor is named after it."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.hass.bus.async_listen(ar.EVENT_AREA_REGISTRY_UPDATED, self._area_changed)
        )

    @callback
    def _area_changed(self, event: Event[ar.EventAreaRegistryUpdatedData]) -> None:
        if event.data["area_id"] == self.area_id and self.available:
            # Setting the name anew is what makes Home Assistant read it again
            self._attr_name = self._name()
            self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        """Whether the room is locked."""
        return self.area_id in locked_rooms(self.engine.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The area, and why the room is locked or free."""
        return {"area_id": self.area_id, "reason": room_reason(self.engine.data, self.area_id)}


class UnreachableSensor(HubEntity, BinarySensorEntity):
    """On while a tracker, resident or door contact is unavailable or gone.

    Guest Access then misses what that entity would report: a door of a locked
    room that opens, a guest or a resident who comes home.
    """

    # Entity IDs of trackers are for automations now, not for the history
    _unrecorded_attributes = frozenset({"entities"})

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, engine: GuestEngine) -> None:
        """Initialize the sensor."""
        super().__init__(engine, "unreachable")

    @property
    def is_on(self) -> bool:
        """Whether an entity is unreachable."""
        return bool(self.engine.unreachable())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The entities that are unreachable."""
        return {"entities": self.engine.unreachable()}


class GuestsHomeSensor(HubEntity, BinarySensorEntity):
    """On while any guest counts: what other parts of Home Assistant read to treat guests as home."""

    # Names and rooms are for automations now, not for the history
    _unrecorded_attributes = frozenset({"guests", "free_rooms", "locked_rooms", "guest_list"})

    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    def __init__(self, engine: GuestEngine) -> None:
        """Initialize the sensor."""
        super().__init__(engine, "guests_home")

    async def async_added_to_hass(self) -> None:
        """Follow the status sensors too: the guest list names them."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, self._status_sensor_changed
            )
        )

    @callback
    def _status_sensor_changed(self, event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        # A new guest's status sensor is registered after the guest is saved, and a
        # user can give it another entity ID
        entity = er.async_get(self.hass).async_get(event.data["entity_id"])
        if entity is not None and entity.platform == DOMAIN and entity.domain == Platform.SENSOR:
            self.async_write_ha_state()

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
