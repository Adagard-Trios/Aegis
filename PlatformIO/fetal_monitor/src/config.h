#pragma once

// ─────────────────────────────────────────────
// PIN DEFINITIONS
// ─────────────────────────────────────────────

// CD74HC4067 Multiplexer
#define MUX_SIG     32
#define MUX_S0      25
#define MUX_S1      26
#define MUX_S2      27
#define MUX_S3      14

// ADS1115 I2C
#define I2C_SDA     21
#define I2C_SCL     22
#define ADS_ADDR    0x48

// ADS1115 Channel Assignments
#define ADS_MIC1    0   // MAX9814 Microphone 1
#define ADS_MIC2    1   // MAX9814 Microphone 2
#define ADS_FILM1   2   // Resistive Film Sensor 1
#define ADS_FILM2   3   // Resistive Film Sensor 2

// MUX Channel Assignments
// Piezo 1 is on Ch4 (C0 was faulty, rerouted)
#define MUX_PIEZO1  4
#define MUX_PIEZO2  1
#define MUX_PIEZO3  2
#define MUX_PIEZO4  3

// ─────────────────────────────────────────────
// SYSTEM CONSTANTS
// ─────────────────────────────────────────────

#define SAMPLE_INTERVAL_MS      250     // Main loop publish rate
#define ADC_RESOLUTION          12      // ESP32 ADC bits (0-4095)
#define ADC_VREF                3.3f    // Reference voltage
#define ROLLING_WINDOW          20      // Samples for rolling average

// Piezo thresholds (raw ADC units from 0-4095, midpoint ~2047)
#define PIEZO_KICK_THRESHOLD    400     // Delta from baseline to count as kick
#define PIEZO_MOVEMENT_THRESHOLD 250    // Delta for abdominal wall movement

// Microphone thresholds (volts)
#define MIC_AUDIO_THRESHOLD     0.15f   // Delta from baseline = sound event
#define MIC_BOWEL_MIN_FREQ_HZ   20      // Bowel sounds frequency range start
#define MIC_BOWEL_MAX_FREQ_HZ   600     // Bowel sounds frequency range end
#define MIC_HEART_MIN_FREQ_HZ   0       // Fetal heart tone range start
#define MIC_HEART_MAX_FREQ_HZ   200     // Fetal heart tone range end

// Film sensor thresholds (volts)
#define FILM_CONTRACTION_THRESHOLD  1.2f  // Voltage rise = contraction
#define FILM_PRESSURE_THRESHOLD     0.8f  // Voltage rise = abdominal pressure

// ─────────────────────────────────────────────
// BLE CONFIGURATION
// ─────────────────────────────────────────────

#define BLE_DEVICE_NAME         "AbdomenMonitor"

// Service UUID
#define BLE_SERVICE_UUID        "12345678-1234-1234-1234-123456789abc"

// Characteristic UUIDs
#define BLE_CHAR_SENSOR_DATA    "12345678-1234-1234-1234-123456789ab1"  // Raw sensor stream
#define BLE_CHAR_EVENTS         "12345678-1234-1234-1234-123456789ab2"  // Detected events
#define BLE_CHAR_MODE           "12345678-1234-1234-1234-123456789ab3"  // Mode read/write

// ─────────────────────────────────────────────
// OPERATING MODES
// ─────────────────────────────────────────────

enum MonitorMode {
    MODE_FETAL      = 0,
    MODE_ABDOMINAL  = 1
};

// ─────────────────────────────────────────────
// LOGGING
// ─────────────────────────────────────────────
// Levels: 0=ERR only, 1=+WARN, 2=+INFO (default), 3=+DEBUG (verbose).
// Production build: -DLOG_LEVEL=0 in build_flags.
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