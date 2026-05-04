#include "ble_manager.h"
#include <Arduino.h>

class AegisBLECallbacks : public NimBLEServerCallbacks {
public:
  AegisBLECallbacks(BLEManager* m) : _m(m) {}
  void onConnect(NimBLEServer* s) override {
    _m->_connected = true;
    Serial.println("[BLE] Client connected.");
    NimBLEDevice::startAdvertising();
  }
  void onDisconnect(NimBLEServer* s) override {
    _m->_connected = false;
    Serial.println("[BLE] Disconnected. Re-advertising...");
    delay(500);
    NimBLEDevice::startAdvertising();
  }
private:
  BLEManager* _m;
};

BLEManager::BLEManager() {}

void BLEManager::begin() {
  NimBLEDevice::init(BLE_DEVICE_NAME);

  // Request a 512-byte MTU to handle large telemetry strings
  NimBLEDevice::setMTU(512);

  NimBLEServer* pServer = NimBLEDevice::createServer();
  pServer->setCallbacks(new AegisBLECallbacks(this));
  NimBLEService* pService = pServer->createService(SERVICE_UUID);
  _pChar = pService->createCharacteristic(
    CHARACTERISTIC_UUID,
    NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
  );
  // Dedicated high-rate ECG burst characteristic on the same service so the
  // backend can subscribe with one BleakClient connection.
  _pEcgChar = pService->createCharacteristic(
    ECG_BURST_CHARACTERISTIC_UUID,
    NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
  );
  pService->start();
  NimBLEAdvertising* pAdv = NimBLEDevice::getAdvertising();
  pAdv->addServiceUUID(SERVICE_UUID);
  pAdv->setScanResponse(true);
  NimBLEDevice::startAdvertising();
  Serial.printf("[BLE] Advertising as '%s'.\n", BLE_DEVICE_NAME);
}

void BLEManager::transmit(const SensorData       &ppg,
                           const PostureData      &posture,
                           const TempData         &temp,
                           const ECGData          &ecg,
                           const AudioData        &audio,
                           const EnvironmentData  &env,
                           bool        anomaly_fired,
                           const char* anomaly_reason) {
  if (!_connected || _pChar == nullptr) return;

  char payload[512];
  snprintf(payload, sizeof(payload),
    "IR1:%lu,Red1:%lu,IR2:%lu,Red2:%lu,IRA:%lu,RedA:%lu,"
    "T1:%.2f,T2:%.2f,"
    "TL:%.1f,TR:%.1f,TC:%.1f,"
    "UP:%.1f,UR:%.1f,LP:%.1f,LR:%.1f,"
    "UAX:%.3f,UAY:%.3f,UAZ:%.3f,UGX:%.2f,UGY:%.2f,UGZ:%.2f,"
    "LAX:%.3f,LAY:%.3f,LAZ:%.3f,LGX:%.2f,LGY:%.2f,LGZ:%.2f,"
    "SA:%.1f,LB:%.1f,PP:%d,LA:%d,"
    "BPR:%.1f,BTP:%.1f,"
    "EP:%.1f,ET:%.1f,HUM:%.1f,DT:%.1f,"
    // L1/L2/L3 raw samples are emitted on the ECG burst characteristic at
    // ~333 Hz; here we keep only the derived HR + status flags.
    "EHR:%.1f,EW:%d,EV:%d,"
    "ARMS:%.0f,DRMS:%.0f,SD:%d,"
    // AL = edge-anomaly flag set by the on-device anomaly_filter (Phase 4).
    // REASON is one of "none|hr_high|hr_low|spo2_low" — phone uses it
    // to fire a local notification immediately when offline.
    "AL:%d,REASON:%s,"
    "FW:" FW_VERSION,
    ppg.ir1, ppg.red1, ppg.ir2, ppg.red2, ppg.ira, ppg.reda,
    ppg.temp1, ppg.temp2,
    temp.leftAxilla, temp.rightAxilla, temp.cervical,
    posture.upper.pitch, posture.upper.roll,
    posture.lower.pitch, posture.lower.roll,
    posture.upper.accelX, posture.upper.accelY, posture.upper.accelZ,
    posture.upper.gyroX,  posture.upper.gyroY,  posture.upper.gyroZ,
    posture.lower.accelX, posture.lower.accelY, posture.lower.accelZ,
    posture.lower.gyroX,  posture.lower.gyroY,  posture.lower.gyroZ,
    posture.spinalAngle, posture.lateralBend,
    posture.poorPosture  ? 1 : 0,
    posture.lateralAlert ? 1 : 0,
    posture.pressure_hPa, posture.bmpTempC,
    env.bmp280PressHpa, env.bmp280TempC,
    env.dht11Humidity,  env.dht11TempC,
    ecg.heartRate,
    ecg.warmingUp ? 1 : 0, ecg.valid ? 1 : 0,
    audio.analogRMS, audio.digitalRMS,
    audio.soundDetected ? 1 : 0,
    anomaly_fired ? 1 : 0,
    anomaly_reason ? anomaly_reason : "none");

  _pChar->setValue((uint8_t*)payload, strlen(payload));
  _pChar->notify();
}

void BLEManager::transmitECGBurst(ECGManager &ecg) {
  if (!_connected || _pEcgChar == nullptr) return;

  float lead1[ECG_BURST_MAX];
  float lead2[ECG_BURST_MAX];
  int n = ecg.drainSamples(lead1, lead2, ECG_BURST_MAX);
  if (n <= 0) return;

  // Compact ASCII payload: "EB1:1234|2345|...,EB2:1234|2345|..."
  // 16 samples × max 5 chars + delimiters fits comfortably under MTU.
  char payload[256];
  int  off = snprintf(payload, sizeof(payload), "EB1:");
  for (int i = 0; i < n; i++) {
    off += snprintf(payload + off, sizeof(payload) - off,
                    "%d%s", (int)lead1[i], (i < n - 1) ? "|" : "");
    if (off >= (int)sizeof(payload) - 8) break;  // safety margin for trailing fields
  }
  off += snprintf(payload + off, sizeof(payload) - off, ",EB2:");
  for (int i = 0; i < n; i++) {
    off += snprintf(payload + off, sizeof(payload) - off,
                    "%d%s", (int)lead2[i], (i < n - 1) ? "|" : "");
    if (off >= (int)sizeof(payload) - 1) break;
  }

  _pEcgChar->setValue((uint8_t*)payload, strlen(payload));
  _pEcgChar->notify();
}
