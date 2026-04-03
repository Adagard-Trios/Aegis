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
                           const EnvironmentData  &env) {
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
    "L1:%.0f,L2:%.0f,L3:%.0f,EHR:%.1f,EW:%d,EV:%d,"
    "ARMS:%.0f,DRMS:%.0f,SD:%d",
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
    ecg.lead1_mv, ecg.lead2_mv, ecg.lead3_mv,
    ecg.heartRate,
    ecg.warmingUp ? 1 : 0, ecg.valid ? 1 : 0,
    audio.analogRMS, audio.digitalRMS,
    audio.soundDetected ? 1 : 0);

  _pChar->setValue((uint8_t*)payload, strlen(payload));
  _pChar->notify();
}
