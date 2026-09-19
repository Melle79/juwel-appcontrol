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
| **SmartFeed AppControl** (feeder) | 🧪 built from the manufacturer's device specification — untested |
| **EccoFlow AppControl** (pump) | 🧪 built from the manufacturer's device specification — untested |

The integration is **trait driven**: for every device it reads the capability
description from the manufacturer's product catalogue and creates the matching
entities. New device types therefore show up on their own.

> If you own a SmartFeed or EccoFlow, feedback is very welcome — please
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

### 🐟 Feeder (SmartFeed)
- **Feed now** button, feed quantity, quantity for the button on the device
- Status LED switch, power

### 🌊 Pump (EccoFlow)
- Power, operating mode, smart-feed pause, power limit
- Maintenance timer resets (pump cleaning, impeller)
- Speed, flow rate, effect, night mode and power profile as sensors

### 📊 Dashboard card (lighting)
- **Daily curve** of the active profile (W/R/G/B over 24 h) with a "now" marker
- Profile row, manual-mode switch and four colour sliders
- **Two layouts:** full or compact (single row)
- **Two designs:** MyJUWEL look or your global Home Assistant theme
- **Pop-up:** the compact card opens the full one — either as its own dialog or
  via a Bubble Card pop-up
- Fully configurable in the **visual card editor**
- **Ships with the integration** and is registered automatically — no manual
  resource entry needed

English and German are included; the card follows your Home Assistant language.

---

## Entities

Lighting devices:

| Entity | Description |
|---|---|
| `light.<name>` | On/off, brightness, colour (RGBW) |
| `number.<name>_white` / `_red` / `_green` / `_blue` | Colour channel in % |
| `switch.<name>_automatic_mode` | Schedule on/off |
| `sensor.<name>_profile` | Active profile; exposes the daily curve as attribute `time_events` |

Feeder and pump get entities derived from their traits — buttons, switches,
selects and numbers where the range is known, sensors otherwise.

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
**Nothing to do** — the integration ships the card, serves it and registers the
resource entry automatically (and bumps it on updates so no browser cache gets in
the way). Just pick **Add card → "Juwel HeliaLux"** in the card picker.

> **Lovelace in YAML mode?** Add the resource yourself:
> `/juwel_appcontrol/juwel-helialux-card.js` as **module**.

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
| `tap_action` | `popup` \| `more-info` \| `hash` \| `none` | What happens on tap |
| `popup_hash` | e.g. `#aquarium` | Target hash for `tap_action: hash` (Bubble Card) |

```yaml
type: custom:juwel-helialux-card
light: light.my_aquarium
layout: compact
design: ha
tap_action: popup
```

---

## Notes

- **Cloud polling**, default interval 60 s.
- This uses the **unofficial** manufacturer API (`app-api.prod.qconnex.io`).
  If Juwel changes it, the integration has to be adapted. No warranty, and no
  affiliation with JUWEL Aquarium GmbH & Co. KG.
- Tested with **HeliaLux AppControl**, firmware V2.0.1.3
  (`@juwel.lighting.helialux1`) on Home Assistant 2026.9.
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
