#include "ble_manager.h"

void ModeWriteCallback::onWrite(BLECharacteristic* characteristic) {
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
    BLEDevice::init(BLE_DEVICE_NAME);
    _server = BLEDevice::createServer();
    _server->setCallbacks(this);

    BLEService* service = _server->createService(BLE_SERVICE_UUID);

    // Sensor data characteristic — notify
    _charSensorData = service->createCharacteristic(
        BLE_CHAR_SENSOR_DATA,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
    );
    _charSensorData->addDescriptor(new BLE2902());

    // Events characteristic — notify
    _charEvents = service->createCharacteristic(
        BLE_CHAR_EVENTS,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
    );
    _charEvents->addDescriptor(new BLE2902());

    // Mode characteristic — read/write
    _charMode = service->createCharacteristic(
        BLE_CHAR_MODE,
        BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE
    );
    _charMode->setCallbacks(new ModeWriteCallback(_requestedMode));
    _charMode->setValue("0"); // Default: fetal mode

    service->start();

    BLEAdvertising* advertising = BLEDevice::getAdvertising();
    advertising->addServiceUUID(BLE_SERVICE_UUID);
    advertising->setScanResponse(true);
    advertising->setMinPreferred(0x06);
    BLEDevice::startAdvertising();

    Serial.println("[BLE] Advertising started. Device: " BLE_DEVICE_NAME);
}

void BLEManager::onConnect(BLEServer* server) {
    _connected = true;
    Serial.println("[BLE] Client connected.");
}

void BLEManager::onDisconnect(BLEServer* server) {
    _connected = false;
    Serial.println("[BLE] Client disconnected. Restarting advertising...");
    BLEDevice::startAdvertising();
}

bool BLEManager::isConnected() {
    return _connected;
}

MonitorMode BLEManager::getRequestedMode() {
    return _requestedMode;
}

void BLEManager::publishSensorData(PiezoData& piezo, MicData& mic, FilmData& film, MonitorMode mode) {
    if (!_connected) return;

    JsonDocument doc;
    doc["ts"]   = millis();
    doc["mode"] = (int)mode;

    // Piezo
    JsonArray pz = doc["pz"].to<JsonArray>();
    for (int i = 0; i < 4; i++) pz.add(piezo.raw[i]);

    JsonArray pzKick = doc["kick"].to<JsonArray>();
    for (int i = 0; i < 4; i++) pzKick.add(piezo.kickDetected[i] ? 1 : 0);

    JsonArray pzMove = doc["move"].to<JsonArray>();
    for (int i = 0; i < 4; i++) pzMove.add(piezo.movementDetected[i] ? 1 : 0);

    // Microphone
    JsonArray mv = doc["mv"].to<JsonArray>();
    for (int i = 0; i < 2; i++) mv.add(serialized(String(mic.volts[i], 3)));

    doc["heart"]  = JsonArray();
    doc["bowel"]  = JsonArray();
    JsonArray heart = doc["heart"].to<JsonArray>();
    JsonArray bowel = doc["bowel"].to<JsonArray>();
    for (int i = 0; i < 2; i++) {
        heart.add(mic.heartToneDetected[i] ? 1 : 0);
        bowel.add(mic.bowelSoundDetected[i] ? 1 : 0);
    }

    // Film
    JsonArray fp = doc["fp"].to<JsonArray>();
    for (int i = 0; i < 2; i++) fp.add(serialized(String(film.pressurePercent[i], 1)));

    JsonArray cont = doc["cont"].to<JsonArray>();
    for (int i = 0; i < 2; i++) cont.add(film.contractionDetected[i] ? 1 : 0);

    char buf[512];
    serializeJson(doc, buf);
    _charSensorData->setValue(buf);
    _charSensorData->notify();
}

void BLEManager::publishEvent(const char* eventType, const char* detail) {
    if (!_connected) return;

    JsonDocument doc;
    doc["ts"]     = millis();
    doc["type"]   = eventType;
    doc["detail"] = detail;

    char buf[200];
    serializeJson(doc, buf);
    _charEvents->setValue(buf);
    _charEvents->notify();

    Serial.printf("[BLE] Event: %s — %s\n", eventType, detail);
}