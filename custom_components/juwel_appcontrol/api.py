"""Client für die MyJUWEL / qconnex Cloud-API der HeliaLux AppControl."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import API_HOST, ENVIRONMENT_NAME, PREVIEW_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class JuwelAuthError(Exception):
    """Anmeldung fehlgeschlagen (falsche Zugangsdaten)."""


class JuwelApiError(Exception):
    """Allgemeiner API-Fehler."""


class JuwelCloud:
    """Kapselt Login und Gerätesteuerung gegen die qconnex-Cloud."""

    def __init__(
        self, session: aiohttp.ClientSession, email: str, password: str
    ) -> None:
        self._session = session
        self._email = email
        self._password = password
        self._token: str | None = None
        self._lock = asyncio.Lock()

    # ---- intern -------------------------------------------------------

    async def _login(self) -> None:
        payload = {
            "email": self._email,
            "password": self._password,
            "environmentName": ENVIRONMENT_NAME,
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        try:
            async with self._session.post(
                f"{API_HOST}/auth/login", json=payload, headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                text = await resp.text()
                if resp.status in (200, 201):
                    data = await resp.json()
                    self._token = data.get("accountToken") or data.get("accessToken")
                    if not self._token:
                        raise JuwelApiError("Login-Antwort ohne Token")
                    return
                if resp.status == 401:
                    raise JuwelAuthError("E-Mail oder Passwort falsch")
                raise JuwelApiError(f"Login HTTP {resp.status}: {text[:200]}")
        except aiohttp.ClientError as err:
            raise JuwelApiError(f"Verbindungsfehler beim Login: {err}") from err

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, path: str, json: Any | None = None, _retry: bool = True
    ) -> Any:
        async with self._lock:
            if not self._token:
                await self._login()
        try:
            async with self._session.request(
                method, f"{API_HOST}{path}", json=json, headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 401 and _retry:
                    self._token = None
                    return await self._request(method, path, json, _retry=False)
                text = await resp.text()
                if resp.status not in (200, 201):
                    raise JuwelApiError(f"{method} {path} -> HTTP {resp.status}: {text[:200]}")
                if resp.content_type == "application/json":
                    return await resp.json()
                return text
        except aiohttp.ClientError as err:
            raise JuwelApiError(f"Verbindungsfehler {method} {path}: {err}") from err

    # ---- öffentlich ---------------------------------------------------

    async def async_validate(self) -> None:
        """Nur Login prüfen (für den Config-Flow)."""
        await self._login()

    async def get_settings(self) -> dict[str, Any]:
        return await self._request("GET", "/settings")

    async def get_product_config(self, product_id: str) -> dict[str, Any] | None:
        """Fähigkeitsbeschreibung eines Produkts (traits mit msg_key/Schema)."""
        try:
            return await self._request("GET", f"/config/product/{product_id}")
        except JuwelApiError as err:
            _LOGGER.debug("Produktkonfiguration %s nicht abrufbar: %s", product_id, err)
            return None

    async def set_trait(
        self, cloud_device_id: str, msg_key: str, value: Any
    ) -> None:
        """Einen Trait-Wert setzen: {"payload": {"type": "request", msg_key: value}}."""
        await self._set_state(cloud_device_id, {msg_key: value})

    async def get_presets(self) -> list[dict[str, Any]]:
        """Alle Profile inkl. Tageskurve (timeEvents)."""
        data = await self._request("GET", "/presets")
        return data if isinstance(data, list) else []

    async def get_state(self, cloud_device_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/device/{cloud_device_id}/state")

    async def _set_state(self, cloud_device_id: str, fields: dict[str, Any]) -> Any:
        body = {"payload": {"type": "request", **fields}}
        return await self._request("POST", f"/device/{cloud_device_id}/state", json=body)

    async def _command(self, cloud_device_id: str, body: dict[str, Any]) -> Any:
        return await self._request("POST", f"/device/{cloud_device_id}/command", json=body)

    async def pause_schedule(self, cloud_device_id: str) -> Any:
        """Zeitplan pausieren = Manuell-/Vorschaumodus aktivieren."""
        return await self._command(
            cloud_device_id,
            {"type": "preset", "action": "pause", "timeout": PREVIEW_TIMEOUT},
        )

    async def resume_schedule(self, cloud_device_id: str) -> Any:
        """Zurück in den Automatik-Modus."""
        return await self._command(cloud_device_id, {"type": "preset", "action": "resume"})

    async def set_manual(
        self,
        cloud_device_id: str,
        *,
        current_mode: str | None,
        status: str | None = None,
        brightness_pct: int | None = None,
        rgb: tuple[int, int, int] | None = None,
        white: int | None = None,
    ) -> None:
        """Manuellen Wert setzen. Pausiert bei Bedarf zuerst den Zeitplan."""
        if current_mode == "auto":
            await self.pause_schedule(cloud_device_id)

        fields: dict[str, Any] = {}
        if status is not None:
            fields["status"] = status
        if brightness_pct is not None:
            fields["brightness"] = {"percentage": int(brightness_pct)}
        if rgb is not None:
            fields["color"] = {"red": int(rgb[0]), "green": int(rgb[1]), "blue": int(rgb[2])}
        if white is not None:
            fields["white"] = {"value": int(white)}

        if fields:
            await self._set_state(cloud_device_id, fields)
