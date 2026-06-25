"""Canonical fingerprint algorithm — must match server/core/fingerprint.py exactly."""

import hashlib


def compute_fingerprint(pc_uuid: str, mb_serial: str, esp_mac: str) -> str:
    """SHA-256(PC_UUID + MB_SERIAL + ESP_MAC) with normalized inputs."""
    raw = pc_uuid.strip() + mb_serial.strip() + esp_mac.strip().upper()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
