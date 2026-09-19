"""Basis-Entity mit Geräteinfo für die Juwel HeliaLux Integration."""
from __future__ import annotations

import time
from typing import Any

from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.device_registry import (
    CONNECTION_NETWORK_MAC,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JuwelCoordinator


class JuwelEntity(CoordinatorEntity[JuwelCoordinator]):
    """Gemeinsame Basis für alle Entities eines Geräts."""

    _attr_has_entity_name = True

    # Wie lange ein selbst geschriebener Wert angezeigt wird, bis das Geraet
    # ihn bestaetigt hat.
    PENDING_TTL = 45.0
    # Nach einem Schreibvorgang wird zu diesen Zeitpunkten nachgefragt.
    REFRESH_DELAYS = (3, 8, 20)

    def __init__(self, coordinator: JuwelCoordinator, cloud_device_id: str) -> None:
        super().__init__(coordinator)
        self._cid = cloud_device_id
        self._pending: Any = None
        self._pending_until = 0.0

    def _optimistic(self, actual: Any) -> Any:
        """Zeigt den gerade geschriebenen Wert, bis das Geraet ihn meldet.

        Die Geraete bestaetigen asynchron; ohne das wuerde ein Schalter nach
        dem Umlegen kurz zurueckspringen.
        """
        if self._pending is None:
            return actual
        if actual == self._pending or time.monotonic() > self._pending_until:
            self._pending = None
            return actual
        return self._pending

    def _note_write(self, value: Any) -> None:
        """Wert vormerken und gestaffelt nachfragen, statt sofort (zu frueh)."""
        self._pending = value
        self._pending_until = time.monotonic() + self.PENDING_TTL
        self.async_write_ha_state()

        def _later(_now: Any) -> None:
            self.hass.async_create_task(self.coordinator.async_request_refresh())

        for delay in self.REFRESH_DELAYS:
            async_call_later(self.hass, delay, _later)

    @property
    def _device(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._cid, {}).get("info", {})

    @property
    def _state(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._cid, {}).get("state", {})

    @property
    def device_info(self) -> DeviceInfo:
        info = self._device
        connections = set()
        if mac := info.get("localDeviceId"):
            connections = {(CONNECTION_NETWORK_MAC, format_mac(mac))}
        return DeviceInfo(
            identifiers={(DOMAIN, self._cid)},
            name=info.get("name", "HeliaLux"),
            manufacturer="Juwel",
            model=info.get("productId", "HeliaLux AppControl"),
            sw_version=info.get("firmwareVersion"),
            connections=connections,
        )

    @property
    def available(self) -> bool:
        return super().available and bool(self._state.get("connected", True))
