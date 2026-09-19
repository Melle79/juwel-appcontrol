"""Selects: enum traits with more than two options (e.g. operating mode)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JuwelCoordinator
from .entity import JuwelEntity
from .traits import T_MODE, TraitSpec, slug

SELECT_TRAITS = (T_MODE,)

ICONS = {T_MODE: "mdi:auto-mode"}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JuwelCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SelectEntity] = []

    for cid, data in coordinator.data.items():
        if data.get("is_light"):
            continue  # lights use the dedicated schedule switch
        traits: dict[str, TraitSpec] = data.get("traits") or {}
        for trait_id in SELECT_TRAITS:
            spec = traits.get(trait_id)
            if spec and spec.enum:
                entities.append(JuwelTraitSelect(coordinator, cid, spec))

    async_add_entities(entities)


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
