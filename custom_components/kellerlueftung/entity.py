"""Base entity for Kellerlüftung."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from . import KellerlueftungConfigEntry
from .const import DOMAIN, NAME, SIGNAL_UPDATE, VERSION


class KellerlueftungEntity(Entity):
    """Base Kellerlüftung entity."""

    _attr_has_entity_name = True

    def __init__(self, entry: KellerlueftungConfigEntry) -> None:
        self.entry = entry
        self.controller = entry.runtime_data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=NAME,
            manufacturer="lenni76",
            model="Kellerlüftungsregelung",
            sw_version=VERSION,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to controller updates."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_UPDATE,
                self._handle_controller_update,
            )
        )

    @callback
    def _handle_controller_update(self, entry_id: str) -> None:
        if entry_id == self.entry.entry_id:
            self.async_write_ha_state()
