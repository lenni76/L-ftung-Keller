"""Select platform for Kellerlüftung."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import KellerlueftungConfigEntry
from .const import MODE_AUTOMATIC, MODES
from .entity import KellerlueftungEntity


async def async_setup_entry(hass: HomeAssistant, entry: KellerlueftungConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up operating mode select."""
    async_add_entities([KellerModeSelect(entry)])


class KellerModeSelect(KellerlueftungEntity, SelectEntity, RestoreEntity):
    """Operating mode selector."""

    _attr_translation_key = "operating_mode"
    _attr_icon = "mdi:fan-auto"
    _attr_options = MODES

    def __init__(self, entry: KellerlueftungConfigEntry) -> None:
        super().__init__(entry)
        self._attr_unique_id = f"{entry.entry_id}_operating_mode"
        self._attr_current_option = MODE_AUTOMATIC

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        previous = await self.async_get_last_state()
        if previous and previous.state in MODES:
            self._attr_current_option = previous.state
            await self.controller.async_set_mode(previous.state)

    async def async_select_option(self, option: str) -> None:
        """Change operating mode."""
        if option not in MODES:
            raise ValueError(f"Unsupported option: {option}")
        self._attr_current_option = option
        await self.controller.async_set_mode(option)
        self.async_write_ha_state()
