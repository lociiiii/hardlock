# 🔒 HardLock

**Hardware-Bound Software Licensing Platform**

> Protect any software by binding it to a specific PC + ESP32 hardware combination. No dongle = no access. Open source, self-hostable, and developer-friendly.

---

## What is HardLock?

HardLock is an open-source "Hardware Authentication as a Service" platform — think Auth0, but instead of authenticating *users*, it authenticates *physical machines*.

A developer integrates the HardLock SDK into their software. The software will only run when:
1. The exact registered **PC** is present (UUID + Motherboard Serial)
2. The exact registered **ESP32 dongle** is plugged in via USB (MAC address + NVS secret)

If either is missing or swapped — the software refuses to launch.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  DEVELOPER                                              │
│  encrypt_game.py → snake_game.enc  (AES-256-CBC)        │
└───────────────────────────┬─────────────────────────────┘
                            │ ships encrypted binary + launcher
                            ▼
┌─────────────────────────────────────────────────────────┐
│  USER — Registration (one time)                         │
│  register.py reads:                                     │
│    • PC UUID + Motherboard Serial  (Windows WMI)        │
│    • ESP32 MAC address             (USB Serial)         │
│  Computes: SHA-256(UUID + MB + MAC) → fingerprint       │
│  Sends to server → stored in database                   │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  USER — Every Launch                                    │
│  launcher.py:                                           │
│    1. Reads hardware IDs → recomputes fingerprint       │
│    2. POST /devices/verify → server checks match        │
│    3. On success → AES key released                     │
│    4. Decrypts software INTO RAM (never touches disk)   │
│    5. exec() game in isolated namespace                 │
│    6. Source bytes zeroed after compile                 │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Python 3.11 |
| Database | PostgreSQL 16 + SQLAlchemy (async) |
| Migrations | Alembic |
| Authentication | JWT (python-jose) |
| Key Management | Fernet (cryptography) |
| Encryption | AES-256-CBC (PyCryptodome) |
| Dashboard | React 18 + Vite + Tailwind CSS |
| Hardware | ESP32 (Arduino framework) |
| SDK | Python (pip installable) |

---

## Project Structure

```
hardlock/
├── server/               # FastAPI backend
│   ├── routers/          # auth, apps, licenses, devices, admin
│   ├── models/           # SQLAlchemy models
│   ├── core/             # fingerprint, keystore, security
│   └── alembic/          # database migrations
├── sdk/                  # pip install hardlock-sdk
│   └── hardlock/         # HardLock client class
├── dashboard/            # React developer dashboard
│   └── src/
│       ├── pages/        # Login, Apps, AppDetail, Logs
│       └── components/   # LicenseCard, DeviceTable, StatsBanner
├── esp32_firmware.ino    # ESP32 USB dongle firmware
├── snake_game.py         # Demo protected application
├── encrypt_game.py       # AES encryption tool
├── register.py           # Device registration client
└── launcher.py           # Hardware-verified game launcher
```

---

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/hardlock.git
cd hardlock
```

### 2. Set up the backend
```bash
cd server
pip install -r requirements.txt
cp ../.env.example .env   # edit with your DB credentials
python -m alembic upgrade head
python -m uvicorn main:app --reload --port 8000
```

### 3. Start the dashboard
```bash
cd dashboard
npm install
npm run dev
```
Open `http://localhost:5173`

### 4. Flash the ESP32
- Open `esp32_firmware.ino` in Arduino IDE
- Select board: **ESP32 Dev Module**
- Select your COM port
- Click Upload

### 5. Encrypt your software
```bash
python encrypt_game.py --input snake_game.py --output snake_game.enc --key YOUR_LICENSE_KEY
```

### 6. Register your device
```bash
python register.py --port COM7 --server http://localhost:8000 --license-key YOUR_KEY --api-key YOUR_API_KEY
```

