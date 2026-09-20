"""Diagnostics for Juwel AppControl."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from .const import DOMAIN

# Was das Konto verrät, bleibt draußen - Zugangsdaten ebenso wie die
# Schlüssel und Token, die der Hersteller je Gerät mitliefert.
TO_REDACT = {
    CONF_EMAIL,
    CONF_PASSWORD,
    "aesKey",
    "accessToken",
    "accountToken",
    "cloudDeviceId",
    "email",
    "macAddress",
    "password",
    "serialNumber",
    "token",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "devices": async_redact_data(coordinator.data, TO_REDACT),
    }
