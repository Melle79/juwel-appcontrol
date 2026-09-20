"""Profil-Sensor: aktives Profil + Tageskurve als Attribut (für die Karte)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
import voluptuous as vol

from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import JuwelCoordinator
from .entity import JuwelEntity
from .traits import LIGHT_TRAITS, SKIP_TRAITS, TraitSpec, device_type, slug


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: JuwelCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for cid, data in coordinator.data.items():
        if data.get("is_light"):
            entities.append(JuwelPresetSensor(coordinator, cid))

        # Everything without a safe control becomes read-only, so nothing is lost
        traits: dict[str, TraitSpec] = data.get("traits") or {}
        for spec in traits.values():
            if spec.trait in SKIP_TRAITS:
                continue
            if data.get("is_light") and spec.trait in LIGHT_TRAITS:
                continue
            if _has_control(spec, data):
                continue
            entities.append(JuwelTraitSensor(coordinator, cid, spec))

        # Diese Felder tauchen im Geraetezustand erst nach der ersten Nutzung
        # auf - deshalb am Geraetetyp festmachen, nicht am aktuellen Zustand.
        if device_type(data) == "feeder":
            entities.append(JuwelMotorSensor(coordinator, cid))
            entities.append(JuwelLastFeedSensor(coordinator, cid))
            entities.append(JuwelFeedPlanSensor(coordinator, cid))

    async_add_entities(entities)

    entity_platform.async_get_current_platform().async_register_entity_service(
        "set_feeding_plan",
        {
            vol.Optional("weekdays"): vol.All(
                cv.ensure_list, [vol.In(list(WEEKDAY_TO_NUMBER) + ["all"])]
            ),
            vol.Optional("feedings"): vol.All(
                cv.ensure_list,
                [vol.Schema({
                    vol.Required("time"): cv.string,
                    vol.Optional("amount", default=1): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=8)
                    ),
                })],
            ),
        },
        "async_set_feeding_plan",
    )


# commandInterval zaehlt wie die Geraetebefehle: 0 = Sonntag .. 6 = Samstag
WEEKDAY_TO_NUMBER = {
    "sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3,
    "thursday": 4, "friday": 5, "saturday": 6,
}


def _has_control(spec: TraitSpec, data: dict[str, Any]) -> bool:
    """True if another platform already exposes this trait as a control."""
    from .button import _enum_options
    from .select import SELECT_TRAITS
    from .switch import SWITCH_TRAITS
    from .traits import T_FEED, T_TIMER_RESET

    if spec.trait in (T_FEED, T_TIMER_RESET):
        return True
    if spec.trait in SELECT_TRAITS and spec.enum:
        return True
    if spec.trait in SWITCH_TRAITS and (spec.enum is not None or spec.is_boolean):
        return True
    if spec.numeric_property():
        return True
    return False


# Weekday numbering confirmed on hardware: a plan for Monday/Thursday/Saturday
# is stored as "1,4,6", so 0 = Sunday ... 6 = Saturday.
WEEKDAY_NAMES = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


def _weekdays(raw: str) -> tuple[list[int], str]:
    """Parse the weekday field of commandInterval ("*" or e.g. "1,4,6")."""
    raw = (raw or "").strip()
    if not raw or raw == "*":
        return list(range(7)), "every day"
    days: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 0 <= int(part) <= 6:
            days.append(int(part))
    return days, ", ".join(WEEKDAY_NAMES[d] for d in days)


class _FeedPlanMixin:
    """Schreiben des Futterplans - am Plan-Sensor angesiedelt."""

    # Womit ein neu angelegter Plan startet, falls das Geraet auf einen
    # Plan zeigt, den es in der Cloud nicht mehr gibt.
    NEW_PLAN_NAME = "Home Assistant"
    NEW_PLAN_COLOR = "#B5D4E3"

    @staticmethod
    def _interval(weekdays: list[str]) -> str:
        """Wochentage in die commandInterval-Schreibweise bringen."""
        if "all" in weekdays:
            return "* * *;"
        nums = sorted({WEEKDAY_TO_NUMBER[d] for d in weekdays})
        return "* * " + ",".join(str(n) for n in nums) + ";"

    @staticmethod
    def _events(feedings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fuetterungen in timeEvents umrechnen: Minuten ab Mitternacht."""
        events = []
        for index, item in enumerate(feedings):
            hours, _, minutes = str(item["time"])[:5].partition(":")
            try:
                total = int(hours) * 60 + int(minutes)
            except ValueError as err:
                raise ValueError(
                    f"Invalid time {item['time']!r}, expected HH:MM"
                ) from err
            if not 0 <= total < 24 * 60:
                raise ValueError(f"Time {item['time']!r} is outside a day")
            events.append(
                {"id": 200 + index, "time": total,
                 "value": {"amount": int(item.get("amount", 1))}}
            )
        events.sort(key=lambda event: event["time"])
        return events

    async def async_set_feeding_plan(
        self, weekdays: list[str] | None = None,
        feedings: list[dict[str, Any]] | None = None,
    ) -> None:
        """Futterplan schreiben - vorhandenen aendern oder einen anlegen."""
        client = self.coordinator.client
        presets = await client.get_feeder_presets()

        data = self.coordinator.data.get(self._cid, {})
        wanted = (data.get("info") or {}).get("fishFeederPresetIdList") or []
        by_id = {str(p.get("id")): p for p in presets}
        target = next((by_id[str(pid)] for pid in wanted if str(pid) in by_id), None)

        if target is None:
            # Das Geraet verweist auf einen Plan, den die Cloud nicht (mehr)
            # fuehrt. Unter genau dieser Kennung einen neuen anlegen, sonst
            # bliebe der Verweis ins Leere zeigen.
            if not wanted:
                raise ValueError("This feeder has no feeding plan assigned")
            if not weekdays or not feedings:
                raise ValueError(
                    "There is no feeding plan yet - please pass both weekdays "
                    "and feedings so a new one can be created"
                )
            target = {
                "id": str(wanted[0]),
                "name": self.NEW_PLAN_NAME,
                "type": "user",
                "color": self.NEW_PLAN_COLOR,
                "timeEvents": [],
                "commandInterval": "* * *;",
            }
            presets.append(target)

        if weekdays:
            target["commandInterval"] = self._interval(weekdays)
        if feedings:
            target["timeEvents"] = self._events(feedings)

        await client.save_feeder_preset(target)
        await self.coordinator.async_request_refresh()


