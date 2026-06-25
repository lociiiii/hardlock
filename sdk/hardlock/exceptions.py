"""HardLock SDK exception hierarchy."""

from __future__ import annotations

from typing import Optional


class HardLockError(Exception):
    """Base exception for all HardLock SDK errors."""


class DeviceNotFoundError(HardLockError):
    """Raised when the ESP32 dongle cannot be found or does not respond."""


class UnauthorizedError(HardLockError):
    """Raised when the server denies authorization."""

    def __init__(self, message: str, reason: Optional[str] = None):
        super().__init__(message)
        self.reason = reason


class HardwareError(HardLockError):
    """Raised when PC hardware identifiers cannot be read."""
