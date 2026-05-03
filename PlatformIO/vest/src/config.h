#pragma once

// ── MAX30102 ──────────────────────────────────────────────────
#define SDA1 16
#define SCL1 21
#define SDA2 4
#define SCL2 5

// ── GY-87 IMU (software I2C — GPIO 6/7 are free on quad-SPI modules)
#define IMU_SDA 6
#define IMU_SCL 7

// ── HW-611 / BMP280 (shares I2C Bus 1 with MAX30102 #1) ──────
#define BMP280_ADDR 0x76       // SDO tied to GND → address 0x76

// ── DHT11 Temperature & Humidity ──────────────────────────────
#define DHT11_PIN 17

// ── DS18B20 OneWire ───────────────────────────────────────────
#define ONE_WIRE_PIN 15

// ── AD8232 ECG ────────────────────────────────────────────────
#define ECG1_PIN 8
#define ECG2_PIN 9

// ── MAX9814 analog mic ────────────────────────────────────────
#define MIC_ANALOG_PIN 14

// ── INMP441 I2S digital mic ───────────────────────────────────
#define I2S_SCK_PIN 42
#define I2S_WS_PIN  45
#define I2S_SD_PIN  48

// ── Firmware version ──────────────────────────────────────────
// Bumped on every flashed change so the backend can detect what payload
// shape it's talking to (see app.py: handle_ble_notification reads `FW:`).
#define FW_VERSION                "3.8"

// ── BLE ───────────────────────────────────────────────────────
#define BLE_DEVICE_NAME           "Aegis_SpO2_Live"
#define SERVICE_UUID              "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID       "beb5483e-36e1-4688-b7f5-ea07361b26a8"
// High-rate ECG burst stream — separate characteristic so the vitals payload
// stays under MTU. Carries N raw ECG samples per notification.
#define ECG_BURST_CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a9"

// ── MAX30102 settings ─────────────────────────────────────────
#define SENSOR_BRIGHTNESS   255
#define SENSOR_AVG_SAMPLES  8
#define SENSOR_LED_MODE     2
#define SENSOR_SAMPLE_RATE  400
#define SENSOR_PULSE_WIDTH  411
#define SENSOR_ADC_RANGE    4096
#define CAL_SAMPLES         80
#define CAL_IR_THRESHOLD    4500

// ── Duty cycle timing (ms) ────────────────────────────────────
#define PPG_READ_INTERVAL    25
#define IMU_READ_INTERVAL    50
#define ECG_SAMPLE_INTERVAL  3       // 333 Hz raw sampling into the ring buffer
#define ECG_PROCESS_INTERVAL 200     // 5 Hz HR/QRS-flag refresh (was 1000)
#define ECG_BURST_INTERVAL   33      // ~30 Hz BLE notify → 11 samples/burst at 333 Hz
#define ECG_BURST_MAX        16      // hard cap on samples per burst packet
#define BLE_TX_INTERVAL      40      // 25 Hz vitals notify (was: every loop iter)
#define AUDIO_INTERVAL       1000
#define TEMP_READ_INTERVAL   5000
#define ENV_READ_INTERVAL    5000
#define PPG_ACTIVE_MS        10000
#define PPG_REST_MS          2000

// ── ECG warmup ────────────────────────────────────────────────
#define ECG_WARMUP_MS 10000

// ── Logging ───────────────────────────────────────────────────
// Levels: 0=ERR only, 1=+WARN, 2=+INFO (default), 3=+DEBUG (verbose).
// Higher levels compile more strings into flash; production build with -DLOG_LEVEL=0.
#ifndef LOG_LEVEL
  #define LOG_LEVEL 2
#endif

#if LOG_LEVEL >= 0
  #define LOG_ERR(fmt, ...)   Serial.printf("[ERR] "  fmt "\n", ##__VA_ARGS__)
#else
  #define LOG_ERR(...)        do {} while (0)
#endif
#if LOG_LEVEL >= 1
  #define LOG_WARN(fmt, ...)  Serial.printf("[WARN] " fmt "\n", ##__VA_ARGS__)
#else
  #define LOG_WARN(...)       do {} while (0)
#endif
#if LOG_LEVEL >= 2
  #define LOG_INFO(fmt, ...)  Serial.printf("[INFO] " fmt "\n", ##__VA_ARGS__)
#else
  #define LOG_INFO(...)       do {} while (0)
#endif
#if LOG_LEVEL >= 3
  #define LOG_DEBUG(fmt, ...) Serial.printf("[DBG] "  fmt "\n", ##__VA_ARGS__)
#else
  #define LOG_DEBUG(...)      do {} while (0)
#endif