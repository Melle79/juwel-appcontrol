"""Licht-Entity für die Juwel HeliaLux AppControl."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGBW_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JuwelCoordinator
from .entity import JuwelEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JuwelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(JuwelLight(coordinator, cid) for cid in coordinator.data)


def _pct_to_255(pct: int) -> int:
    return max(0, min(255, round(pct * 255 / 100)))


def _255_to_pct(val: int) -> int:
    return max(0, min(100, round(val * 100 / 255)))


class JuwelLight(JuwelEntity, LightEntity):
    """Aquarienlicht: Helligkeit + WRGB (Weiß-Kanal über RGBW)."""

    _attr_name = None  # nutzt den Gerätenamen
    _attr_color_mode = ColorMode.RGBW
    _attr_supported_color_modes = {ColorMode.RGBW}

    def __init__(self, coordinator: JuwelCoordinator, cloud_device_id: str) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._attr_unique_id = f"{cloud_device_id}_light"

    @property
    def is_on(self) -> bool:
        return self._state.get("status") == "on"

    @property
    def brightness(self) -> int | None:
        pct = (self._state.get("brightness") or {}).get("percentage")
        return _pct_to_255(pct) if pct is not None else None

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        color = self._state.get("color") or {}
        white = (self._state.get("white") or {}).get("value", 0)
        if not color:
            return None
        return (
            int(color.get("red", 0)),
            int(color.get("green", 0)),
            int(color.get("blue", 0)),
            int(white),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "mode": self._state.get("mode"),
            "active_preset": self._state.get("active_preset"),
            "preview": self._state.get("preview"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        mode = self._state.get("mode")
        brightness_pct = None
        rgb = None
        white = None

        if ATTR_BRIGHTNESS in kwargs:
            brightness_pct = max(1, _255_to_pct(kwargs[ATTR_BRIGHTNESS]))
        if ATTR_RGBW_COLOR in kwargs:
            r, g, b, w = kwargs[ATTR_RGBW_COLOR]
            rgb = (r, g, b)
            white = w

        await self.coordinator.client.set_manual(
            self._cid,
            current_mode=mode,
            status="on",
            brightness_pct=brightness_pct,
            rgb=rgb,
            white=white,
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.set_manual(
            self._cid, current_mode=self._state.get("mode"), status="off"
        )
        await self.coordinator.async_request_refresh()