### 7. Launch
```bash
python launcher.py --port COM7 --server http://localhost:8000 --license-key YOUR_KEY --api-key YOUR_API_KEY --game snake_game.enc
```

---

## How the Fingerprint Works

```python
fingerprint = SHA-256(PC_UUID + Motherboard_Serial + ESP32_MAC)
```

All three values must match the registered combination. Changing any one of them — swapping the ESP32, moving to a different PC, or replacing the motherboard — invalidates the fingerprint and blocks the launch.

---

## Security Design

| Threat | Mitigation |
|---|---|
| Copy software to another PC | Fingerprint includes PC UUID + Motherboard serial |
| Use a different ESP32 | MAC is burned in eFuse — unalterable |
| Read NVS secret off ESP32 flash | Flash encryption enabled — returns encrypted garbage |
| Intercept network traffic | Use HTTPS in production |
| Extract decrypted game from disk | Decryption happens in RAM only — never written to disk |
| Replay server response | Fingerprint recomputed live on every launch |
| Share license key | Key is bound to specific hardware fingerprint |

---

## ESP32 Serial Protocol

The ESP32 firmware responds to three commands over USB Serial (115200 baud):

| Command | Response |
|---|---|
| `PING` | `PONG` |
| `GET_MAC` | `MAC:AA:BB:CC:DD:EE:FF` |
| `GET_SECRET` | `SECRET:<64 hex chars>` |

---

## API Reference

### Authentication
```
POST /auth/register   { email, password }
POST /auth/login      { email, password } → JWT token
```

### Applications (JWT required)
```
GET  /apps            → list of developer's apps
POST /apps            { name, description } → { api_key }
GET  /apps/{id}       → app detail + licenses + stats
```

### Licenses (JWT required)
```
POST /licenses/generate  { app_id, count, max_devices }
POST /licenses/{key}/revoke
```

### Devices (API key required)
```
POST /devices/register  { license_key, pc_uuid, mb_serial, esp_mac }
POST /devices/verify    { license_key, pc_uuid, mb_serial, esp_mac }
                        → { authorized: true, session_token }
```

---

## SDK Usage

```python
from hardlock import HardLock, HardLockError

hl = HardLock(
    api_key="hl_live_xxxxxxxxxxxx",
    product_id="your-app-uuid",
)

try:
    session = hl.verify()
    print("Authorized — launching software")
    # run your protected code here

except HardLockError as e:
    print(f"Not authorized: {e}")
    sys.exit(1)
```

---

## vs Commercial Dongles

| Feature | HardLock | HASP HL | Wibu CodeMeter |
|---|---|---|---|
| Cost per unit | ~$5 (ESP32) | ~$50 | ~$80 |
| Open source | ✅ Yes | ❌ No | ❌ No |
| Self-hostable | ✅ Yes | ❌ No | ❌ No |
| Custom firmware | ✅ Yes | ❌ No | ❌ No |
| Flash encryption | ✅ Yes | ✅ Yes | ✅ Yes |
| Cloud dashboard | ✅ Yes | ✅ Yes | ✅ Yes |

---

## Future Work

- [ ] Node.js and C++ SDKs
- [ ] ESP32 challenge-response protocol (HMAC)
- [ ] Stripe billing integration
- [ ] PyInstaller + code signing for launcher
- [ ] Kubernetes deployment
- [ ] ML model weights protection demo
- [ ] Redis rate limiting
- [ ] Anomaly detection for piracy flagging

---

## Built With

This project was built as a final-year ECE major project demonstrating:
- Hardware security (ESP32, eFuse, NVS flash encryption)
- Cryptography (AES-256-CBC, SHA-256, Fernet key wrapping)
- Embedded systems (Arduino/ESP-IDF firmware)
- Full-stack development (FastAPI, PostgreSQL, React)
- Systems programming (in-memory execution, process isolation)

---

## License

MIT License — free to use, modify, and self-host.
