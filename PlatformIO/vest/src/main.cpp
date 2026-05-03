#include <Arduino.h>
#include <esp_task_wdt.h>
#include "config.h"
#include "sensors/sensor_manager.h"
#include "ble/ble_manager.h"
#include "imu/imu_manager.h"
#include "temperature/temp_manager.h"
#include "ecg/ecg_manager.h"
#include "audio/audio_manager.h"
#include "environment/env_manager.h"

// 10-second task watchdog — any hung blocking call (I2C, DHT11, I2S read,
// BLE) triggers a clean reboot instead of locking the device forever.
// Fed once per loop iteration after all sensor reads are dispatched.
#define WDT_TIMEOUT_S 10

SensorManager sensors;
BLEManager    ble;
IMUManager    imu;
TempManager   temp;
ECGManager    ecg;
AudioManager  audio;
EnvManager    env;

SensorData      ppgData;
PostureData     postureData;
TempData        tempData;
ECGData         ecgData;
AudioData       audioData;
EnvironmentData envData;

unsigned long lastPPGRead    = 0;
unsigned long lastIMURead    = 0;
unsigned long lastTempRead   = 0;
unsigned long lastECGSample  = 0;
unsigned long lastECGProcess = 0;
unsigned long lastECGBurst   = 0;
unsigned long lastBLETX      = 0;
unsigned long lastAudioRead  = 0;
unsigned long lastEnvRead    = 0;
unsigned long ppgActiveStart = 0;
bool          ppgActive      = true;

void setup() {
  Serial.begin(115200);
  // Was delay(5000) "wait for serial" — pure boot tax. With ARDUINO_USB_CDC_ON_BOOT=0
  // (set in platformio.ini) Serial routes to UART0 which is ready immediately.
  delay(100);

  // Enable watchdog before anything blocking can run, so init hangs reboot
  // cleanly instead of bricking the device. true = panic+reboot on timeout.
  esp_task_wdt_init(WDT_TIMEOUT_S, true);
  esp_task_wdt_add(NULL);

  Serial.println("\n========================================");
  Serial.println("  AEGIS VEST — FULL SYSTEM v3.7         ");
  Serial.println("  GY-87 + HW-611 + DHT11               ");
  Serial.println("========================================\n");

  if (!sensors.begin()) {
    Serial.println("[MAIN] Fatal: no PPG sensors. Halting.");
    while (1) { delay(1000); }
  }

  if (!imu.begin())
    Serial.println("[MAIN] GY-87 IMU init failed — continuing without posture.");

  if (!env.begin(sensors.getBus1()))
    Serial.println("[MAIN] Environment sensors init failed — continuing.");

  temp.begin();
  ecg.begin();

  if (!audio.begin())
    Serial.println("[MAIN] Audio init failed — continuing.");

  ble.begin();

  ppgActiveStart = millis();

  Serial.println("\n[MAIN] All systems initialised.");
  Serial.println("[MAIN] System ready.\n");
}

void loop() {
  unsigned long now = millis();

  if (ppgActive && (now - ppgActiveStart >= PPG_ACTIVE_MS)) {
    ppgActive = false; ppgActiveStart = now;
  } else if (!ppgActive && (now - ppgActiveStart >= PPG_REST_MS)) {
    ppgActive = true;  ppgActiveStart = now;
  }

  if (ppgActive && (now - lastPPGRead >= PPG_READ_INTERVAL)) {
    sensors.read(ppgData);
    lastPPGRead = now;
  }

  if (now - lastECGSample >= ECG_SAMPLE_INTERVAL) {
    ecg.sample();
    lastECGSample = now;
  }

  if (now - lastIMURead >= IMU_READ_INTERVAL) {
    imu.read(postureData);
    lastIMURead = now;
  }

  if (now - lastECGProcess >= ECG_PROCESS_INTERVAL) {
    ecg.process(ecgData);
    lastECGProcess = now;
  }

  if (now - lastTempRead >= TEMP_READ_INTERVAL) {
    temp.read(tempData);
    lastTempRead = now;
  }

  if (now - lastEnvRead >= ENV_READ_INTERVAL) {
    env.read(envData);
    lastEnvRead = now;
  }

  if (now - lastAudioRead >= AUDIO_INTERVAL) {
    audio.read(audioData);
    lastAudioRead = now;
  }

  // Vitals notify on its own clock (25 Hz). Used to fire every loop iteration
  // (200+ Hz with mostly-stale data) which wasted CPU + radio + stole notify
  // slots from the ECG burst characteristic.
  if (now - lastBLETX >= BLE_TX_INTERVAL) {
    ble.transmit(ppgData, postureData, tempData, ecgData, audioData, envData);
    lastBLETX = now;
  }

  // Drain the ECG ring buffer at ~30 Hz on its own characteristic — this is
  // what gives the backend true 333 Hz instead of the 1 Hz scalar in vitals.
  if (now - lastECGBurst >= ECG_BURST_INTERVAL) {
    ble.transmitECGBurst(ecg);
    lastECGBurst = now;
  }

  // Pet the watchdog — only reached if no read above hung for >WDT_TIMEOUT_S.
  esp_task_wdt_reset();

  Serial.printf(
    "[DATA] PPG:%s IR:%lu | "
    "ECG L1:%.0f L2:%.0f L3:%.0f HR:%.1f (%s) | "
    "IMU P:%.1f R:%.1f %s%s | "
    "BMP %.1fhPa %.1fC | "
    "ENV %.1fhPa %.1fC H:%.0f%% %.1fC | "
    "T:%.1f/%.1f/%.1f | "
    "Audio A:%.0f D:%.0f\n",
    ppgActive ? "ON " : "OFF",
    ppgData.ira,
    ecgData.lead1_mv, ecgData.lead2_mv,
    ecgData.lead3_mv, ecgData.heartRate,
    ecgData.warmingUp ? "warmup" : ecgData.valid ? "ok" : "invalid",
    postureData.spinalAngle, postureData.lateralBend,
    postureData.poorPosture  ? "LEAN" : "ok",
    postureData.lateralAlert ? "/SIDE" : "",
    postureData.pressure_hPa, postureData.bmpTempC,
    envData.bmp280PressHpa, envData.bmp280TempC,
    envData.dht11Humidity,  envData.dht11TempC,
    tempData.leftAxilla, tempData.rightAxilla, tempData.cervical,
    audioData.analogRMS, audioData.digitalRMS);
}