class JuwelFeedPlanSensor(_FeedPlanMixin, JuwelEntity, SensorEntity):
    """The feeding plan assigned to this feeder.

    Structure verified on hardware:
        {"id": "...", "name": "Täglich füttern 1", "type": "user",
         "timeEvents": [{"time": 1080, "value": {"amount": 1}}],
         "commandInterval": "* * 1,4,6;"}
    `time` is minutes since midnight, `amount` the feed quantity, and the last
    field of `commandInterval` lists the weekdays ("*" = every day).
    """

    _attr_translation_key = "feed_plan"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: JuwelCoordinator, cloud_device_id: str) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._attr_unique_id = f"{cloud_device_id}_feed_plan"

    @property
    def _plan(self) -> dict[str, Any] | None:
        data = self.coordinator.data.get(self._cid, {})
        wanted = (data.get("info") or {}).get("fishFeederPresetIdList") or []
        presets = data.get("feeder_presets") or []
        for pid in wanted:
            for preset in presets:
                if str(preset.get("id")) == str(pid):
                    return preset
        return None

    @property
    def native_value(self) -> str | None:
        plan = self._plan
        if plan:
            return plan.get("name")
        return "none"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        plan = self._plan
        if not plan:
            return self._related_feeder_entities()
        feedings = []
        for ev in plan.get("timeEvents") or []:
            minutes = ev.get("time")
            amount = (ev.get("value") or {}).get("amount")
            if minutes is None:
                continue
            feedings.append(
                {"time": f"{int(minutes) // 60:02d}:{int(minutes) % 60:02d}",
                 "minutes": minutes, "amount": amount}
            )
        feedings.sort(key=lambda f: f["minutes"])
        interval = str(plan.get("commandInterval") or "").strip().rstrip(";")
        raw_days = interval.split(" ")[-1] if interval else ""
        days, names = _weekdays(raw_days)
        return {
            "plan_id": plan.get("id"),
            "plan_type": plan.get("type"),
            "feedings": feedings,
            "feedings_per_day": len(feedings),
            "weekdays": days,
            "weekdays_text": names,
            "command_interval": plan.get("commandInterval"),
            **self._related_feeder_entities(),
        }

    def _related_feeder_entities(self) -> dict[str, Any]:
        """Entity-IDs des Geraets, damit die Karte sie ohne Namensraten findet."""
        try:
            reg = er.async_get(self.hass)
        except Exception:  # noqa: BLE001
            return {}

        def find(domain: str, suffix: str) -> str | None:
            return reg.async_get_entity_id(domain, DOMAIN, f"{self._cid}_{suffix}")

        related = {
            "feed_button": find("button", "feed_now"),
            "quantity_entity": find("number", "feed_quantity"),
            "key_quantity_entity": find("number", "feed_key_quantity"),
            "led_entity": find("switch", "led_switch"),
            "power_entity": find("switch", "status"),
            "chamber_entity": find("binary_sensor", "feed_chamber_status"),
            "error_entity": find("binary_sensor", "error"),
            "motor_entity": find("sensor", "feed_motor_state"),
            "last_feed_entity": find("sensor", "last_feed"),
        }
        return {k: v for k, v in related.items() if v}


