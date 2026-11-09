"""Base classes: entities of a guest's device and of the Guest Access device."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GuestAccessConfigEntry
from .const import DOMAIN, TITLE
from .engine import GuestEngine


class GuestAccessEntity(Entity):
    """An entity that follows the engine."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, engine: GuestEngine) -> None:
        """Initialize the entity."""
        self.engine = engine

    async def async_added_to_hass(self) -> None:
        """Write the state after every change of the engine."""
        self.async_on_remove(self.engine.async_add_listener(self._changed))

    @callback
    def _changed(self) -> None:
        self.async_write_ha_state()


class HubEntity(GuestAccessEntity):
    """An entity of the Guest Access device."""

    def __init__(self, engine: GuestEngine, key: str) -> None:
        """Initialize the entity."""
        super().__init__(engine)
        entry_id = engine.entry.entry_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=TITLE,
            entry_type=DeviceEntryType.SERVICE,
        )


class GuestEntity(GuestAccessEntity):
    """An entity of a guest's device."""

    def __init__(self, engine: GuestEngine, guest_id: str, key: str) -> None:
        """Initialize the entity."""
        super().__init__(engine)
        self.guest_id = guest_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{guest_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """The guest's device, with the name the guest has now.

        Home Assistant applies this again whenever the entity is added, also after
        an entity ID change; a name kept from creation would undo a later rename.
        """
        guest = self.engine.guest(self.guest_id)
        return DeviceInfo(
            identifiers={(DOMAIN, self.guest_id)},
            name=self.guest_id if guest is None else guest.name,
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def available(self) -> bool:
        """Available while the guest exists."""
        return self.engine.guest(self.guest_id) is not None

    @callback
    def _changed(self) -> None:
        # A removed guest's entities go with its device; until then nothing to write
        if self.available:
            self.async_write_ha_state()


def add_guest_entities(
    entry: GuestAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    create: Callable[[GuestEngine, str], list[Entity]],
) -> None:
    """Add the entities of every guest now and of every guest added later."""
    engine = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add() -> None:
        new = [guest_id for guest_id in engine.data.guests if guest_id not in known]
        known.intersection_update(engine.data.guests)
        known.update(new)
        if new:
            async_add_entities([entity for guest_id in new for entity in create(engine, guest_id)])

    _add()
    entry.async_on_unload(engine.async_add_listener(_add))
