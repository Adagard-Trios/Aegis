#pragma once

#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <ArduinoJson.h>

#include "../config.h"
#include "../sensors/piezo.h"
#include "../sensors/microphone.h"
#include "../sensors/film.h"

// ── Mode Write Callback ───────────────────────
// Called when the BLE client writes to the Mode characteristic.
class ModeWriteCallback : public BLECharacteristicCallbacks {
public:
    explicit ModeWriteCallback(MonitorMode& mode) : _mode(mode) {}
    void onWrite(BLECharacteristic* characteristic) override;

private:
    MonitorMode& _mode;
};

// ── BLEManager Class ──────────────────────────
class BLEManager : public BLEServerCallbacks {
public:
    BLEManager();

    void begin();

    // BLEServerCallbacks
    void onConnect(BLEServer* server) override;
    void onDisconnect(BLEServer* server) override;

    bool        isConnected();
    MonitorMode getRequestedMode();

    // Publish a full sensor-data JSON packet via NOTIFY
    void publishSensorData(PiezoData& piezo, MicData& mic, FilmData& film, MonitorMode mode);

    // Publish a discrete event (kick, contraction, bowel sound …)
    void publishEvent(const char* eventType, const char* detail);

private:
    BLEServer*         _server         = nullptr;
    BLECharacteristic* _charSensorData = nullptr;
    BLECharacteristic* _charEvents     = nullptr;
    BLECharacteristic* _charMode       = nullptr;

    bool        _connected;
    MonitorMode _requestedMode;
};
