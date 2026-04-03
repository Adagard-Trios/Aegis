#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>

#include "config.h"
#include "sensors/piezo.h"
#include "sensors/microphone.h"
#include "sensors/film.h"
#include "ble/ble_manager.h"
#include "modes/fetal_mode.h"
#include "modes/abdominal_mode.h"

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

    // I2C
    Wire.begin(I2C_SDA, I2C_SCL);
    Wire.setClock(100000);

    // ADS1115
    if (!ads.begin(ADS_ADDR)) {
        Serial.println("[ERROR] ADS1115 not found! Halting.");
        while (1) delay(1000);
    }
    ads.setGain(GAIN_TWOTHIRDS);
    Serial.println("[ADS1115] Ready.");

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