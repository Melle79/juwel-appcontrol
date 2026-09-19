"""Konstanten für die Juwel HeliaLux (MyJUWEL Cloud) Integration."""
from __future__ import annotations

DOMAIN = "juwel_appcontrol"

# qconnex/MyJUWEL Cloud
API_HOST = "https://app-api.prod.qconnex.io"
ENVIRONMENT_NAME = "Juwel"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# Wie lange der Zeitplan beim manuellen Eingriff pausiert wird (Sekunden).
# Entspricht dem Verhalten der App (Vorschaumodus = 1 h).
PREVIEW_TIMEOUT = 3600

DEFAULT_SCAN_INTERVAL = 60  # Sekunden

# Produkt-IDs, die diese Integration als Licht behandelt
LIGHT_PRODUCT_IDS = ("@juwel.lighting.helialux1",)

# Dashboard-Karte, die die Integration selbst mitbringt
CARD_FILENAME = "juwel-helialux-card.js"
CARD_URL_BASE = f"/{DOMAIN}"
CARD_VERSION = "2.1.0"
