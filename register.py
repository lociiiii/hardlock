"""
register.py
-----------
One-time device registration script (run by the end-user).

Reads:
  • PC UUID          — from Windows WMI (ComputerSystemProduct.UUID)
  • Motherboard ID   — from WMI (BaseBoard.SerialNumber)
  • ESP32 MAC        — from USB Serial using the DRM firmware protocol

Sends a registration request to the DRM server.
The server hashes these three values together and stores the fingerprint.

Usage:
    python register.py --port COM3 --server http://localhost:5000 --license-key YOUR_KEY

Dependencies:
    pip install pyserial requests wmi
"""

import argparse
import hashlib
import json
import sys
import time

import serial
import requests

# WMI is Windows-only — we import conditionally so the file can be linted
# on other platforms without crashing.
try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


# ── Hardware ID collection ────────────────────────────────────────────────────

def get_pc_uuid() -> str:
    """Return the Windows PC UUID via WMI."""
    if not WMI_AVAILABLE:
        raise EnvironmentError("wmi module not available. Run on Windows.")
    c = wmi.WMI()
    for item in c.Win32_ComputerSystemProduct():
        uid = item.UUID.strip()
        if uid and uid.upper() not in ("", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
                                        "00000000-0000-0000-0000-000000000000"):
            return uid
    raise RuntimeError("Could not read a valid PC UUID from WMI.")


def get_motherboard_serial() -> str:
    """Return the motherboard serial number via WMI."""
    if not WMI_AVAILABLE:
        raise EnvironmentError("wmi module not available. Run on Windows.")
    c = wmi.WMI()
    for item in c.Win32_BaseBoard():
        sn = item.SerialNumber.strip()
        if sn and sn.upper() not in ("", "TO BE FILLED BY O.E.M.",
                                     "NONE", "N/A", "DEFAULT_STRING"):
            return sn
    raise RuntimeError("Could not read a valid Motherboard serial from WMI.")


def get_esp32_mac(port: str, baud: int = 115200, timeout: float = 5.0) -> str:
    """
    Open the ESP32 over USB Serial, send GET_MAC, and return the MAC string.
    Expected response format: "MAC:AA:BB:CC:DD:EE:FF"
    """
    print(f"[*] Opening serial port {port} at {baud} baud…")
    with serial.Serial(port, baud, timeout=timeout) as ser:
        time.sleep(2)           # let ESP32 finish boot / reset
        ser.reset_input_buffer()

        ser.write(b"GET_MAC\n")
        ser.flush()

        deadline = time.time() + timeout
        while time.time() < deadline:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("MAC:"):
                mac = line[4:].strip()
                print(f"[+] ESP32 MAC: {mac}")
                return mac
            if line:
                print(f"    ESP32: {line}")   # show INFO/ERROR lines

    raise TimeoutError(f"No MAC response received from ESP32 on {port} within {timeout}s.")


# ── Fingerprint ───────────────────────────────────────────────────────────────

def compute_fingerprint(pc_uuid: str, mb_serial: str, esp_mac: str) -> str:
    """SHA-256(PC_UUID + MB_SERIAL + ESP_MAC)  — must match server logic."""
    raw = (pc_uuid + mb_serial + esp_mac).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ── Registration request ──────────────────────────────────────────────────────

def register(server_url: str, license_key: str,
             pc_uuid: str, mb_serial: str, esp_mac: str) -> None:
    fingerprint = compute_fingerprint(pc_uuid, mb_serial, esp_mac)
    print(f"[*] Device fingerprint (SHA-256): {fingerprint}")

    payload = {
    "license_key": license_key,
    "pc_uuid":     pc_uuid,
    "mb_serial":   mb_serial,
    "esp_mac":     esp_mac,
}

    url = server_url.rstrip("/") + "/devices/register"
    print(f"[*] Sending registration to {url}…")

    try:
        resp = requests.post(url, json=payload, timeout=15, 
                     headers={"X-API-Key": "hl_live_02f105b9e8482237fe100d78"})
        resp.raise_for_status()
        data = resp.json()
        print(f"[+] Server response: {json.dumps(data, indent=2)}")
        if data.get("status") == "ok":
            print("\n✅  Registration successful! You may now launch the game.")
        else:
            print(f"\n❌  Registration failed: {data.get('message', 'Unknown error')}")
    except requests.exceptions.ConnectionError:
        print(f"[!] Could not connect to server at {url}. Is it running?")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"[!] HTTP error: {e}")
        print(f"    Response body: {resp.text}")
        sys.exit(1)


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Register this PC + ESP32 combination with the DRM server."
    )
    parser.add_argument("--port",        required=True,
                        help="COM port of the ESP32 (e.g. COM3 or /dev/ttyUSB0)")
    parser.add_argument("--server",      default="http://localhost:5000",
                        help="Base URL of the DRM Flask server")
    parser.add_argument("--license-key", required=True,
                        help="License key provided with your purchase")
    args = parser.parse_args()

    print("=" * 60)
    print(" Hardware-Bound DRM — Device Registration")
    print("=" * 60)

    # Collect hardware identifiers
    print("\n[*] Reading PC UUID…")
    pc_uuid = get_pc_uuid()
    print(f"    PC UUID:      {pc_uuid}")

    print("[*] Reading Motherboard serial…")
    mb_serial = get_motherboard_serial()
    print(f"    MB Serial:    {mb_serial}")

    esp_mac = get_esp32_mac(args.port)

    # Register with server
    print()
    register(args.server, args.license_key, pc_uuid, mb_serial, esp_mac)


if __name__ == "__main__":
    main()
