"""HardLock Python SDK — hardware-bound software licensing."""

from hardlock.client import HardLock, HardLockSession
from hardlock.exceptions import (
    DeviceNotFoundError,
    HardLockError,
    HardwareError,
    UnauthorizedError,
)
from hardlock.fingerprint import compute_fingerprint
from hardlock.hardware import find_esp32_port, get_esp32_mac, get_mb_serial, get_pc_uuid

__all__ = [
    "HardLock",
    "HardLockSession",
    "HardLockError",
    "DeviceNotFoundError",
    "UnauthorizedError",
    "HardwareError",
    "compute_fingerprint",
    "find_esp32_port",
    "get_esp32_mac",
    "get_mb_serial",
    "get_pc_uuid",
]

__version__ = "0.1.0"
