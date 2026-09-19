"""Schalter 'Automatikmodus' für die Juwel HeliaLux AppControl.

An  = Zeitplan aktiv (Automatik).
Aus = Zeitplan pausiert (manueller/Vorschau-Modus), damit Licht-Entity greift.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JuwelCoordinator
from .entity import JuwelEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JuwelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(JuwelAutoSwitch(coordinator, cid) for cid in coordinator.data)


class JuwelAutoSwitch(JuwelEntity, SwitchEntity):
    """Automatik-Zeitplan an/aus."""

    _attr_translation_key = "auto_mode"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: JuwelCoordinator, cloud_device_id: str) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._attr_unique_id = f"{cloud_device_id}_auto"

    @property
    def is_on(self) -> bool:
        return self._state.get("mode") == "auto"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.resume_schedule(self._cid)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.pause_schedule(self._cid)
        await self.coordinator.async_request_refresh()
