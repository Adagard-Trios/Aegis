#include <Arduino.h>
#include "config.h"
#include "sensors/sensor_manager.h"
#include "ble/ble_manager.h"
#include "imu/imu_manager.h"
#include "temperature/temp_manager.h"
#include "ecg/ecg_manager.h"
#include "audio/audio_manager.h"
#include "environment/env_manager.h"

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
unsigned long lastAudioRead  = 0;
unsigned long lastEnvRead    = 0;
unsigned long ppgActiveStart = 0;
bool          ppgActive      = true;

void setup() {
  Serial.begin(115200);
  delay(5000);

  Serial.println("\n========================================");
  Serial.println("  AEGIS VEST — FULL SYSTEM v3.2         ");
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

  ble.transmit(ppgData, postureData, tempData, ecgData, audioData, envData);

  // Drain the ECG ring buffer at ~30 Hz on its own characteristic — this is
  // what gives the backend true 333 Hz instead of the 1 Hz scalar in vitals.
  if (now - lastECGBurst >= ECG_BURST_INTERVAL) {
    ble.transmitECGBurst(ecg);
    lastECGBurst = now;
  }

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