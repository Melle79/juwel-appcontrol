"""Switches: automatic schedule (lights) and boolean/enum traits."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JuwelCoordinator
from .entity import JuwelEntity
from .traits import (
    T_LED_SWITCH,
    T_POWER,
    T_POWER_LIMIT,
    T_SMART_FEED,
    T_STATUS,
    TraitSpec,
    slug,
)

# Traits that become a plain on/off switch on non-light devices
SWITCH_TRAITS = (T_STATUS, T_POWER, T_LED_SWITCH, T_SMART_FEED, T_POWER_LIMIT)

ICONS = {
    T_STATUS: "mdi:power",
    T_POWER: "mdi:power",
    T_LED_SWITCH: "mdi:led-on",
    T_SMART_FEED: "mdi:fish",
    T_POWER_LIMIT: "mdi:speedometer-slow",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JuwelCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SwitchEntity] = []

    for cid, data in coordinator.data.items():
        # The lights keep their dedicated schedule switch
        if data.get("is_light"):
            entities.append(JuwelAutoSwitch(coordinator, cid))
            continue
        traits: dict[str, TraitSpec] = data.get("traits") or {}
        for trait_id in SWITCH_TRAITS:
            spec = traits.get(trait_id)
            if spec and (spec.enum is not None or spec.is_boolean):
                entities.append(JuwelTraitSwitch(coordinator, cid, spec))

    async_add_entities(entities)


class JuwelAutoSwitch(JuwelEntity, SwitchEntity):
    """Automatic schedule on/off (HeliaLux)."""

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


class JuwelTraitSwitch(JuwelEntity, SwitchEntity):
    """A trait that is either on/off or 0/1 or a boolean."""

    def __init__(
        self, coordinator: JuwelCoordinator, cloud_device_id: str, spec: TraitSpec
    ) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._spec = spec
        self._attr_translation_key = slug(spec.trait)
        self._attr_icon = ICONS.get(spec.trait)
        self._attr_unique_id = f"{cloud_device_id}_{spec.msg_key}"

    def _on_off_values(self) -> tuple[Any, Any]:
        """Return the (on, off) representation this trait expects."""
        if self._spec.is_boolean:
            return True, False
        enum = self._spec.enum or ["on", "off"]
        if set(enum) == {0, 1}:
            return 1, 0
        return ("on", "off") if "on" in enum else (enum[0], enum[-1])

    @property
    def is_on(self) -> bool | None:
        value = self._state.get(self._spec.msg_key)
        if value is None:
            return None
        on_value, _ = self._on_off_values()
        return value == on_value

    async def _set(self, on: bool) -> None:
        on_value, off_value = self._on_off_values()
        await self.coordinator.client.set_trait(
            self._cid, self._spec.msg_key, on_value if on else off_value
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)
