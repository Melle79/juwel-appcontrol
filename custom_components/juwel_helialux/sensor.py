"""Profil-Sensor: aktives Profil + Tageskurve als Attribut (für die Karte)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
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
    async_add_entities(JuwelPresetSensor(coordinator, cid) for cid in coordinator.data)


class JuwelPresetSensor(JuwelEntity, SensorEntity):
    """Aktives Beleuchtungsprofil; liefert die Tageskurve als Attribut."""

    _attr_name = "Profil"
    _attr_icon = "mdi:chart-bell-curve-cumulative"

    def __init__(self, coordinator: JuwelCoordinator, cloud_device_id: str) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._attr_unique_id = f"{cloud_device_id}_preset"

    @property
    def _preset(self) -> dict[str, Any] | None:
        return self.coordinator.data.get(self._cid, {}).get("active_preset")

    @property
    def native_value(self) -> str | None:
        preset = self._preset
        if preset:
            return preset.get("name")
        slot = self._state.get("active_preset")
        return f"Slot {slot}" if slot is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        preset = self._preset or {}
        # timeEvents: [{time: Minuten ab 0 Uhr, value: {red,green,blue,white} in %}]
        events = []
        for ev in preset.get("timeEvents") or []:
            val = ev.get("value") or {}
            events.append(
                {
                    "time": ev.get("time"),
                    "white": val.get("white", 0),
                    "red": val.get("red", 0),
                    "green": val.get("green", 0),
                    "blue": val.get("blue", 0),
                }
            )
        return {
            "preset_id": preset.get("id"),
            "preset_type": preset.get("type"),
            "preset_color": preset.get("color"),
            "time_events": events,
            "mode": self._state.get("mode"),
            "status": self._state.get("status"),
            "connected": self._state.get("connected"),
        }
