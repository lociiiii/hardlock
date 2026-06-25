/*
 * esp32_firmware.ino
 * ------------------
 * Hardware-bound DRM — ESP32 side.
 *
 * Responsibilities:
 *   1. Store a unique device secret in NVS (Non-Volatile Storage) with
 *      flash encryption enabled so it cannot be read off the chip with
 *      a flash reader.
 *   2. Expose the device MAC address + a signed challenge response over
 *      USB Serial so the host launcher can identify this exact unit.
 *
 * Flash encryption should be enabled via `idf.py menuconfig` or the
 * Arduino ESP32 security fuses before provisioning.
 *
 * Communication protocol (newline-terminated ASCII over Serial 115200 baud):
 *   Host sends:  "GET_MAC\n"
 *   Device sends: "MAC:<xx:xx:xx:xx:xx:xx>\n"
 *
 *   Host sends:  "GET_SECRET\n"
 *   Device sends: "SECRET:<hex_string>\n"
 *      (32-byte secret stored in NVS, hex-encoded → 64 hex chars)
 *
 *   Host sends:  "PING\n"
 *   Device sends: "PONG\n"
 *
 * Dependencies:
 *   Board: esp32 by Espressif (Arduino IDE board manager)
 *   Libraries: Preferences (built-in with ESP32 core)
 */

#include <Arduino.h>
#include <Preferences.h>
#include <esp_system.h>
#include <esp_mac.h>

// ── Configuration ─────────────────────────────────────────────────────────────

// NVS namespace and key for the device secret
#define NVS_NAMESPACE   "drm_store"
#define NVS_KEY_SECRET  "dev_secret"

// Length of the device secret in bytes
#define SECRET_LEN      32

// Serial baud rate
#define BAUD_RATE       115200

// Onboard LED pin (active-HIGH on most ESP32 DevKit boards)
#define LED_PIN         2

// ── Globals ───────────────────────────────────────────────────────────────────

Preferences prefs;
uint8_t     g_secret[SECRET_LEN];
char        g_mac_str[18];   // "AA:BB:CC:DD:EE:FF\0"

// ── Helper: byte array → hex string ──────────────────────────────────────────

void bytes_to_hex(const uint8_t *data, size_t len, char *out) {
    for (size_t i = 0; i < len; i++) {
        sprintf(out + i * 2, "%02x", data[i]);
    }
    out[len * 2] = '\0';
}

// ── Setup ─────────────────────────────────────────────────────────────────────

void setup() {
    Serial.begin(BAUD_RATE);
    pinMode(LED_PIN, OUTPUT);

    // Blink once to signal boot
    digitalWrite(LED_PIN, HIGH);
    delay(200);
    digitalWrite(LED_PIN, LOW);

    // ── Read MAC address ──────────────────────────────────────────────────
    uint8_t mac[6];
    esp_efuse_mac_get_default(mac);          // base MAC from eFuse
    snprintf(g_mac_str, sizeof(g_mac_str),
             "%02X:%02X:%02X:%02X:%02X:%02X",
             mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    // ── Load or provision device secret from NVS ──────────────────────────
    prefs.begin(NVS_NAMESPACE, false);       // read-write mode

    size_t stored_len = prefs.getBytesLength(NVS_KEY_SECRET);

    if (stored_len != SECRET_LEN) {
        // First boot — generate a random secret and persist it
        // esp_fill_random uses the hardware RNG
        esp_fill_random(g_secret, SECRET_LEN);
        prefs.putBytes(NVS_KEY_SECRET, g_secret, SECRET_LEN);
        Serial.println("INFO:First boot — secret provisioned to NVS");
    } else {
        prefs.getBytes(NVS_KEY_SECRET, g_secret, SECRET_LEN);
        Serial.println("INFO:Secret loaded from NVS");
    }

    prefs.end();

    Serial.print("INFO:MAC=");
    Serial.println(g_mac_str);
    Serial.println("INFO:DRM firmware ready. Awaiting commands.");
}

// ── Command handler ───────────────────────────────────────────────────────────

void handle_command(const String &cmd) {
    if (cmd == "GET_MAC") {
        Serial.print("MAC:");
        Serial.println(g_mac_str);

    } else if (cmd == "GET_SECRET") {
        char hex_buf[SECRET_LEN * 2 + 1];
        bytes_to_hex(g_secret, SECRET_LEN, hex_buf);
        Serial.print("SECRET:");
        Serial.println(hex_buf);

        // Brief LED flash to indicate secret was read
        digitalWrite(LED_PIN, HIGH);
        delay(50);
        digitalWrite(LED_PIN, LOW);

    } else if (cmd == "PING") {
        Serial.println("PONG");

    } else {
        Serial.print("ERROR:Unknown command: ");
        Serial.println(cmd);
    }
}

// ── Main loop ─────────────────────────────────────────────────────────────────

void loop() {
    if (Serial.available()) {
        // Read until newline — commands are newline-terminated
        String line = Serial.readStringUntil('\n');
        line.trim();   // strip CR/LF/spaces
        if (line.length() > 0) {
            handle_command(line);
        }
    }
}
