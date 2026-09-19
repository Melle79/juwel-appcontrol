"""Basis-Entity mit Geräteinfo für die Juwel HeliaLux Integration."""
from __future__ import annotations

from typing import Any

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

    def __init__(self, coordinator: JuwelCoordinator, cloud_device_id: str) -> None:
        super().__init__(coordinator)
        self._cid = cloud_device_id

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
