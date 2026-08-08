"""Sensor platform for Kellerlüftung."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KellerlueftungConfigEntry
from .entity import KellerlueftungEntity


@dataclass(frozen=True, kw_only=True)
class KellerSensorDescription(SensorEntityDescription):
    value_fn: Callable[[object], object]


SENSORS = (
    KellerSensorDescription(key="absolute_humidity_indoor", translation_key="absolute_humidity_indoor", native_unit_of_measurement="g/m³", state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2, value_fn=lambda s: s.indoor_absolute_humidity),
    KellerSensorDescription(key="absolute_humidity_outdoor", translation_key="absolute_humidity_outdoor", native_unit_of_measurement="g/m³", state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2, value_fn=lambda s: s.outdoor_absolute_humidity),
    KellerSensorDescription(key="humidity_delta", translation_key="humidity_delta", native_unit_of_measurement="g/m³", state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2, value_fn=lambda s: s.humidity_delta),
    KellerSensorDescription(key="dew_point_indoor", translation_key="dew_point_indoor", device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1, value_fn=lambda s: s.indoor_dew_point),
    KellerSensorDescription(key="dew_point_outdoor", translation_key="dew_point_outdoor", device_class=SensorDeviceClass.TEMPERATURE, native_unit_of_measurement=UnitOfTemperature.CELSIUS, state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=1, value_fn=lambda s: s.outdoor_dew_point),
    KellerSensorDescription(key="required_delta", translation_key="required_delta", native_unit_of_measurement="g/m³", state_class=SensorStateClass.MEASUREMENT, suggested_display_precision=2, value_fn=lambda s: s.required_delta),
    KellerSensorDescription(key="status", translation_key="status", value_fn=lambda s: s.status),
    KellerSensorDescription(key="decision", translation_key="decision", value_fn=lambda s: s.reason),
)


async def async_setup_entry(hass: HomeAssistant, entry: KellerlueftungConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Kellerlüftung sensors."""
    async_add_entities(KellerSensor(entry, description) for description in SENSORS)


class KellerSensor(KellerlueftungEntity, SensorEntity):
    """Representation of a Kellerlüftung sensor."""

    entity_description: KellerSensorDescription

    def __init__(self, entry: KellerlueftungConfigEntry, description: KellerSensorDescription) -> None:
        super().__init__(entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self):
        """Return sensor value."""
        return self.entity_description.value_fn(self.controller.snapshot)
