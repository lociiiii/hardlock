import hashlib


def compute_fingerprint(pc_uuid: str, mb_serial: str, esp_mac: str) -> str:
    """Canonical fingerprint — must match sdk/hardlock/fingerprint.py exactly."""
    raw = pc_uuid.strip() + mb_serial.strip() + esp_mac.strip().upper()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
