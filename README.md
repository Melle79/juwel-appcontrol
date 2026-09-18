# Juwel HeliaLux – Home Assistant Integration

[![GitHub Release](https://img.shields.io/github/v/release/Melle79/juwel-helialux?style=flat-square)](https://github.com/Melle79/juwel-helialux/releases)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-green?style=flat-square)](LICENSE)
[![Home Assistant Integration](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?style=flat-square&logo=homeassistant&logoColor=white)](https://www.home-assistant.io/integrations/)
[![HACS: Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square&logo=homeassistantcommunitystore&logoColor=white)](https://hacs.xyz/)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-melle79-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/melle79)

[![Repository zu HACS hinzufügen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Melle79&repository=juwel-helialux&category=integration)

Steuert die **Juwel HeliaLux AppControl** (Aquarienbeleuchtung) in Home Assistant –
inklusive passender Dashboard-Karte im MyJUWEL-Look.

Die AppControl besitzt **keine lokale Schnittstelle**: Sie hält ausschließlich eine
ausgehende Verbindung zur Hersteller-Cloud. Diese Integration spricht daher dieselbe
Cloud-API wie die MyJUWEL-App, mit deinem MyJUWEL-Konto.

---

## Features

### 💡 Steuerung
- **An/Aus**, Helligkeit und Farbe (WRGB) über eine Licht-Entität
- **Einzelne Farbkanäle** W/R/G/B als Prozent-Regler
- **Automatik-Zeitplan** an/aus – die Integration pausiert ihn bei manuellen Eingriffen automatisch
- Aktives **Beleuchtungsprofil** inklusive kompletter Tageskurve

### 📊 Dashboard-Karte
- **Tageskurve** des aktiven Profils (W/R/G/B über 24 h) mit Jetzt-Markierung
- Profilanzeige, Manuell-Schalter und vier Farbregler
- **Zwei Darstellungen:** vollständig oder kompakt (eine Zeile)
- **Zwei Designs:** MyJUWEL-Look oder globales Home-Assistant-Theme
- **Popup:** kompakte Karte öffnet auf Klick die große – wahlweise als eigener Dialog oder über ein Bubble-Card-Popup
- Vollständig über die **UI konfigurierbar** (grafischer Karten-Editor)
- **Wird von der Integration mitgeliefert** und automatisch geladen – kein Ressourcen-Eintrag nötig

---

## Entitäten

Pro Gerät werden angelegt:

| Entität | Beschreibung |
|---|---|
| `light.<name>` | An/Aus, Helligkeit, Farbe (RGBW) |
| `number.<name>_weiss` | Weiß-Kanal in % |
| `number.<name>_rot` | Rot-Kanal in % |
| `number.<name>_gruen` | Grün-Kanal in % |
| `number.<name>_blau` | Blau-Kanal in % |
| `switch.<name>_automatikmodus` | Zeitplan an/aus |
| `sensor.<name>_profil` | Aktives Profil; liefert die Tageskurve als Attribut `time_events` |

> **Automatik vs. Manuell:** Im Automatikmodus ignoriert die Lampe manuelle Befehle –
> genauso wie in der App, wo die Regler dann ausgegraut sind. Sobald du Helligkeit,
> Farbe oder An/Aus änderst, pausiert die Integration den Zeitplan automatisch
> (Vorschaumodus, 1 Stunde). Über den Schalter **Automatikmodus** geht es jederzeit
> zurück auf den gespeicherten Tagesverlauf.

---

## Installation

### HACS (empfohlen)
1. HACS → ⋮ → **Benutzerdefinierte Repositories** → `https://github.com/Melle79/juwel-helialux` als **Integration** hinzufügen
2. „Juwel HeliaLux" installieren
3. Home Assistant neu starten

### Manuell
1. Ordner `custom_components/juwel_helialux/` nach `<config>/custom_components/` kopieren
2. Home Assistant neu starten

### Einrichten
**Einstellungen → Geräte & Dienste → Integration hinzufügen → „Juwel HeliaLux"**,
dann E-Mail und Passwort deines MyJUWEL-Kontos eintragen (dieselben wie in der App).

### Dashboard-Karte
**Nichts weiter zu tun** – die Integration bringt die Karte mit, liefert sie selbst aus
und legt den passenden Ressourcen-Eintrag automatisch an (und hebt ihn bei Updates auf
die neue Version, damit kein Browser-Cache im Weg steht).

Einfach im Dashboard **Karte hinzufügen → „Juwel HeliaLux"** wählen.

> **Lovelace im YAML-Modus?** Dann trage die Ressource selbst ein:
> `/juwel_helialux/juwel-helialux-card.js` als **module**.
>
> **Update von ≤ 1.2.0?** Den alten Eintrag `/local/juwel-helialux-card.js` und die
> Datei in `www/` löschen – beides wird nicht mehr gebraucht.

---

## Karten-Optionen

Alles im grafischen Editor einstellbar:

| Option | Werte | Bedeutung |
|---|---|---|
| `light` | Entität | Licht-Entität der Integration; alles Weitere wird automatisch gefunden |
| `name` | Text | Eigene Überschrift |
| `layout` | `full` \| `compact` | Vollständig oder eine Zeile |
| `design` | `juwel` \| `ha` | MyJUWEL-Look oder globales HA-Theme |
| `show_chart` | true/false | Tageskurve (nur bei `full`) |
| `tap_action` | `popup` \| `more-info` \| `hash` \| `none` | Verhalten beim Antippen |
| `popup_hash` | z. B. `#aquarium` | Ziel-Hash bei `tap_action: hash` (Bubble Card) |

```yaml
type: custom:juwel-helialux-card
light: light.neles_aquarium
layout: compact
design: ha
tap_action: popup
```

---

## Hinweise

- **Cloud-Polling**, Standardintervall 60 s.
- Die Integration nutzt die **inoffizielle** Hersteller-API
  (`app-api.prod.qconnex.io`). Ändert Juwel etwas daran, muss die Integration
  angepasst werden. Es gibt keine Garantie und keine Verbindung zu JUWEL Aquarium.
- Getestet mit **HeliaLux AppControl**, Firmware V2.0.1.3
  (`@juwel.lighting.helialux1`), Home Assistant 2026.9.
- Der ältere **HeliaLux SmartControl** wird *nicht* unterstützt – der hat eine lokale
  Weboberfläche, dafür gibt es bereits andere Integrationen.

---

## Lizenz

MIT – siehe [LICENSE](LICENSE).

Wenn dir das Projekt hilft:
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20me%20a%20coffee-melle79-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/melle79)
