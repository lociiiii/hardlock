"""
server.py
---------
DRM Flask server.

Endpoints:
  POST /register   — one-time device registration
  POST /launch     — validate fingerprint at launch; return AES key if valid
  GET  /status     — health check

Storage:
  SQLite database  (drm_database.db)  — simple, no extra dependencies.
  Schema:
    licenses(license_key TEXT PK,
             fingerprint  TEXT,        -- SHA-256 of PC_UUID+MB+MAC
             registered   INTEGER,     -- 0 or 1
             registered_at TEXT,
             launch_count  INTEGER)

Security notes (for a real deployment):
  • Serve over HTTPS (TLS).
  • Rate-limit /launch to prevent brute-force.
  • Store the AES license key in an HSM or at minimum an env variable,
    never hardcoded.
  • Rotate the shared secret between server and ESP32 periodically.

Dependencies:
    pip install flask
"""

import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, request

# ── Configuration ─────────────────────────────────────────────────────────────

# In production replace with a proper secrets manager / env variables.
# The AES key stored here is the one used to encrypt snake_game.enc
# (the result of `python encrypt_game.py --key <LICENSE_KEY>`).
# The server returns the raw license key; the launcher derives the AES
# key from it using SHA-256 — matching encrypt_game.py's derive_key().
LICENSES = {
    # license_key : aes_license_key  (same string here; separate if you want)
    "DEMO-LICENSE-KEY-1234": "DEMO-LICENSE-KEY-1234",
}

DB_PATH = os.environ.get("DRM_DB_PATH", "drm_database.db")
DEBUG   = os.environ.get("FLASK_DEBUG", "0") == "1"

app = Flask(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ── Database helpers ──────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                license_key   TEXT PRIMARY KEY,
                fingerprint   TEXT,
                registered    INTEGER DEFAULT 0,
                registered_at TEXT,
                launch_count  INTEGER DEFAULT 0
            )
        """)
        # Pre-populate known license keys (unregistered)
        for key in LICENSES:
            conn.execute("""
                INSERT OR IGNORE INTO licenses (license_key, registered)
                VALUES (?, 0)
            """, (key,))
        conn.commit()
    log.info("Database initialised at %s", DB_PATH)


# ── Fingerprint utility ───────────────────────────────────────────────────────

def compute_fingerprint(pc_uuid: str, mb_serial: str, esp_mac: str) -> str:
    """Must match register.py and launcher.py exactly."""
    raw = (pc_uuid + mb_serial + esp_mac).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ── Request helpers ───────────────────────────────────────────────────────────

def require_json(f):
    """Decorator: reject requests that aren't JSON."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 415
        return f(*args, **kwargs)
    return wrapper


def missing_fields(data: dict, fields: list) -> list:
    return [f for f in fields if not data.get(f)]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/status", methods=["GET"])
def status():
    """Health-check endpoint."""
    return jsonify({"status": "ok", "service": "DRM Server", "time": _now()})


@app.route("/register", methods=["POST"])
@require_json
def register():
    """
    One-time registration.
    Body: { license_key, pc_uuid, mb_serial, esp_mac, fingerprint }
    """
    data = request.get_json()
    missing = missing_fields(data, ["license_key", "pc_uuid", "mb_serial", "esp_mac"])
    if missing:
        return jsonify({"status": "error", "message": f"Missing fields: {missing}"}), 400

    lk        = data["license_key"]
    pc_uuid   = data["pc_uuid"].strip()
    mb_serial = data["mb_serial"].strip()
    esp_mac   = data["esp_mac"].strip().upper()

    # Verify license key exists
    if lk not in LICENSES:
        log.warning("Registration attempt with unknown license key: %s", lk)
        return jsonify({"status": "error", "message": "Invalid license key"}), 403

    # Server recomputes fingerprint independently — don't trust client's value
    fingerprint = compute_fingerprint(pc_uuid, mb_serial, esp_mac)

    with get_db() as conn:
        row = conn.execute("SELECT * FROM licenses WHERE license_key=?", (lk,)).fetchone()

        if row is None:
            return jsonify({"status": "error", "message": "License not found"}), 403

        if row["registered"]:
            # Already registered — check if same hardware
            if row["fingerprint"] == fingerprint:
                log.info("Re-registration with same hardware for key %s", lk)
                return jsonify({"status": "ok",
                                "message": "Already registered (same hardware)."})
            else:
                log.warning("Re-registration attempt with DIFFERENT hardware for key %s", lk)
                return jsonify({"status": "error",
                                "message": "License already registered to different hardware."}), 403

        # First-time registration
        conn.execute("""
            UPDATE licenses
               SET fingerprint=?, registered=1, registered_at=?
             WHERE license_key=?
        """, (fingerprint, _now(), lk))
        conn.commit()

    log.info("Registered license %s | fingerprint %s…", lk, fingerprint[:16])
    return jsonify({"status": "ok",
                    "message": "Registration successful. You may now launch the game."})


@app.route("/launch", methods=["POST"])
@require_json
def launch():
    """
    Called every time the user launches the game.
    Body: { license_key, pc_uuid, mb_serial, esp_mac }
    Returns the AES license key if fingerprint matches; 403 otherwise.
    """
    data = request.get_json()
    missing = missing_fields(data, ["license_key", "pc_uuid", "mb_serial", "esp_mac"])
    if missing:
        return jsonify({"status": "error", "message": f"Missing fields: {missing}"}), 400

    lk        = data["license_key"]
    pc_uuid   = data["mb_serial"].strip()   # intentional read of all three
    pc_uuid   = data["pc_uuid"].strip()
    mb_serial = data["mb_serial"].strip()
    esp_mac   = data["esp_mac"].strip().upper()

    if lk not in LICENSES:
        log.warning("Launch attempt with unknown license key: %s", lk)
        return jsonify({"status": "error", "message": "Invalid license key"}), 403

    fingerprint = compute_fingerprint(pc_uuid, mb_serial, esp_mac)

    with get_db() as conn:
        row = conn.execute("SELECT * FROM licenses WHERE license_key=?", (lk,)).fetchone()

        if row is None or not row["registered"]:
            return jsonify({"status": "error",
                            "message": "License not registered. Run register.py first."}), 403

        if row["fingerprint"] != fingerprint:
            log.warning("Fingerprint MISMATCH for key %s | expected %s… got %s…",
                        lk, row["fingerprint"][:16], fingerprint[:16])
            return jsonify({"status": "error",
                            "message": "Hardware fingerprint mismatch. Unauthorised device."}), 403

        # Fingerprint matches — bump launch counter and return the key
        conn.execute("UPDATE licenses SET launch_count=launch_count+1 WHERE license_key=?", (lk,))
        conn.commit()

    log.info("Authorised launch for key %s | total launches: %s",
             lk, row["launch_count"] + 1)

    return jsonify({
        "status":      "ok",
        "license_key": LICENSES[lk],   # launcher derives AES key from this
        "message":     "Launch authorised."
    })


# ── Utility ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print(" Hardware-Bound DRM — License Server")
    print("=" * 60)
    print(f" Database : {DB_PATH}")
    print(f" Endpoints: /register  /launch  /status")
    print("=" * 60)
    # In production: use gunicorn/waitress + HTTPS
    app.run(host="0.0.0.0", port=5000, debug=DEBUG)
