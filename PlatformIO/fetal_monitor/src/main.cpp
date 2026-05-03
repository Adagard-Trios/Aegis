#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include <esp_task_wdt.h>

#include "config.h"
#include "sensors/piezo.h"
#include "sensors/microphone.h"
#include "sensors/film.h"
#include "ble/ble_manager.h"
#include "modes/fetal_mode.h"
#include "modes/abdominal_mode.h"

// 10-second task watchdog — any hung blocking call (I2C, ADS read, BLE)
// triggers a clean reboot instead of locking the device forever. Fed in
// each loop iteration + during the ADS retry wait above.
#define WDT_TIMEOUT_S 10

// ── Global Objects ───────────────────────────
Adafruit_ADS1115  ads;
PiezoSensor       piezo;
MicrophoneSensor  mic(ads);
FilmSensor        film(ads);
BLEManager        bleManager;
FetalMode         fetalMode(bleManager);
AbdominalMode     abdominalMode(bleManager);

MonitorMode       currentMode = MODE_FETAL;
unsigned long     lastPublish = 0;

// ── Setup ────────────────────────────────────
void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("\n=============================");
    Serial.println(" Abdominal Monitor — Booting");
    Serial.println("=============================");

    // Enable the task watchdog before anything blocking can run, so we get
    // a clean reboot if init hangs. true = panic+reboot on timeout.
    esp_task_wdt_init(WDT_TIMEOUT_S, true);
    esp_task_wdt_add(NULL);

    // I2C — bump to 400 kHz (Fast Mode) so the four ADS1115 single-ended
    // reads per loop don't stack up on bus latency.
    Wire.begin(I2C_SDA, I2C_SCL);
    Wire.setClock(400000);

    // ADS1115 — retry indefinitely with a soft delay instead of a hard halt
    // so a transient I2C failure (loose connector at boot) recovers cleanly.
    // The watchdog (initialised below) is fed each cycle so we don't reboot
    // ourselves while waiting.
    int adsAttempt = 0;
    while (!ads.begin(ADS_ADDR)) {
        adsAttempt++;
        Serial.printf("[ADS1115] Init failed (attempt %d) — retrying in 2 s...\n", adsAttempt);
        for (int i = 0; i < 20; i++) {       // 20 × 100 ms = 2 s with WDT pets
            delay(100);
            esp_task_wdt_reset();
        }
    }
    ads.setGain(GAIN_TWOTHIRDS);
    // 860 SPS drops single-ended read latency from ~10 ms to ~5 ms; full
    // 4-channel pass goes from ~40 ms to ~20 ms with no accuracy loss for
    // our sub-400 Hz band of interest.
    ads.setDataRate(RATE_ADS1115_860SPS);
    Serial.println("[ADS1115] Ready (860 SPS, fast-mode I2C).");

    // Sensors
    piezo.begin();
    mic.begin();
    film.begin();

    // BLE
    bleManager.begin();

    Serial.println("[System] All modules initialised. Starting loop.");
}

// ── Main Loop ────────────────────────────────
void loop() {
    esp_task_wdt_reset();   // pet the watchdog every iteration

    // Check for mode change from BLE app
    MonitorMode requested = bleManager.getRequestedMode();
    if (requested != currentMode) {
        currentMode = requested;
        Serial.printf("[Mode] Switched to: %s\n",
                      currentMode == MODE_FETAL ? "FETAL" : "ABDOMINAL");
    }

    // Sample all sensors
    piezo.update();
    mic.update();
    film.update();

    // Get latest data
    PiezoData piezoData = piezo.getData();
    MicData   micData   = mic.getData();
    FilmData  filmData  = film.getData();

    // Run mode-specific event detection
    if (currentMode == MODE_FETAL) {
        fetalMode.process(piezoData, micData, filmData);
    } else {
        abdominalMode.process(piezoData, micData, filmData);
    }

    // Publish raw sensor data over BLE at fixed interval
    unsigned long now = millis();
    if (now - lastPublish >= SAMPLE_INTERVAL_MS) {
        lastPublish = now;
        bleManager.publishSensorData(piezoData, micData, filmData, currentMode);

        // Serial debug
        Serial.printf("[%s] P:%d/%d/%d/%d | M:%.2f/%.2f | F:%.0f%%/%.0f%%\n",
                      currentMode == MODE_FETAL ? "FET" : "ABD",
                      piezoData.raw[0], piezoData.raw[1],
                      piezoData.raw[2], piezoData.raw[3],
                      micData.volts[0], micData.volts[1],
                      filmData.pressurePercent[0], filmData.pressurePercent[1]);
    }
}