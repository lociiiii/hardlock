"""Hardware identifier collection: PC UUID, motherboard serial, ESP32 MAC."""

from __future__ import annotations

import subprocess
from typing import Optional, Tuple
import sys
import time

import serial
import serial.tools.list_ports

from hardlock.exceptions import DeviceNotFoundError, HardwareError

try:
    import wmi

    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False

ESP32_BAUD = 115200
ESP32_BOOT_DELAY = 2.0
ESP32_RESPONSE_TIMEOUT = 5.0
PING_PROBE_TIMEOUT = 1.0

_INVALID_UUIDS = frozenset(
    {
        "",
        "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
        "00000000-0000-0000-0000-000000000000",
    }
)
_INVALID_MB_SERIALS = frozenset(
    {"", "TO BE FILLED BY O.E.M.", "NONE", "N/A", "DEFAULT_STRING"}
)


def get_pc_uuid() -> str:
    """Return the PC UUID via WMI (Windows) or dmidecode (Linux)."""
    if sys.platform == "win32":
        return _get_pc_uuid_wmi()
    return _get_pc_uuid_dmidecode()


def get_mb_serial() -> str:
    """Return the motherboard serial via WMI (Windows) or dmidecode (Linux)."""
    if sys.platform == "win32":
        return _get_mb_serial_wmi()
    return _get_mb_serial_dmidecode()


def _get_pc_uuid_wmi() -> str:
    if not WMI_AVAILABLE:
        raise HardwareError("wmi module not available. Install with: pip install wmi")
    client = wmi.WMI()
    for item in client.Win32_ComputerSystemProduct():
        uid = item.UUID.strip()
        if uid and uid.upper() not in _INVALID_UUIDS:
            return uid
    raise HardwareError("Could not read a valid PC UUID from WMI.")


def _get_mb_serial_wmi() -> str:
    if not WMI_AVAILABLE:
        raise HardwareError("wmi module not available. Install with: pip install wmi")
    client = wmi.WMI()
    for item in client.Win32_BaseBoard():
        serial = item.SerialNumber.strip()
        if serial and serial.upper() not in _INVALID_MB_SERIALS:
            return serial
    raise HardwareError("Could not read a valid motherboard serial from WMI.")


def _run_dmidecode(field: str) -> str:
    try:
        result = subprocess.run(
            ["dmidecode", "-s", field],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except FileNotFoundError as exc:
        raise HardwareError(
            "dmidecode not found. Install dmidecode or run on Windows with wmi."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise HardwareError(f"dmidecode failed for {field}: {exc.stderr.strip()}") from exc

    value = result.stdout.strip()
    if not value:
        raise HardwareError(f"dmidecode returned empty value for {field}.")
    return value


def _get_pc_uuid_dmidecode() -> str:
    uid = _run_dmidecode("system-uuid")
    if uid.upper() in _INVALID_UUIDS:
        raise HardwareError("Could not read a valid PC UUID from dmidecode.")
    return uid


def _get_mb_serial_dmidecode() -> str:
    serial_number = _run_dmidecode("baseboard-serial-number")
    if serial_number.upper() in _INVALID_MB_SERIALS:
        raise HardwareError("Could not read a valid motherboard serial from dmidecode.")
    return serial_number


def _serial_exchange(
    port: str,
    command: bytes,
    *,
    baud: int = ESP32_BAUD,
    timeout: float = ESP32_RESPONSE_TIMEOUT,
    boot_delay: float = ESP32_BOOT_DELAY,
    predicate,
) -> str:
    """Open a serial port, send a command, and return the first matching line."""
    with serial.Serial(port, baud, timeout=timeout) as ser:
        if boot_delay:
            time.sleep(boot_delay)
        ser.reset_input_buffer()
        ser.write(command)
        ser.flush()

        deadline = time.time() + timeout
        while time.time() < deadline:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue
            result = predicate(line)
            if result is not None:
                return result

    raise TimeoutError(f"No expected response from ESP32 on {port} within {timeout}s.")


def ping_esp32(port: str, *, timeout: float = PING_PROBE_TIMEOUT) -> bool:
    """Return True if the device on ``port`` responds to PING with PONG."""

    def _predicate(line: str) -> Optional[str]:
        return "" if line == "PONG" else None

    try:
        _serial_exchange(
            port,
            b"PING\n",
            timeout=timeout,
            boot_delay=0,
            predicate=_predicate,
        )
        return True
    except (TimeoutError, serial.SerialException, OSError):
        return False


def find_esp32_port(*, timeout: float = PING_PROBE_TIMEOUT) -> str:
    """Scan COM ports and return the first that responds to PING with PONG."""
    candidates = [info.device for info in serial.tools.list_ports.comports()]
    if not candidates:
        raise DeviceNotFoundError("No serial ports found.")

    for port in candidates:
        if ping_esp32(port, timeout=timeout):
            return port

    raise DeviceNotFoundError(
        "No ESP32 found. Connect the dongle and ensure firmware is flashed."
    )


def get_esp32_mac(
    port: Optional[str] = None,
    *,
    baud: int = ESP32_BAUD,
    timeout: float = ESP32_RESPONSE_TIMEOUT,
) -> Tuple[str, str]:
    """
    Read the ESP32 MAC address over USB serial.

    Returns ``(mac_address, port_used)``. Auto-detects the port when ``port`` is None.
    """
    resolved_port = port or find_esp32_port()

    def _predicate(line: str) -> Optional[str]:
        if line.startswith("MAC:"):
            return line[4:].strip()
        return None

    try:
        mac = _serial_exchange(
            resolved_port,
            b"GET_MAC\n",
            baud=baud,
            timeout=timeout,
            predicate=_predicate,
        )
    except serial.SerialException as exc:
        raise DeviceNotFoundError(
            f"Failed to open serial port {resolved_port}: {exc}"
        ) from exc

    return mac, resolved_port