class JuwelLastFeedSensor(JuwelEntity, SensorEntity):
    """Timestamp of the last feeding.

    Verified on hardware: `last_feed_ts` carries the unix time of the most
    recent feeding (manual or scheduled); 0 means "never".
    """

    _attr_translation_key = "last_feed"
    _attr_icon = "mdi:clock-check-outline"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: JuwelCoordinator, cloud_device_id: str) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._attr_unique_id = f"{cloud_device_id}_last_feed"

    @property
    def native_value(self) -> Any:
        ts = self._state.get("last_feed_ts")
        if not ts:
            return None
        return dt_util.utc_from_timestamp(int(ts))


class JuwelMotorSensor(JuwelEntity, SensorEntity):
    """Feed motor state. Verified on hardware: 0 = idle, 2 = running."""

    _attr_translation_key = "feed_motor_state"
    _attr_icon = "mdi:engine-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: JuwelCoordinator, cloud_device_id: str) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._attr_unique_id = f"{cloud_device_id}_feed_motor_state"

    @property
    def native_value(self) -> Any:
        from .binary_sensor import MOTOR_STATES
        raw = self._state.get("feed_motor_status")
        return MOTOR_STATES.get(raw, raw)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"raw": self._state.get("feed_motor_status")}


class JuwelTraitSensor(JuwelEntity, SensorEntity):
    """Read-only view of a trait we do not offer a control for (yet)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: JuwelCoordinator, cloud_device_id: str, spec: TraitSpec
    ) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._spec = spec
        self._attr_translation_key = slug(spec.trait)
        self._attr_unique_id = f"{cloud_device_id}_{spec.msg_key}"

    @property
    def native_value(self) -> Any:
        value = self._state.get(self._spec.msg_key)
        if isinstance(value, dict):
            # objects are shown through the attributes, keep the state short
            if len(value) == 1:
                return next(iter(value.values()))
            return "ok" if value else None
        if isinstance(value, bool):
            return "on" if value else "off"
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        value = self._state.get(self._spec.msg_key)
        if isinstance(value, dict):
            return dict(value)
        return {}


# Vendor presets carry internal keys; the app shows product names for them.
VENDOR_NAMES = {
    "standard": "Standard",
    "aquascape": "Aquascape",
    "ohne_mittagpause": "Standard without midday break",
    "malawi": "Malawi",
    "amazonas": "Amazonas",
    "amazons": "Amazonas",
    "feeder_daily": "Feed daily",
}


def pretty_preset_name(name: str | None) -> str:
    """Vendor key -> product name; user presets keep their own name."""
    if not name:
        return ""
    return VENDOR_NAMES.get(str(name).lower(), str(name))


class JuwelPresetSensor(JuwelEntity, SensorEntity):
    """Aktives Beleuchtungsprofil; liefert die Tageskurve als Attribut."""

    _attr_translation_key = "preset"
    _attr_icon = "mdi:chart-bell-curve-cumulative"

    def __init__(self, coordinator: JuwelCoordinator, cloud_device_id: str) -> None:
        super().__init__(coordinator, cloud_device_id)
        self._attr_unique_id = f"{cloud_device_id}_preset"

    @property
    def _preset(self) -> dict[str, Any] | None:
        return self.coordinator.data.get(self._cid, {}).get("active_preset")

    @property
    def native_value(self) -> str | None:
        preset = self._preset
        if preset:
            return pretty_preset_name(preset.get("name"))
        slot = self._state.get("active_preset")
        return f"Slot {slot}" if slot is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        preset = self._preset or {}
        # timeEvents: [{time: Minuten ab 0 Uhr, value: {red,green,blue,white} in %}]
        events = []
        for ev in preset.get("timeEvents") or []:
            val = ev.get("value") or {}
            events.append(
                {
                    "time": ev.get("time"),
                    "white": val.get("white", 0),
                    "red": val.get("red", 0),
                    "green": val.get("green", 0),
                    "blue": val.get("blue", 0),
                }
            )
        return {
            "preset_id": preset.get("id"),
            "preset_type": preset.get("type"),
            "preset_color": preset.get("color"),
            "time_events": events,
            "mode": self._state.get("mode"),
            "status": self._state.get("status"),
            "connected": self._state.get("connected"),
            **self._weekly_plan(),
            # Geschwister-Entitäten, damit die Karte sie sprachunabhängig findet
            **self._related_entities(),
        }

    def _weekly_plan(self) -> dict[str, Any]:
        """Welches Profil an welchem Wochentag laeuft.

        `preset_id_by_weekday` enthaelt je Wochentag den Slot; die Slots sind
        ueber `presetSlotInfo` den Profilen zugeordnet. Die Reihenfolge des
        Arrays wird zusaetzlich gegen `active_preset` geprueft, damit eine
        falsche Annahme sofort auffaellt statt still Unsinn zu liefern.
        """
        week = self._state.get("preset_id_by_weekday")
        if not isinstance(week, list) or len(week) != 7:
            return {}

        info = self.coordinator.data.get(self._cid, {}).get("info") or {}
        presets = self.coordinator.data.get(self._cid, {}).get("presets") or []
        slot_to_id = {
            e.get("slotId"): str(e.get("presetId"))
            for e in info.get("presetSlotInfo") or []
        }
        id_to_name = {str(p.get("id")): p.get("name") for p in presets}

        def name_of(slot: Any) -> str:
            resolved = id_to_name.get(slot_to_id.get(slot, ""))
            return pretty_preset_name(resolved) if resolved else f"Slot {slot}"

        # Array beginnt mit Montag; Gegenprobe ueber den heutigen Tag
        labels = ["monday", "tuesday", "wednesday", "thursday",
                  "friday", "saturday", "sunday"]
        today_index = dt_util.now().weekday()          # 0 = Montag
        matches = week[today_index] == self._state.get("active_preset")

        # Zur Fehlersuche: was die Cloud plant vs. was das Geraet meldet
        cloud_timeline = {}
        for entry in info.get("timeline") or []:
            day = entry.get("dayOfWeek")
            if day is None:
                continue
            resolved = id_to_name.get(str(entry.get("id")))
            cloud_timeline[str(day)] = (
                pretty_preset_name(resolved) if resolved else f"id {entry.get('id')}"
            )

        return {
            "weekly_plan": {d: name_of(week[i]) for i, d in enumerate(labels)},
            "weekly_plan_slots": week,
            "weekly_plan_verified": matches,
            "slot_info": {str(k): name_of(k) for k in sorted(slot_to_id)},
            "cloud_timeline": cloud_timeline,
        }

    def _related_entities(self) -> dict[str, Any]:
        """Entity-IDs der übrigen Entitäten dieses Geräts (über die unique_ids)."""
        try:
            reg = er.async_get(self.hass)
        except Exception:  # noqa: BLE001
            return {}

        def find(domain: str, suffix: str) -> str | None:
            return reg.async_get_entity_id(domain, DOMAIN, f"{self._cid}_{suffix}")

        channels = {
            ch: find("number", ch) for ch in ("white", "red", "green", "blue")
        }
        return {
            "light_entity": find("light", "light"),
            "auto_switch_entity": find("switch", "auto"),
            "channel_entities": {k: v for k, v in channels.items() if v},
        }
