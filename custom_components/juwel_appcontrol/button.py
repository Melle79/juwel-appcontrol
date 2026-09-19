"""Buttons: feed now, timer resets."""
from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JuwelCoordinator
from .entity import JuwelEntity
from .traits import T_FEED, T_FEED_QUANTITY, T_TIMER_RESET, TraitSpec


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JuwelCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[ButtonEntity] = []

    for cid, data in coordinator.data.items():
        traits: dict[str, TraitSpec] = data.get("traits") or {}

        if (feed := traits.get(T_FEED)) is not None:
            entities.append(JuwelFeedButton(coordinator, cid, feed, traits.get(T_FEED_QUANTITY)))

        reset = traits.get(T_TIMER_RESET)
        if reset is not None:
            for option in _enum_options(reset):
                entities.append(JuwelResetButton(coordinator, cid, reset, option))

    async_add_entities(entities)


def _enum_options(spec: TraitSpec) -> list[str]:
    """Enum values of a trait, whether declared directly or inside a property."""
    if spec.enum:
        return [str(v) for v in spec.enum]
    for prop in spec.properties.values():
        if prop.get("enum"):
            return [str(v) for v in prop["enum"]]
    return []


class JuwelFeedButton(JuwelEntity, ButtonEntity):
    """Feed now – uses the configured feed quantity as the amount."""

    _attr_translation_key = "feed_now"
    _attr_icon = "mdi:food-drumstick"

    def __init__(
        self,
        coordinator: JuwelCoordinator,
        cloud_device_id: str,
        spec: TraitSpec,
        quantity: TraitSpec | None,
    ) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._spec = spec
        self._quantity = quantity
        self._attr_unique_id = f"{cloud_device_id}_feed_now"

    def _amount(self) -> int:
        """Configured quantity, otherwise the smallest valid amount."""
        if self._quantity:
            value = self._state.get(self._quantity.msg_key)
            if isinstance(value, dict):
                value = next(iter(value.values()), None)
            try:
                return int(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                pass
        prop = self._spec.numeric_property()
        return int(prop[1]) if prop else 1

    async def async_press(self) -> None:
        prop = self._spec.numeric_property()
        key = prop[0] if prop else "feed"
        await self.coordinator.client.set_trait(
            self._cid, self._spec.msg_key, {key: self._amount()}
        )
        await self.coordinator.async_request_refresh()


class JuwelResetButton(JuwelEntity, ButtonEntity):
    """Reset a maintenance timer (clean_pump / impeller / all)."""

    _attr_icon = "mdi:restart"

    def __init__(
        self,
        coordinator: JuwelCoordinator,
        cloud_device_id: str,
        spec: TraitSpec,
        option: str,
    ) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._spec = spec
        self._option = option
        self._attr_translation_key = f"timer_reset_{option}"
        self._attr_unique_id = f"{cloud_device_id}_{spec.msg_key}_{option}"

    async def async_press(self) -> None:
        value: Any = self._option
        if self._spec.properties:
            prop = next(iter(self._spec.properties))
            value = {prop: self._option}
        await self.coordinator.client.set_trait(self._cid, self._spec.msg_key, value)
        await self.coordinator.async_request_refresh()
