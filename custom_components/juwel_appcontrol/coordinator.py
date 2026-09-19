"""DataUpdateCoordinator für die Juwel HeliaLux Cloud-Integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JuwelApiError, JuwelAuthError, JuwelCloud
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LIGHT_PRODUCT_IDS

_LOGGER = logging.getLogger(__name__)


class JuwelCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Holt Geräteliste + Zustände regelmäßig aus der Cloud."""

    def __init__(self, hass: HomeAssistant, client: JuwelCloud) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.client = client
        self.devices: dict[str, dict[str, Any]] = {}

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            settings = await self.client.get_settings()
        except JuwelAuthError as err:
            raise UpdateFailed(f"Anmeldung ungültig: {err}") from err
        except JuwelApiError as err:
            raise UpdateFailed(str(err)) from err

        # Profile (Tageskurven) – ohne sie funktioniert der Rest trotzdem
        try:
            presets = await self.client.get_presets()
        except JuwelApiError as err:
            _LOGGER.debug("Profile nicht abrufbar: %s", err)
            presets = []

        result: dict[str, dict[str, Any]] = {}
        for dev in settings.get("devices", []):
            if dev.get("productId") not in LIGHT_PRODUCT_IDS:
                continue
            cid = dev.get("cloudDeviceId")
            if not cid:
                continue
            self.devices[cid] = dev
            try:
                state = await self.client.get_state(cid)
            except JuwelApiError as err:
                _LOGGER.warning("Zustand von %s nicht abrufbar: %s", dev.get("name"), err)
                state = {"connected": False}
            result[cid] = {
                "info": dev,
                "state": state,
                "presets": presets,
                "active_preset": _active_preset(dev, state, presets),
            }
        return result


def _active_preset(
    info: dict[str, Any], state: dict[str, Any], presets: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """Aktives Profil ermitteln: active_preset (Slot) -> presetId -> /presets."""
    slot = state.get("active_preset")
    if slot is None:
        return None
    preset_id = None
    for entry in info.get("presetSlotInfo") or []:
        if entry.get("slotId") == slot:
            preset_id = str(entry.get("presetId"))
            break
    if preset_id is None:
        return None
    for preset in presets:
        if str(preset.get("id")) == preset_id:
            return preset
    return None
