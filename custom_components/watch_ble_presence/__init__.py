"""Watch BLE Presence integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import CONF_WATCHES, DOMAIN, PLATFORMS
from .coordinator import WatchBleCoordinator, WatchDefinition


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configure watches using IRKs stored by Watch BLE Presence."""
    watches = [
        WatchDefinition(
            watch_id=watch["id"],
            irk=bytes.fromhex(watch["irk"]),
            name=watch["name"],
        )
        for watch in entry.data.get(CONF_WATCHES, [])
    ]

    # Read the shared Bluetooth cache without requesting scans or listeners.
    coordinator = WatchBleCoordinator(hass, entry, watches)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _remove_orphan_watches(hass, entry, {watch.watch_id for watch in watches})
    return True


def _remove_orphan_watches(hass: HomeAssistant, entry: ConfigEntry, active_ids: set[str]) -> None:
    """Remove only devices and entities belonging to removed watch definitions."""
    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    for device in dr.async_entries_for_config_entry(devices, entry.entry_id):
        watch_ids = {identifier for domain, identifier in device.identifiers if domain == DOMAIN}
        if not watch_ids or watch_ids & active_ids:
            continue
        for entity in er.async_entries_for_device(entities, device.id, include_disabled_entities=True):
            if entity.config_entry_id == entry.entry_id and entity.platform == DOMAIN:
                entities.async_remove(entity.entity_id)
        if device.config_entries == {entry.entry_id}:
            devices.async_remove_device(device.id)
        else:
            devices.async_update_device(device.id, remove_config_entry_id=entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Watch BLE Presence entities."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
