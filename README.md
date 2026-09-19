# Juwel HeliaLux – Home Assistant Integration

[![GitHub Release](https://img.shields.io/github/v/release/Melle79/juwel-helialux?style=flat-square)](https://github.com/Melle79/juwel-helialux/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Home Assistant Integration](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?style=flat-square&logo=homeassistant&logoColor=white)](https://www.home-assistant.io/integrations/)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square&logo=homeassistantcommunitystore&logoColor=white)](https://hacs.xyz/)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-melle79-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/melle79)

[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Melle79&repository=juwel-helialux&category=integration)

Control your **Juwel HeliaLux AppControl** aquarium light from Home Assistant —
including a matching dashboard card in the look of the MyJUWEL app.

The AppControl has **no local API**: it only keeps an outbound connection to the
manufacturer's cloud. This integration therefore talks to the same cloud API the
MyJUWEL app uses, with your MyJUWEL account.

<!-- Add a screenshot here once you have one:
![Card](docs/card.png)
-->

---

## Features

### 💡 Control
- **On/off**, brightness and colour (WRGB) through a single light entity
- **Individual colour channels** W/R/G/B as percentage sliders
- **Automatic schedule** on/off — manual changes pause it automatically
- Active **lighting profile** including its full daily curve

### 📊 Dashboard card
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

Created per device:

| Entity | Description |
|---|---|
| `light.<name>` | On/off, brightness, colour (RGBW) |
| `number.<name>_white` | White channel in % |
| `number.<name>_red` | Red channel in % |
| `number.<name>_green` | Green channel in % |
| `number.<name>_blue` | Blue channel in % |
| `switch.<name>_automatic_mode` | Schedule on/off |
| `sensor.<name>_profile` | Active profile; exposes the daily curve as attribute `time_events` |

> **Automatic vs. manual:** While the schedule is running, the lamp ignores manual
> commands — exactly like the app, where the sliders are greyed out. As soon as you
> change brightness, colour or on/off, the integration pauses the schedule for you
> (preview mode, 1 hour). The **Automatic mode** switch takes you back to the stored
> daily cycle at any time.

---

## Installation

### HACS
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/Melle79/juwel-helialux` as **Integration**
2. Install "Juwel HeliaLux"
3. Restart Home Assistant

### Manual
1. Copy `custom_components/juwel_helialux/` into `<config>/custom_components/`
2. Restart Home Assistant

### Set up
**Settings → Devices & services → Add integration → "Juwel HeliaLux"**,
then enter the email and password of your MyJUWEL account (same as in the app).

### Dashboard card
**Nothing to do** — the integration ships the card, serves it and registers the
resource entry automatically (and bumps it on updates so no browser cache gets in
the way). Just pick **Add card → "Juwel HeliaLux"**.

> **Lovelace in YAML mode?** Add the resource yourself:
> `/juwel_helialux/juwel-helialux-card.js` as **module**.
>
> **Upgrading from ≤ 1.2.0?** Remove the old `/local/juwel-helialux-card.js`
> resource entry and the file in `www/` — both are no longer needed.

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
- The older **HeliaLux SmartControl** is *not* supported — it has a local web
  interface, and other integrations already cover it.

---

## License

MIT — see [LICENSE](LICENSE).

If this project helps you:
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-melle79-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/melle79)
