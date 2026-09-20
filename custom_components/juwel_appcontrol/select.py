"""Selects: profile per weekday and enum traits (e.g. operating mode)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import JuwelCoordinator
from .entity import JuwelEntity
from .traits import T_MODE, TraitSpec, slug

_LOGGER = logging.getLogger(__name__)

# The command counts 0 = Sunday .. 6 = Saturday
WEEKDAY_TO_COMMAND = {
    "sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3,
    "thursday": 4, "friday": 5, "saturday": 6,
}
WEEKDAY_CHOICES = ["today", "all", *WEEKDAY_TO_COMMAND]

SERVICE_SET_PROFILE = "set_profile"

SELECT_TRAITS = (T_MODE,)

ICONS = {T_MODE: "mdi:auto-mode"}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JuwelCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []

    for cid, data in coordinator.data.items():
        if data.get("is_light"):
            entities.append(JuwelPresetSelect(coordinator, cid))
            continue  # lights use the dedicated schedule switch
        traits: dict[str, TraitSpec] = data.get("traits") or {}
        for trait_id in SELECT_TRAITS:
            spec = traits.get(trait_id)
            if spec and spec.enum:
                entities.append(JuwelTraitSelect(coordinator, cid, spec))

    async_add_entities(entities)

    entity_platform.async_get_current_platform().async_register_entity_service(
        SERVICE_SET_PROFILE,
        {
            vol.Required("profile"): cv.string,
            vol.Optional("weekday", default="today"): vol.In(WEEKDAY_CHOICES),
        },
        "async_set_profile",
    )


class JuwelTraitSelect(JuwelEntity, SelectEntity):
    """An enum trait exposed as a dropdown."""

    def __init__(
        self, coordinator: JuwelCoordinator, cloud_device_id: str, spec: TraitSpec
    ) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._spec = spec
        self._attr_options = [str(v) for v in (spec.enum or [])]
        self._attr_translation_key = slug(spec.trait)
        self._attr_icon = ICONS.get(spec.trait)
        self._attr_unique_id = f"{cloud_device_id}_{spec.msg_key}"

    @property
    def current_option(self) -> str | None:
        value = self._optimistic(self._state.get(self._spec.msg_key))
        return str(value) if value is not None else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.client.set_trait(self._cid, self._spec.msg_key, option)
        self._note_write(option)


class JuwelPresetSelect(JuwelEntity, SelectEntity):
    """The lighting profile used *today*.

    The lamp holds three profiles in slots and assigns one to every weekday.
    Selecting here changes **today only** — exactly what the app's "activate"
    button does; the weekly assignment lives in the app's weekly planner and
    is left untouched. The full week is visible on the profile sensor.

        {"type": "preset", "action": "set", "id": <slot>, "dayOfWeek": <0-6>}

    Two different weekday numberings, both verified on hardware: the command
    counts 0 = Sunday .. 6 = Saturday, while the state array
    `preset_id_by_weekday` starts at Monday.

    The device confirms at once but reports the new state only about a minute
    later, so the chosen value is shown optimistically meanwhile.
    """

    _attr_translation_key = "preset"
    _attr_icon = "mdi:palette-swatch"
    PENDING_TTL = 180.0
    REFRESH_DELAYS = (10, 30, 50, 75)

    def __init__(self, coordinator: JuwelCoordinator, cloud_device_id: str) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._attr_unique_id = f"{cloud_device_id}_preset_select"

    def _slot_names(self) -> dict[int, str]:
        """slot -> profile name, resolved through presetSlotInfo and /presets."""
        data = self.coordinator.data.get(self._cid, {})
        info = data.get("info") or {}
        from .sensor import pretty_preset_name

        id_to_name = {str(p.get("id")): p.get("name") for p in data.get("presets") or []}
        names: dict[int, str] = {}
        for entry in info.get("presetSlotInfo") or []:
            slot = entry.get("slotId")
            if slot is None:
                continue
            resolved = id_to_name.get(str(entry.get("presetId")))
            names[slot] = pretty_preset_name(resolved) if resolved else f"Slot {slot}"
        return names

    @property
    def options(self) -> list[str]:
        return list(self._slot_names().values())

    @property
    def current_option(self) -> str | None:
        slot = self._optimistic(self._state.get("active_preset"))
        return self._slot_names().get(slot)

    async def async_select_option(self, option: str) -> None:
        slot = next(
            (s for s, name in self._slot_names().items() if name == option), None
        )
        if slot is None:
            return
        # Nur heute, wie der "Aktivieren"-Knopf der App.
        # Befehl zaehlt 0 = Sonntag, Python 0 = Montag.
        day_of_week = (dt_util.now().weekday() + 1) % 7
        await self.coordinator.client.set_preset_for_weekday(
            self._cid, slot, day_of_week
        )
        self._note_write(slot)

    # ---- Aktion: Profil fuer einen bestimmten Wochentag ----------------

    def _days_for(self, weekday: str) -> list[int]:
        """Wochentag(e) in die Zaehlweise des Befehls uebersetzen."""
        if weekday == "today":
            return [(dt_util.now().weekday() + 1) % 7]
        if weekday == "all":
            return list(range(7))
        return [WEEKDAY_TO_COMMAND[weekday]]

    def _applied_days(self) -> dict[int, int]:
        """Aktuell zugewiesener Slot je Befehls-Wochentag."""
        week = self._state.get("preset_id_by_weekday")
        if not isinstance(week, list) or len(week) != 7:
            return {}
        # Array beginnt bei Montag, der Befehl bei Sonntag
        return {(i + 1) % 7: slot for i, slot in enumerate(week)}

    async def async_set_profile(self, profile: str, weekday: str = "today") -> None:
        """Ein Profil einem oder allen Wochentagen zuweisen.

        Das Geraet verarbeitet Profilbefehle einzeln und braucht dafuer Zeit;
        mehrere schnell hintereinander gehen verloren. Deshalb mit Abstand
        senden, danach pruefen und Fehlende einmal nachreichen.
        """
        slot = next(
            (s for s, name in self._slot_names().items() if name == profile), None
        )
        if slot is None:
            raise ValueError(
                f"Unknown profile {profile!r}. Available: {', '.join(self.options)}"
            )

        days = self._days_for(weekday)
        for attempt in (1, 2):
            for day in days:
                await self.coordinator.client.set_preset_for_weekday(
                    self._cid, slot, day
                )
                if len(days) > 1:
                    await asyncio.sleep(6)
            if len(days) == 1:
                break
            await asyncio.sleep(20)
            await self.coordinator.async_request_refresh()
            missing = [d for d, s_ in self._applied_days().items()
                       if d in days and s_ != slot]
            if not missing:
                break
            _LOGGER.debug("Profil fehlte noch an Tagen %s, zweiter Versuch", missing)
            days = missing
        else:
            _LOGGER.warning(
                "Profil %s konnte nicht allen Wochentagen zugewiesen werden", profile
            )

        self._note_write(slot)
