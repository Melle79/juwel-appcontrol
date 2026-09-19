"""Mapping of qconnex device traits to Home Assistant entities.

The cloud describes every product through `/config/product/{productId}`:
each trait carries a `msg_key` (the key used in the device state and in
commands) and a `value_schema`.

Reading  : GET  /device/{id}/state   -> {msg_key: value, ...}
Writing  : POST /device/{id}/state   -> {"payload": {"type": "request", msg_key: value}}

Writable controls are only created where the schema defines a clear domain
(an enum or min/max). Everything else is exposed read-only, so we never send
a value we cannot validate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# --- Trait IDs -------------------------------------------------------------

T_STATUS = "@core/traits/status"
T_BRIGHTNESS = "@core/traits/brightness"
T_COLOR = "@core/traits/color"
T_WHITE = "@core/traits/white"
T_COLOR_MODE = "@core/traits/color-mode"
T_CONNECTIVITY = "@core/traits/connectivity"

T_FEED = "@core/traits/feed"
T_FEED_QUANTITY = "@core/traits/feed-quantity"
T_FEED_KEY_QUANTITY = "@core/traits/feed-key-quantity"
T_LED_SWITCH = "@core/traits/led-switch"

T_POWER = "@core/traits/power"
T_MODE = "@core/traits/mode"
T_SMART_FEED = "@core/traits/smart-feed"
T_POWER_LIMIT = "@core/traits/power-limit"
T_TIMER_RESET = "@core/traits/timer-reset"

# Traits handled by the light entity – no separate entities for them
LIGHT_TRAITS = {T_STATUS, T_BRIGHTNESS, T_COLOR, T_WHITE, T_COLOR_MODE}

# Never gets an entity of its own (drives availability instead)
SKIP_TRAITS = {T_CONNECTIVITY}


@dataclass(frozen=True)
class TraitSpec:
    """A single trait of a concrete device."""

    trait: str
    msg_key: str
    schema: dict[str, Any] = field(default_factory=dict)

    # -- schema helpers ----------------------------------------------------

    @property
    def is_object(self) -> bool:
        return self.schema.get("type") == "object"

    @property
    def enum(self) -> list[Any] | None:
        return self.schema.get("enum")

    @property
    def properties(self) -> dict[str, Any]:
        return self.schema.get("properties") or {}

    def numeric_property(self) -> tuple[str, float, float] | None:
        """Return (property, min, max) if the trait is a single bounded number."""
        props = self.properties
        if len(props) != 1:
            return None
        name, spec = next(iter(props.items()))
        if spec.get("type") not in ("integer", "number"):
            return None
        if "minimum" not in spec or "maximum" not in spec:
            return None
        return name, float(spec["minimum"]), float(spec["maximum"])

    @property
    def is_boolean(self) -> bool:
        return self.schema.get("type") == "boolean"


def parse_traits(product_config: dict[str, Any] | None) -> dict[str, TraitSpec]:
    """Build {trait_id: TraitSpec} from a product configuration."""
    specs: dict[str, TraitSpec] = {}
    for entry in (product_config or {}).get("deviceTraits") or []:
        trait = entry.get("trait")
        msg_key = entry.get("msg_key")
        if not trait or not msg_key:
            continue
        specs[trait] = TraitSpec(trait, msg_key, entry.get("value_schema") or {})
    return specs


def slug(trait: str) -> str:
    """'@core/traits/feed-quantity' -> 'feed_quantity' (used as translation key)."""
    return trait.rsplit("/", 1)[-1].replace("-", "_")
