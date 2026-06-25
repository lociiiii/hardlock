# HardLock Python SDK

Hardware-bound software licensing for Python applications. Bind your software to a specific PC + ESP32 USB dongle combination with a single SDK call.

## Installation

```bash
# From the repo root
pip install -e ./sdk

# Windows (WMI for PC UUID / motherboard serial)
pip install -e "./sdk[windows]"
```

## Quick start

```python
from hardlock import HardLock, HardLockError

hl = HardLock(
    api_key="hl_live_xxxxxxxxxxxx",       # from HardLock dashboard
    license_key="HLCK-XXXX-XXXX-XXXX",    # end-user license
    product_id="app-uuid-here",           # application UUID
    esp_port=None,                        # None = auto-detect ESP32
)

try:
    session = hl.verify()
    print(f"Authorized. Session valid for {session.expires_in}s")
    # run protected code here

except HardLockError as e:
    print(f"Not authorized: {e}")
```

## Device registration

Run once per machine before verification:

```python
result = hl.register(label="Pretesh's home PC")
print(result)  # {"status": "registered", "device_id": "..."}
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `HARDLOCK_SERVER_URL` | API base URL (default: `http://localhost:8000`) |

## Hardware requirements

- **Windows:** `wmi` package reads PC UUID and motherboard serial via WMI
- **Linux:** `dmidecode` must be installed and readable (often requires root)
- **ESP32:** USB dongle flashed with HardLock firmware, responding to `PING` / `GET_MAC`

## ESP32 auto-detection

When `esp_port=None`, the SDK scans all serial ports and sends `PING\n`. The first port that replies `PONG\n` is used for `GET_MAC\n`.

To pin a port explicitly:

```python
hl = HardLock(..., esp_port="COM3")
```

## Fingerprint algorithm

The SDK computes fingerprints identically to the HardLock server:

```python
from hardlock import compute_fingerprint

fp = compute_fingerprint(pc_uuid, mb_serial, esp_mac)
# SHA-256(pc_uuid.strip() + mb_serial.strip() + esp_mac.strip().upper())
```

## Exceptions

| Exception | When |
|-----------|------|
| `HardLockError` | Base class for all SDK errors |
| `DeviceNotFoundError` | ESP32 not found or serial communication failed |
| `UnauthorizedError` | Server denied verification (`reason` attribute set) |
| `HardwareError` | PC UUID or motherboard serial could not be read |

## API endpoints used

| Method | Endpoint | Auth |
|--------|----------|------|
| `POST` | `/devices/register` | `X-API-Key` header |
| `POST` | `/devices/verify` | `X-API-Key` header |
