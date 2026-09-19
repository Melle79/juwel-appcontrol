"""Profil-Sensor: aktives Profil + Tageskurve als Attribut (für die Karte)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JuwelCoordinator
from .entity import JuwelEntity
from .traits import LIGHT_TRAITS, SKIP_TRAITS, TraitSpec, slug


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JuwelCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for cid, data in coordinator.data.items():
        if data.get("is_light"):
            entities.append(JuwelPresetSensor(coordinator, cid))

        # Everything without a safe control becomes read-only, so nothing is lost
        traits: dict[str, TraitSpec] = data.get("traits") or {}
        for spec in traits.values():
            if spec.trait in SKIP_TRAITS:
                continue
            if data.get("is_light") and spec.trait in LIGHT_TRAITS:
                continue
            if _has_control(spec, data):
                continue
            entities.append(JuwelTraitSensor(coordinator, cid, spec))

    async_add_entities(entities)


def _has_control(spec: TraitSpec, data: dict[str, Any]) -> bool:
    """True if another platform already exposes this trait as a control."""
    from .button import _enum_options
    from .select import SELECT_TRAITS
    from .switch import SWITCH_TRAITS
    from .traits import T_FEED, T_TIMER_RESET

    if spec.trait in (T_FEED, T_TIMER_RESET):
        return True
    if spec.trait in SELECT_TRAITS and spec.enum:
        return True
    if spec.trait in SWITCH_TRAITS and (spec.enum is not None or spec.is_boolean):
        return True
    if spec.numeric_property():
        return True
    return False


class JuwelTraitSensor(JuwelEntity, SensorEntity):
    """Read-only view of a trait we do not offer a control for (yet)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: JuwelCoordinator, cloud_device_id: str, spec: TraitSpec
    ) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._spec = spec
        self._attr_translation_key = slug(spec.trait)
        self._attr_unique_id = f"{cloud_device_id}_{spec.msg_key}"

    @property
    def native_value(self) -> Any:
        value = self._state.get(self._spec.msg_key)
        if isinstance(value, dict):
            # objects are shown through the attributes, keep the state short
            if len(value) == 1:
                return next(iter(value.values()))
            return "ok" if value else None
        if isinstance(value, bool):
            return "on" if value else "off"
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        value = self._state.get(self._spec.msg_key)
        if isinstance(value, dict):
            return dict(value)
        return {}


class JuwelPresetSensor(JuwelEntity, SensorEntity):
    """Aktives Beleuchtungsprofil; liefert die Tageskurve als Attribut."""

    _attr_translation_key = "preset"
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
            # Geschwister-Entitäten, damit die Karte sie sprachunabhängig findet
            **self._related_entities(),
        }

    def _related_entities(self) -> dict[str, Any]:
        """Entity-IDs der übrigen Entitäten dieses Geräts (über die unique_ids)."""
        try:
            reg = er.async_get(self.hass)
        except Exception:  # noqa: BLE001
            return {}

        def find(domain: str, suffix: str) -> str | None:
            return reg.async_get_entity_id(domain, DOMAIN, f"{self._cid}_{suffix}")

        channels = {
            ch: find("number", ch) for ch in ("white", "red", "green", "blue")
        }
        return {
            "light_entity": find("light", "light"),
            "auto_switch_entity": find("switch", "auto"),
            "channel_entities": {k: v for k, v in channels.items() if v},
        }
