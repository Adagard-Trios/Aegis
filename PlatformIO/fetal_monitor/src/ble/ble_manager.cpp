#include "ble_manager.h"

void ModeWriteCallback::onWrite(NimBLECharacteristic* characteristic) {
    std::string val = characteristic->getValue();
    if (val.length() > 0) {
        int m = atoi(val.c_str());
        _mode = (m == 1) ? MODE_ABDOMINAL : MODE_FETAL;
        Serial.printf("[BLE] Mode changed to: %s\n",
                      _mode == MODE_FETAL ? "FETAL" : "ABDOMINAL");
    }
}

BLEManager::BLEManager() : _connected(false), _requestedMode(MODE_FETAL) {}

void BLEManager::begin() {
    NimBLEDevice::init(BLE_DEVICE_NAME);
    NimBLEDevice::setMTU(247);   // request larger MTU for the compact payload

    _server = NimBLEDevice::createServer();
    _server->setCallbacks(this);

    NimBLEService* service = _server->createService(BLE_SERVICE_UUID);

    // Sensor data characteristic — notify (NimBLE auto-creates the CCCD)
    _charSensorData = service->createCharacteristic(
        BLE_CHAR_SENSOR_DATA,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

    // Events characteristic — notify
    _charEvents = service->createCharacteristic(
        BLE_CHAR_EVENTS,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::NOTIFY
    );

    // Mode characteristic — read/write
    _charMode = service->createCharacteristic(
        BLE_CHAR_MODE,
        NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::WRITE
    );
    _charMode->setCallbacks(new ModeWriteCallback(_requestedMode));
    _charMode->setValue("0");   // default: fetal mode

    service->start();

    NimBLEAdvertising* advertising = NimBLEDevice::getAdvertising();
    advertising->addServiceUUID(BLE_SERVICE_UUID);
    advertising->setScanResponse(true);
    NimBLEDevice::startAdvertising();

    Serial.println("[BLE] (NimBLE) Advertising started. Device: " BLE_DEVICE_NAME);
}

void BLEManager::onConnect(NimBLEServer* server) {
    _connected = true;
    Serial.println("[BLE] Client connected.");
}

void BLEManager::onDisconnect(NimBLEServer* server) {
    _connected = false;
    Serial.println("[BLE] Client disconnected. Restarting advertising...");
    NimBLEDevice::startAdvertising();
}

bool BLEManager::isConnected() {
    return _connected;
}

MonitorMode BLEManager::getRequestedMode() {
    return _requestedMode;
}

void BLEManager::publishSensorData(PiezoData& piezo, MicData& mic, FilmData& film, MonitorMode mode) {
    if (!_connected) return;

    // Compact comma-separated key:value payload (matches the vest's vitals
    // format). Was a JsonDocument heap-alloc'd per call which fragmented
    // RAM over hours; this version uses one stack-allocated 256 B buffer
    // and is ~5× faster to parse on the backend.
    //
    // Field map (kept stable so the backend just needs to swap json.loads
    // for the same comma-split parser the vest already uses):
    //   ts:millis, mode:0|1
    //   pz0..pz3        — raw piezo
    //   k0..k3          — kick flags
    //   m0..m3          — movement flags
    //   mv0,mv1         — mic volts
    //   ht0,ht1         — heart-tone flags
    //   bs0,bs1         — bowel-sound flags
    //   fp0,fp1         — film pressure %
    //   c0,c1           — contraction flags
    char payload[256];
    snprintf(payload, sizeof(payload),
        "ts:%lu,mode:%d,"
        "pz0:%d,pz1:%d,pz2:%d,pz3:%d,"
        "k0:%d,k1:%d,k2:%d,k3:%d,"
        "m0:%d,m1:%d,m2:%d,m3:%d,"
        "mv0:%.3f,mv1:%.3f,"
        "ht0:%d,ht1:%d,"
        "bs0:%d,bs1:%d,"
        "fp0:%.1f,fp1:%.1f,"
        "c0:%d,c1:%d",
        millis(), (int)mode,
        piezo.raw[0], piezo.raw[1], piezo.raw[2], piezo.raw[3],
        piezo.kickDetected[0] ? 1 : 0, piezo.kickDetected[1] ? 1 : 0,
        piezo.kickDetected[2] ? 1 : 0, piezo.kickDetected[3] ? 1 : 0,
        piezo.movementDetected[0] ? 1 : 0, piezo.movementDetected[1] ? 1 : 0,
        piezo.movementDetected[2] ? 1 : 0, piezo.movementDetected[3] ? 1 : 0,
        mic.volts[0], mic.volts[1],
        mic.heartToneDetected[0] ? 1 : 0, mic.heartToneDetected[1] ? 1 : 0,
        mic.bowelSoundDetected[0] ? 1 : 0, mic.bowelSoundDetected[1] ? 1 : 0,
        film.pressurePercent[0], film.pressurePercent[1],
        film.contractionDetected[0] ? 1 : 0, film.contractionDetected[1] ? 1 : 0);

    _charSensorData->setValue((uint8_t*)payload, strlen(payload));
    _charSensorData->notify();
}

void BLEManager::publishEvent(const char* eventType, const char* detail) {
    if (!_connected) return;

    char payload[200];
    snprintf(payload, sizeof(payload), "ts:%lu,type:%s,detail:%s", millis(), eventType, detail);

    _charEvents->setValue((uint8_t*)payload, strlen(payload));
    _charEvents->notify();

    Serial.printf("[BLE] Event: %s — %s\n", eventType, detail);
}
