"""Kellerlüftung custom integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .controller import KellerlueftungController


type KellerlueftungConfigEntry = ConfigEntry[KellerlueftungController]


async def async_setup_entry(hass: HomeAssistant, entry: KellerlueftungConfigEntry) -> bool:
    """Set up Kellerlüftung from a config entry."""
    controller = KellerlueftungController(hass, entry)
    entry.runtime_data = controller
    await controller.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KellerlueftungConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_stop()
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: KellerlueftungConfigEntry) -> None:
    """Reload when configuration or options change."""
    await hass.config_entries.async_reload(entry.entry_id)
