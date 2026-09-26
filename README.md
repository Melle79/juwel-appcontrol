# Juwel AppControl – Home Assistant Integration

[![GitHub Release](https://img.shields.io/github/v/release/Melle79/juwel-appcontrol?style=flat-square)](https://github.com/Melle79/juwel-appcontrol/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Home Assistant Integration](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?style=flat-square&logo=homeassistant&logoColor=white)](https://www.home-assistant.io/integrations/)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square&logo=homeassistantcommunitystore&logoColor=white)](https://hacs.xyz/)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-melle79-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/melle79)

[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Melle79&repository=juwel-appcontrol&category=integration)

Control your **JUWEL AppControl** aquarium devices from Home Assistant, including a
dashboard card for the lighting in the look of the MyJUWEL app.

AppControl devices have **no local API**: they only keep an outbound connection to
the manufacturer's cloud. This integration therefore talks to the same cloud API the
MyJUWEL app uses, with your MyJUWEL account.

---

## Supported devices

| Device | Status |
|---|---|
| **HeliaLux AppControl** (lighting) | ✅ verified on real hardware |
| **SmartFeed AppControl** (feeder) | ✅ verified on real hardware |
| **EccoFlow AppControl** (pump) | 🧪 built from the manufacturer's device specification — untested |

The integration is **trait driven**: for every device it reads the capability
description from the manufacturer's product catalogue and creates the matching
entities. New device types therefore show up on their own.

> If you own an EccoFlow, feedback is very welcome — please
> [open an issue](https://github.com/Melle79/juwel-appcontrol/issues) with what works
> and what does not. Controls are only created where the specification defines a
> clear value range; everything else is exposed read-only so no invalid command is
> ever sent to your device.

---

## Features

### 💡 Lighting (HeliaLux)
- **On/off**, brightness and colour (WRGB) through a single light entity
- **Individual colour channels** W/R/G/B as percentage sliders
- **Automatic schedule** on/off — manual changes pause it automatically
- Active **lighting profile** including its full daily curve
- **Weekly plan:** a profile per weekday, editable right in the card

### 🐟 Feeder (SmartFeed)
- **Feed now** button, feed quantity, quantity for the button on the device
- Status LED switch, power
- **Feed chamber empty** and device-error warnings, auger state, last feeding
- **Feeding plan** with times, amounts and weekdays — editable right in the card

### 🌊 Pump (EccoFlow)
- Power, operating mode, smart-feed pause, power limit
- Maintenance timer resets (pump cleaning, impeller)
- Speed, flow rate, effect, night mode and power profile as sensors

### 📊 Dashboard cards
- **Daily curve** of the active profile (W/R/G/B over 24 h) with a "now" marker
- Profile row, manual-mode switch and four colour sliders
- **Weekly plan** as a collapsible section: one profile per weekday, or apply one
  to the whole week
- **Two layouts:** full or compact (single row)
- **Two designs:** MyJUWEL look or your global Home Assistant theme
- **Pop-up:** the compact card opens the full one — either as its own dialog or
  via a Bubble Card pop-up
- Fully configurable in the **visual card editor**
- **Ships with the integration** and is registered automatically — no manual
  resource entry needed

There is a second card for the **SmartFeed**: a large *Feed now* button (disabled
while the auger runs), quantity stepper, status LED, chamber state and last feeding
— plus a collapsible **feeding planner**: pick the weekdays, set each feeding time
and amount, add or remove feedings, then save. Same two layouts, same two designs.

English and German are included; the cards follow your Home Assistant language.

---

## Entities

Lighting devices:

| Entity | Description |
|---|---|
| `light.<name>` | On/off, brightness, colour (RGBW) |
| `number.<name>_white` / `_red` / `_green` / `_blue` | Colour channel in % |
| `switch.<name>_automatic_mode` | Schedule on/off |
| `sensor.<name>_profile` | Active profile; exposes the daily curve as attribute `time_events` |

> **Where the light's values come from.** In automatic mode the device does not
> report intermediate channel values — they were observed frozen on the daytime
> plateau for four days while the tank was dark at night, because the cloud only
> gets them while the app is connected. The integration therefore reads the
> **active profile's curve at the current time** whenever the schedule is running,
> and falls back to the reported values in manual mode. The light entity says
> which it used, in the attribute `values_from` (`schedule` or `device`).

Every device also gets diagnostics: **last contact**, and **signal strength** where
the device reports it. Firmware, hardware revision and serial number show up on the
device page.

Feeder (SmartFeed):

| Entity | Description |
|---|---|
| `button.<name>_feed_now` | Feeds the configured quantity |
| `number.<name>_feed_quantity` | Feed quantity 1–8 |
| `number.<name>_feed_quantity_device_button` | Quantity for the button on the device |
| `switch.<name>_power` / `_status_led` | Power and status LED |
| `binary_sensor.<name>_feed_chamber_empty` | Chamber empty warning |
| `binary_sensor.<name>_device_error` | Device error channel |
| `sensor.<name>_feed_motor` | Auger: idle / running |
| `sensor.<name>_last_feeding` | Timestamp of the last feeding |
| `sensor.<name>_feeding_plan` | Plan name; times, amounts and weekdays as attributes |

The pump gets entities derived from its traits — switches, a select and buttons
where the specification defines a clear value range, sensors otherwise.

> **The manufacturer's catalogue is incomplete.** On the two devices verified here
> it declares 6 of 25 state fields. Anything a device reports that the catalogue
> does not describe is therefore offered as a **disabled diagnostic sensor** —
> enable it on the device page. For an EccoFlow that should include the water
> temperature, which the product page advertises but the catalogue omits.

> **Automatic vs. manual (lighting):** While the schedule is running, the lamp
> ignores manual commands — exactly like the app, where the sliders are greyed out.
> As soon as you change brightness, colour or on/off, the integration pauses the
> schedule for you (preview mode, 1 hour). The **Automatic mode** switch takes you
> back to the stored daily cycle at any time.

---

## Installation

### HACS
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/Melle79/juwel-appcontrol` as **Integration**
2. Install "Juwel AppControl"
3. Restart Home Assistant

### Manual
1. Copy `custom_components/juwel_appcontrol/` into `<config>/custom_components/`
2. Restart Home Assistant

### Set up
**Settings → Devices & services → Add integration → "Juwel AppControl"**,
then enter the email and password of your MyJUWEL account (same as in the app).

### Dashboard card
**Nothing to do** — the integration ships both cards, serves them and registers the
resource entry automatically (and bumps it on updates so no browser cache gets in
the way). Just pick **Add card → "Juwel HeliaLux"** or **"Juwel SmartFeed"** in the card picker.

> **Lovelace in YAML mode?** Add the resource yourself:
> `/juwel_appcontrol/juwel-appcontrol-cards.js` as **module**.

---

## Card options

Everything is available in the visual editor:

| Option | Values | Meaning |
|---|---|---|
| `light` | entity | Light entity of this integration; everything else is discovered automatically |
| `name` | text | Custom heading |
| `layout` | `full` \| `compact` | Full card or a single row |
| `design` | `juwel` \| `ha` | MyJUWEL look or your Home Assistant theme |
| `show_chart` | true/false | Daily curve (only with `full`) |
| `show_week` | true/false | Weekly plan section |
| `tap_action` | `popup` \| `more-info` \| `hash` \| `none` | What happens on tap |
| `popup_hash` | e.g. `#aquarium` | Target hash for `tap_action: hash` (Bubble Card) |

```yaml
type: custom:juwel-helialux-card
light: light.my_aquarium
layout: compact
design: ha
tap_action: popup
```

### Feeder card

| Option | Values | Meaning |
|---|---|---|
| `plan_sensor` | entity | The feeding-plan sensor; everything else is discovered automatically |
| `name` | text | Custom heading |
| `layout` | `full` \| `compact` | Full card or a single row |
| `design` | `juwel` \| `ha` | MyJUWEL look or your Home Assistant theme |
| `show_plan` | true/false | Feeding planner section |
| `tap_action` | `popup` \| `more-info` \| `none` | What happens on tap |

```yaml
type: custom:juwel-feeder-card
plan_sensor: sensor.my_feeder_feeding_plan
design: ha
```

---

## Actions

Both are also available from the cards, so you only need them for automations.

### `juwel_appcontrol.set_profile`

Assign a lighting profile to a weekday. Target a `select` entity of this integration.

| Field | Values | Meaning |
|---|---|---|
| `profile` | text | Profile name as shown by the *Profile (today)* entity |
| `weekday` | `today` \| `all` \| `monday` … `sunday` | Which day to assign it to |

```yaml
action: juwel_appcontrol.set_profile
target:
  entity_id: select.my_aquarium_profile_today
data:
  profile: Standard
  weekday: saturday
```

> The MyJUWEL app can only change the current day. Here you can pick any day, or
> the whole week — `all` walks through the seven days and takes about a minute.

### `juwel_appcontrol.set_feeding_plan`

Change a SmartFeed's feeding plan. Target the feeding-plan `sensor`.

| Field | Values | Meaning |
|---|---|---|
| `weekdays` | list of `all` \| `monday` … `sunday` | Days the plan runs on; omit to keep them |
| `feedings` | list of `{time, amount}` | Times (`HH:MM`) and amounts (1–8); omit to keep them |

```yaml
action: juwel_appcontrol.set_feeding_plan
target:
  entity_id: sensor.my_feeder_feeding_plan
data:
  weekdays: [monday, thursday, saturday]
  feedings:
    - time: "08:00"
      amount: 2
    - time: "18:00"
      amount: 1
```

> This replaces the whole feeding plan — the service has no way to change a single
> entry. Fields you leave out keep their current value. If the feeder has no plan
> at all, one is created; pass both fields in that case.

---

## Notes

- **Cloud polling**, default interval 60 s, adjustable from 30 to 600 s under
  *Configure* on the integration page. The devices report slowly and the daily
  curve changes gently — about two percentage points a minute on the steepest
  ramp — so a longer interval misses nothing and halves the requests.
- This talks to the manufacturer's own cloud service, the same one the MyJUWEL
  app uses, with your MyJUWEL account. There is no public or documented API for
  it, so if Juwel changes the service, the integration has to be adapted. No
  warranty, and no affiliation with JUWEL Aquarium GmbH & Co. KG.
- Tested with **HeliaLux AppControl** (firmware V2.0.1.3) and **SmartFeed
  AppControl** (firmware V2.0.1.58) on Home Assistant 2026.9. Lighting weekly plan
  and feeding planner are both verified on real hardware.
- The EccoFlow measures water temperature and raises alarms for blocked rotor,
  critical water level and temperature limits. None of this is in the product
  catalogue, so those values arrive as disabled diagnostic sensors.
- The manufacturer's product catalogue declares some values as objects where the
  devices actually use plain numbers. The integration mirrors whatever the device
  reports instead of trusting the schema — verified on both devices.
- The older **HeliaLux SmartControl** is *not* supported by this integration. It has
  a local web interface and is covered by
  [MrSleeps/Juwel-HeliaLux-Home-Assistant-Custom-Component](https://github.com/MrSleeps/Juwel-HeliaLux-Home-Assistant-Custom-Component)
  (domain `juwel_helialux`). This integration uses the separate domain
  `juwel_appcontrol`, so both can be installed side by side.

---

## License

MIT — see [LICENSE](LICENSE).

If this project helps you:
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-melle79-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/melle79)
