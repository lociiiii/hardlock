"""HardLock client — hardware verification against the HardLock API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import requests

from hardlock.exceptions import DeviceNotFoundError, HardLockError, UnauthorizedError
from hardlock.fingerprint import compute_fingerprint
from hardlock.hardware import get_esp32_mac, get_mb_serial, get_pc_uuid


@dataclass(frozen=True)
class HardLockSession:
    """Short-lived authorization returned by :meth:`HardLock.verify`."""

    authorized: bool
    session_token: str
    expires_in: int


class HardLock:
    """
    Hardware-bound licensing client.

    Parameters
    ----------
    api_key:
        Application API key from the HardLock dashboard (``hl_live_...``).
    license_key:
        End-user license key (``HLCK-XXXX-XXXX-XXXX``).
    product_id:
        Application UUID from the dashboard.
    esp_port:
        Serial port for the ESP32 dongle (e.g. ``COM3``). ``None`` auto-detects.
    server_url:
        HardLock API base URL. Defaults to ``HARDLOCK_SERVER_URL`` env var or
        ``http://localhost:8000``.
    timeout:
        HTTP request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        license_key: str,
        product_id: str,
        *,
        esp_port: Optional[str] = None,
        server_url: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self.api_key = api_key
        self.license_key = license_key
        self.product_id = product_id
        self.esp_port = esp_port
        self.server_url = (
            server_url or os.environ.get("HARDLOCK_SERVER_URL") or "http://localhost:8000"
        ).rstrip("/")
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    def _collect_hardware(self) -> Tuple[str, str, str, str]:
        """Return ``(pc_uuid, mb_serial, esp_mac, esp_port)``."""
        try:
            pc_uuid = get_pc_uuid()
            mb_serial = get_mb_serial()
        except Exception as exc:
            raise HardLockError(f"Failed to read PC hardware IDs: {exc}") from exc

        try:
            esp_mac, resolved_port = get_esp32_mac(self.esp_port)
        except DeviceNotFoundError:
            raise
        except Exception as exc:
            raise DeviceNotFoundError(f"Failed to read ESP32 MAC: {exc}") from exc

        self.esp_port = resolved_port
        return pc_uuid, mb_serial, esp_mac, resolved_port

    def register(self, label: Optional[str] = None) -> dict:
        """
        One-time device registration for this license on the current hardware.

        POST /devices/register
        """
        pc_uuid, mb_serial, esp_mac, _ = self._collect_hardware()
        payload = {
            "license_key": self.license_key,
            "pc_uuid": pc_uuid,
            "mb_serial": mb_serial,
            "esp_mac": esp_mac,
        }
        if label:
            payload["label"] = label

        url = f"{self.server_url}/devices/register"
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise HardLockError(f"Cannot reach HardLock server at {url}: {exc}") from exc

        if response.status_code >= 400:
            self._raise_api_error(response, "Registration failed")

        return response.json()

    def verify(self, license_key: Optional[str] = None) -> HardLockSession:
        """
        Verify hardware against the server and return a short-lived session.

        Reads PC UUID, motherboard serial, and ESP32 MAC, then POSTs to
        ``/devices/verify``. Blocks for a few seconds while hardware is probed.
        """
        key = license_key or self.license_key
        pc_uuid, mb_serial, esp_mac, _ = self._collect_hardware()

        payload = {
            "license_key": key,
            "pc_uuid": pc_uuid,
            "mb_serial": mb_serial,
            "esp_mac": esp_mac,
        }

        url = f"{self.server_url}/devices/verify"
        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise HardLockError(f"Cannot reach HardLock server at {url}: {exc}") from exc

        if response.status_code == 403:
            data = response.json()
            reason = data.get("reason", "UNAUTHORIZED")
            raise UnauthorizedError(
                f"Not authorized: {reason}",
                reason=reason,
            )

        if response.status_code >= 400:
            self._raise_api_error(response, "Verification failed")

        data = response.json()
        if not data.get("authorized"):
            reason = data.get("reason", "UNAUTHORIZED")
            raise UnauthorizedError(
                f"Not authorized: {reason}",
                reason=reason,
            )

        return HardLockSession(
            authorized=True,
            session_token=data["session_token"],
            expires_in=int(data.get("expires_in", 28800)),
        )

    @staticmethod
    def _raise_api_error(response: requests.Response, prefix: str) -> None:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise HardLockError(f"{prefix} ({response.status_code}): {detail}")

    @property
    def fingerprint(self) -> str:
        """Compute the device fingerprint for the currently attached hardware."""
        pc_uuid, mb_serial, esp_mac, _ = self._collect_hardware()
        return compute_fingerprint(pc_uuid, mb_serial, esp_mac)
