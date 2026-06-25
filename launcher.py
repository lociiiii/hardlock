"""
launcher.py
-----------
End-user game launcher for the hardware-bound DRM system.
"""

import argparse
import base64
import hashlib
import json
import os
import sys
import time
import types

import serial
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

try:
    import wmi
    WMI_AVAILABLE = True
except ImportError:
    WMI_AVAILABLE = False


# ── Hardware ID collection ────────────────────────────────────────────────────

def get_pc_uuid() -> str:
    if not WMI_AVAILABLE:
        raise EnvironmentError("wmi module not available. Must run on Windows.")
    c = wmi.WMI()
    for item in c.Win32_ComputerSystemProduct():
        uid = item.UUID.strip()
        if uid and uid.upper() not in ("", "FFFFFFFF-FFFF-FFFF-FFFF-FFFFFFFFFFFF",
                                        "00000000-0000-0000-0000-000000000000"):
            return uid
    raise RuntimeError("Could not read PC UUID from WMI.")


def get_motherboard_serial() -> str:
    if not WMI_AVAILABLE:
        raise EnvironmentError("wmi module not available. Must run on Windows.")
    c = wmi.WMI()
    for item in c.Win32_BaseBoard():
        sn = item.SerialNumber.strip()
        if sn and sn.upper() not in ("", "TO BE FILLED BY O.E.M.",
                                     "NONE", "N/A", "DEFAULT_STRING"):
            return sn
    raise RuntimeError("Could not read Motherboard serial from WMI.")


def get_esp32_mac(port: str, baud: int = 115200, timeout: float = 5.0) -> str:
    with serial.Serial(port, baud, timeout=timeout) as ser:
        time.sleep(2)
        ser.reset_input_buffer()
        ser.write(b"GET_MAC\n")
        ser.flush()
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if line.startswith("MAC:"):
                return line[4:].strip()
    raise TimeoutError(f"No MAC response from ESP32 on {port}.")


# ── Fingerprint ───────────────────────────────────────────────────────────────

def compute_fingerprint(pc_uuid: str, mb_serial: str, esp_mac: str) -> str:
    raw = (pc_uuid + mb_serial + esp_mac).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ── Server communication ──────────────────────────────────────────────────────

def request_launch_key(server_url: str, license_key: str,
                       pc_uuid: str, mb_serial: str, esp_mac: str,
                       api_key: str) -> str:
    payload = {
        "license_key": license_key,
        "pc_uuid":     pc_uuid,
        "mb_serial":   mb_serial,
        "esp_mac":     esp_mac.upper(),
    }
    url = server_url.rstrip("/") + "/devices/verify"
    try:
        resp = requests.post(url, json=payload, timeout=15,
                             headers={"X-API-Key": api_key})
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Cannot reach DRM server at {url}.")

    if resp.status_code == 403:
        data = resp.json()
        raise PermissionError(f"Server denied launch: {data.get('reason', 'Unauthorised')}")

    resp.raise_for_status()
    data = resp.json()

    if not data.get("authorized"):
        raise PermissionError(f"Not authorized: {data.get('reason', 'Unknown')}")

    # Return the license key itself — used to derive the AES decryption key
    return license_key


# ── AES decryption (in RAM) ───────────────────────────────────────────────────

def derive_aes_key(license_key: str) -> bytes:
    return hashlib.sha256(license_key.encode("utf-8")).digest()


def decrypt_game(enc_path: str, license_key: str) -> bytes:
    with open(enc_path, "rb") as f:
        envelope = json.loads(f.read())

    iv         = base64.b64decode(envelope["iv"])
    ciphertext = base64.b64decode(envelope["ciphertext"])
    aes_key    = derive_aes_key(license_key)

    cipher    = AES.new(aes_key, AES.MODE_CBC, iv)
    plaintext = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return plaintext


# ── In-memory execution ───────────────────────────────────────────────────────

def _zero_bytes(data: bytearray) -> None:
    for i in range(len(data)):
        data[i] = 0


def run_decrypted(source_bytes: bytes) -> None:
    source_ba = bytearray(source_bytes)
    code = compile(source_bytes, "<drm_protected_game>", "exec")

    game_module = types.ModuleType("snake_game")
    game_module.__file__    = "<drm_protected_game>"
    game_module.__package__ = ""

    _zero_bytes(source_ba)
    del source_bytes, source_ba

    exec(code, game_module.__dict__)

    if hasattr(game_module, "run_game") and callable(game_module.run_game):
        game_module.run_game()


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Hardware-bound DRM launcher."
    )
    parser.add_argument("--port",        required=True,  help="COM port of ESP32 (e.g. COM7)")
    parser.add_argument("--server",      default="http://localhost:8000", help="DRM server URL")
    parser.add_argument("--license-key", required=True,  help="Your license key")
    parser.add_argument("--game",        default="snake_game.enc", help="Encrypted game file")
    parser.add_argument("--api-key", required=True, help="HardLock API key from dashboard")
    args = parser.parse_args()

    if not os.path.isfile(args.game):
        print(f"[!] Encrypted game file not found: {args.game}")
        sys.exit(1)

    print("=" * 55)
    print(" Hardware-Bound DRM — Game Launcher")
    print("=" * 55)

    # Step 1 — collect hardware IDs
    print("\n[1/4] Reading hardware identifiers…")
    try:
        pc_uuid   = get_pc_uuid()
        mb_serial = get_motherboard_serial()
    except Exception as e:
        print(f"[!] Failed to read PC hardware IDs: {e}")
        sys.exit(1)

    try:
        esp_mac = get_esp32_mac(args.port)
    except Exception as e:
        print(f"[!] Failed to read ESP32 MAC: {e}")
        sys.exit(1)

    fp = compute_fingerprint(pc_uuid, mb_serial, esp_mac)
    print(f"    Fingerprint: {fp[:24]}…")

    # Step 2 — verify with server
    print("\n[2/4] Verifying hardware with DRM server…")
    try:
        license_key = request_launch_key(
            args.server, args.license_key,
            pc_uuid, mb_serial, esp_mac,
            args.api_key
        )
    except PermissionError as e:
        print(f"\n❌  {e}")
        print("    Ensure this PC + ESP32 are registered (run register.py).")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Server error: {e}")
        sys.exit(1)

    print("    ✅  Hardware verified. Launch authorised.")

    # Step 3 — decrypt game into RAM
    print("\n[3/4] Decrypting game into memory (no disk write)…")
    try:
        game_source = decrypt_game(args.game, license_key)
    except Exception as e:
        print(f"[!] Decryption failed: {e}")
        sys.exit(1)
    print(f"    Decrypted {len(game_source):,} bytes of game source.")

    # Step 4 — run the game
    print("\n[4/4] Starting Snake…\n")
    run_decrypted(game_source)


if __name__ == "__main__":
    main()