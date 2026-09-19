"""Einzelne Farbkanäle (W/R/G/B) als Prozent-Regler."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JuwelCoordinator
from .entity import JuwelEntity


@dataclass(frozen=True)
class ChannelDesc:
    key: str          # Kanal im Geraetezustand
    icon: str


CHANNELS: tuple[ChannelDesc, ...] = (
    ChannelDesc("white", "mdi:brightness-7"),
    ChannelDesc("red", "mdi:palette"),
    ChannelDesc("green", "mdi:palette"),
    ChannelDesc("blue", "mdi:palette"),
)


def _raw_to_pct(raw: int) -> int:
    return max(0, min(100, round(raw * 100 / 255)))


def _pct_to_raw(pct: float) -> int:
    return max(0, min(255, round(pct * 255 / 100)))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JuwelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        JuwelChannelNumber(coordinator, cid, ch)
        for cid in coordinator.data
        for ch in CHANNELS
    )


class JuwelChannelNumber(JuwelEntity, NumberEntity):
    """Ein Farbkanal in Prozent (0–100)."""

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self, coordinator: JuwelCoordinator, cloud_device_id: str, channel: ChannelDesc
    ) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._ch = channel
        self._attr_translation_key = channel.key
        self._attr_icon = channel.icon
        self._attr_unique_id = f"{cloud_device_id}_{channel.key}"

    def _raw(self, key: str) -> int:
        if key == "white":
            return int((self._state.get("white") or {}).get("value", 0))
        return int((self._state.get("color") or {}).get(key, 0))

    @property
    def native_value(self) -> float | None:
        if not self._state:
            return None
        return _raw_to_pct(self._raw(self._ch.key))

    async def async_set_native_value(self, value: float) -> None:
        raw = _pct_to_raw(value)
        kwargs: dict[str, Any] = {}
        if self._ch.key == "white":
            kwargs["white"] = raw
        else:
            # Farbe muss komplett gesendet werden -> andere Kanäle beibehalten
            rgb = {k: self._raw(k) for k in ("red", "green", "blue")}
            rgb[self._ch.key] = raw
            kwargs["rgb"] = (rgb["red"], rgb["green"], rgb["blue"])

        await self.coordinator.client.set_manual(
            self._cid, current_mode=self._state.get("mode"), **kwargs
        )
        await self.coordinator.async_request_refresh()
