"""Config-Flow für die Juwel HeliaLux (MyJUWEL Cloud) Integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import JuwelApiError, JuwelAuthError, JuwelCloud
from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            client = JuwelCloud(session, email, user_input[CONF_PASSWORD])
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
