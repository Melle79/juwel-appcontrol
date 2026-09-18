"""Juwel HeliaLux (MyJUWEL Cloud) Integration."""
from __future__ import annotations

import logging
import os

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JuwelCloud
from .const import (
    CARD_FILENAME,
    CARD_URL_BASE,
    CARD_VERSION,
    CONF_EMAIL,
    CONF_PASSWORD,
    DOMAIN,
)
from .coordinator import JuwelCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]

_CARD_KEY = f"{DOMAIN}_card_registered"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Dashboard-Karte ausliefern und im Frontend laden – ohne Ressourcen-Eintrag."""
    if hass.data.get(_CARD_KEY):
        return

    card_path = os.path.join(os.path.dirname(__file__), "www", CARD_FILENAME)
    if not os.path.exists(card_path):
        _LOGGER.warning("Dashboard-Karte nicht gefunden: %s", card_path)
        return

    url = f"{CARD_URL_BASE}/{CARD_FILENAME}"
    try:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(url, card_path, cache_headers=False)]
        )
        add_extra_js_url(hass, f"{url}?v={CARD_VERSION}")
        hass.data[_CARD_KEY] = True
        _LOGGER.debug("Dashboard-Karte registriert unter %s", url)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Dashboard-Karte konnte nicht registriert werden")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration aus einem Config-Entry einrichten."""
    await _async_register_card(hass)

    session = async_get_clientsession(hass)
    client = JuwelCloud(session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD])

    coordinator = JuwelCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Config-Entry entladen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
