"""A guest's status, the ends of visit and approval, the hours; how many guests are home and since when."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import Platform, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import GuestAccessConfigEntry
from .engine import GuestEngine
from .entity import GuestEntity, HubEntity, add_guest_entities
from .logic import GuestStatus, counting_guests, home_since, last_month_minutes, month_minutes

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GuestAccessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the hub's sensor and the sensors of every guest."""
    async_add_entities(
        [GuestsHomeSinceSensor(entry.runtime_data), GuestsCountSensor(entry.runtime_data)]
    )

    def _create(engine: GuestEngine, guest_id: str) -> list[Entity]:
        return [
            GuestStatusSensor(engine, guest_id),
            VisitEndsSensor(engine, guest_id),
            ApprovalEndsSensor(engine, guest_id),
            MonthHoursSensor(engine, guest_id),
            LastMonthHoursSensor(engine, guest_id),
        ]

    add_guest_entities(entry, async_add_entities, _create)


class VisitEndsSensor(GuestEntity, SensorEntity):
    """The end of the visit; unknown while the guest does not count or the time is unlimited."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(engine, guest_id, "visit_ends", Platform.SENSOR)

    @property
    def native_value(self) -> datetime | None:
        """The end of the visit."""
        presence = self.engine.data.presence_of(self.guest_id)
        return presence.visit_ends if presence.counting else None


class ApprovalEndsSensor(GuestEntity, SensorEntity):
    """The end of the approval; unknown for one without an end or switched off."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(engine, guest_id, "approval_ends", Platform.SENSOR)

    @property
    def native_value(self) -> datetime | None:
        """The end of the approval."""
        guest = self.engine.guest(self.guest_id)
        return None if guest is None else guest.approval.until


class GuestStatusSensor(GuestEntity, SensorEntity):
    """Counts, time up, approval expired, home without approval, resuming or away."""

    _with_picture = True
    # The photo's address is for dashboards now, not for the history
    _unrecorded_attributes = frozenset({"entity_picture"})

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [status.value for status in GuestStatus]

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(engine, guest_id, "status", Platform.SENSOR)

    @property
    def native_value(self) -> str:
        """The status of the guest."""
        return self.engine.status(self.guest_id).value


class GuestsHomeSinceSensor(HubEntity, SensorEntity):
    """Since when guests count: the earliest arrival; unknown while no guest counts.

    It comes from the stored visits, so a restart or a return within the grace time
    does not move it.
    """

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, engine: GuestEngine) -> None:
        """Initialize the sensor."""
        super().__init__(engine, "guests_home_since")

    @property
    def native_value(self) -> datetime | None:
        """The earliest arrival of the guests who count."""
        return home_since(self.engine.data)


class GuestsCountSensor(HubEntity, SensorEntity):
    """How many guests count right now."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, engine: GuestEngine) -> None:
        """Initialize the sensor."""
        super().__init__(engine, "guests_count")

    @property
    def native_value(self) -> int:
        """The number of guests who count."""
        return len(counting_guests(self.engine.data))


class MonthHoursSensor(GuestEntity, SensorEntity):
    """The hours of the guest's finished visits this month, from the visit log.

    Unknown while the guest keeps no visit log.
    """

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    # Every user can read an entity, the log is for administrators: off until enabled
    _attr_entity_registry_enabled_default = False
    _attr_suggested_display_precision = 2

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the sensor."""
        super().__init__(engine, guest_id, "month_hours", Platform.SENSOR)

    @property
    def native_value(self) -> float | None:
        """The hours this month."""
        guest = self.engine.guest(self.guest_id)
        if guest is None or not guest.log_visits:
            return None
        return month_minutes(self.engine.data, self.guest_id, dt_util.utcnow()) / 60


class LastMonthHoursSensor(MonthHoursSensor):
    """The hours of the guest's visits last month: the figure to settle at the start of a month.

    Unknown while the guest keeps no visit log, or while monthly totals are kept
    for the current month only.
    """

    def __init__(self, engine: GuestEngine, guest_id: str) -> None:
        """Initialize the sensor."""
        GuestEntity.__init__(self, engine, guest_id, "last_month_hours", Platform.SENSOR)

    @property
    def native_value(self) -> float | None:
        """The hours last month; unknown when last month's total is not kept."""
        guest = self.engine.guest(self.guest_id)
        if guest is None or not guest.log_visits:
            return None
        if self.engine.data.settings.log_keep_months < 2:
            return None
        return last_month_minutes(self.engine.data, self.guest_id, dt_util.utcnow()) / 60
