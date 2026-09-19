"""Binary sensors for fields the product catalogue does not declare.

The SmartFeed reports `feed_chamber_status`, `feed_motor_status` and `error`
in its state although no trait mentions them. They matter most on a feeder, so
they get first-class entities.

Verified on real hardware: an empty chamber reports `feed_chamber_status = 0`,
which matches the app's own FeedChamberStatus enum (EMPTY / ENOUGH).
"""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import JuwelCoordinator
from .entity import JuwelEntity
from .traits import device_type


@dataclass(frozen=True)
class ProblemDesc:
    key: str                              # field in the device state
    translation_key: str
    icon: str
    is_problem: Callable[[Any], bool]


PROBLEMS: tuple[ProblemDesc, ...] = (
    # Verified: 0 = empty, 1 = enough
    ProblemDesc("feed_chamber_status", "feed_chamber_empty", "mdi:cup-off-outline",
                lambda v: v == 0),
    # The device's own error channel. Verified: it fills with a message when a
    # command is rejected and clears itself afterwards.
    ProblemDesc("error", "device_error", "mdi:alert-circle-outline",
                lambda v: bool(v)),
)

# feed_motor_status is NOT a fault indicator: a value of 2 was observed while
# the motor was running normally. It is exposed as a plain sensor instead.
MOTOR_STATES = {0: "idle", 2: "running"}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JuwelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        JuwelProblemSensor(coordinator, cid, desc)
        for cid, data in coordinator.data.items()
        for desc in PROBLEMS
        # Felder erscheinen teils erst nach der ersten Nutzung -> Typ pruefen
        if desc.key in (data.get("state") or {})
        or (device_type(data) == "feeder" and desc.key.startswith("feed_"))
    )


class JuwelProblemSensor(JuwelEntity, BinarySensorEntity):
    """Reports a device problem (empty chamber, motor fault, error list)."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self, coordinator: JuwelCoordinator, cloud_device_id: str, desc: ProblemDesc
    ) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._desc = desc
        self._attr_translation_key = desc.translation_key
        self._attr_icon = desc.icon
        self._attr_unique_id = f"{cloud_device_id}_{desc.key}"

    @property
    def is_on(self) -> bool | None:
        if self._desc.key not in self._state:
            return None
        return self._desc.is_problem(self._state.get(self._desc.key))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        value = self._state.get(self._desc.key)
        return {"raw": value} if value is not None else {}
