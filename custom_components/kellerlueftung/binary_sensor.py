"""Binary sensor platform for Kellerlüftung."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import KellerlueftungConfigEntry
from .entity import KellerlueftungEntity


@dataclass(frozen=True, kw_only=True)
class KellerBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[object], bool]


BINARY_SENSORS = (
    KellerBinaryDescription(key="ventilation_useful", translation_key="ventilation_useful", icon="mdi:fan-check", value_fn=lambda s: s.ventilation_useful),
    KellerBinaryDescription(key="dryer_active", translation_key="dryer_active", icon="mdi:tumble-dryer", value_fn=lambda s: s.dryer_active),
    KellerBinaryDescription(key="sensors_ok", translation_key="sensors_ok", icon="mdi:check-network-outline", value_fn=lambda s: s.sensors_ok),
)


async def async_setup_entry(hass: HomeAssistant, entry: KellerlueftungConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up Kellerlüftung binary sensors."""
    async_add_entities(KellerBinarySensor(entry, description) for description in BINARY_SENSORS)


class KellerBinarySensor(KellerlueftungEntity, BinarySensorEntity):
    """Representation of a Kellerlüftung binary sensor."""

    entity_description: KellerBinaryDescription

    def __init__(self, entry: KellerlueftungConfigEntry, description: KellerBinaryDescription) -> None:
        super().__init__(entry)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return binary state."""
        return self.entity_description.value_fn(self.controller.snapshot)
