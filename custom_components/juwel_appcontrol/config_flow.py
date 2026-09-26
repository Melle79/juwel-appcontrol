"""Config-Flow für die Juwel HeliaLux (MyJUWEL Cloud) Integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JuwelApiError, JuwelAuthError, JuwelCloud
from .const import (
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class JuwelConfigFlow(ConfigFlow, domain=DOMAIN):
    """Anmeldung mit MyJUWEL-Zugangsdaten."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> JuwelOptionsFlow:
        return JuwelOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_configured()

            client = JuwelCloud(
                lambda: async_get_clientsession(self.hass), email, user_input[CONF_PASSWORD]
            )
            try:
                await client.async_validate()
            except JuwelAuthError:
                errors["base"] = "invalid_auth"
            except JuwelApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unerwarteter Fehler beim MyJUWEL-Login")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"MyJUWEL ({email})",
                    data={CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class JuwelOptionsFlow(OptionsFlow):
    """Abfrageintervall einstellen.

    Die Geraete melden traege und der Tagesverlauf aendert sich langsam -
    in der steilsten Rampe rund zwei Prozentpunkte je Minute. Wer die
    Cloud schonen will, darf hier hochgehen, ohne etwas zu verpassen.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        aktuell = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=aktuell): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=10,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.BOX,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
