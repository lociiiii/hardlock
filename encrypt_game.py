"""
encrypt_game.py
---------------
Developer-side tool.
AES-256-CBC encrypts snake_game.py (or any Python file) using a license key.

Output: snake_game.enc  — the encrypted binary you ship to end-users.

Usage:
    python encrypt_game.py --input snake_game.py --output snake_game.enc --key YOUR_LICENSE_KEY

Dependencies:
    pip install pycryptodome
"""

import argparse
import hashlib
import os
import json
import base64

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


# ── Helpers ──────────────────────────────────────────────────────────────────

def derive_key(license_key: str) -> bytes:
    """
    Derive a 32-byte AES key from an arbitrary license key string
    using SHA-256.  The same derivation is performed on the server
    when the decryption key is released.
    """
    return hashlib.sha256(license_key.encode("utf-8")).digest()


def encrypt_file(input_path: str, output_path: str, license_key: str) -> None:
    # Read plaintext source
    with open(input_path, "rb") as f:
        plaintext = f.read()

    key = derive_key(license_key)

    # Random 16-byte IV — unique per encryption run
    iv = os.urandom(16)

    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))

    # Package: store IV + ciphertext together in a simple JSON envelope
    # so the launcher can unpack both fields cleanly.
    envelope = {
        "iv":         base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
    }
    payload = json.dumps(envelope).encode("utf-8")

    with open(output_path, "wb") as f:
        f.write(payload)

    print(f"[+] Encrypted '{input_path}' → '{output_path}'")
    print(f"    AES-256-CBC | IV: {iv.hex()} | Ciphertext size: {len(ciphertext)} bytes")
    print(f"    License key hash (first 8 bytes): {key[:8].hex()}…")
    print()
    print("  Ship to users:")
    print(f"    • {output_path}  (encrypted game)")
    print( "    • launcher.py   (handles decryption + execution)")
    print()
    print("  Store ONLY on the license server:")
    print(f"    • License key: {license_key}")


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="AES-256-CBC encrypt a Python game file for hardware-bound DRM."
    )
    parser.add_argument("--input",  default="snake_game.py",  help="Path to plaintext game file")
    parser.add_argument("--output", default="snake_game.enc", help="Path to write encrypted output")
    parser.add_argument("--key",    required=True,            help="License key (secret, server-side only)")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[!] Input file not found: {args.input}")
        return

    encrypt_file(args.input, args.output, args.key)


if __name__ == "__main__":
    main()
