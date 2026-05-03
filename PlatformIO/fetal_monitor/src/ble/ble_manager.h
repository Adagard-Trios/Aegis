#pragma once

#include <Arduino.h>
#include <NimBLEDevice.h>

#include "../config.h"
#include "../sensors/piezo.h"
#include "../sensors/microphone.h"
#include "../sensors/film.h"

// ── Mode Write Callback ───────────────────────
// Called when the BLE client writes to the Mode characteristic.
class ModeWriteCallback : public NimBLECharacteristicCallbacks {
public:
    explicit ModeWriteCallback(MonitorMode& mode) : _mode(mode) {}
    void onWrite(NimBLECharacteristic* characteristic) override;

private:
    MonitorMode& _mode;
};

// ── BLEManager Class ──────────────────────────
// Migrated from Bluedroid to NimBLE for ~70 KB of freed RAM, faster notify
// throughput, and parity with the vest firmware. NimBLE auto-creates the
// CCCD descriptor (BLE2902 equivalent) so we no longer have to attach it
// manually to each notify characteristic.
class BLEManager : public NimBLEServerCallbacks {
public:
    BLEManager();

    void begin();

    // NimBLEServerCallbacks
    void onConnect(NimBLEServer* server) override;
    void onDisconnect(NimBLEServer* server) override;

    bool        isConnected();
    MonitorMode getRequestedMode();

    // Publish a full sensor snapshot via NOTIFY. Compact ASCII format
    // (key:value,key:value,...) — see ble_manager.cpp for the field list.
    // Replaces the previous JSON serialisation, which heap-allocated a
    // JsonDocument per call (slow + fragments memory over hours).
    void publishSensorData(PiezoData& piezo, MicData& mic, FilmData& film, MonitorMode mode);

    // Publish a discrete event (kick, contraction, bowel sound …)
    void publishEvent(const char* eventType, const char* detail);

private:
    NimBLEServer*         _server         = nullptr;
    NimBLECharacteristic* _charSensorData = nullptr;
    NimBLECharacteristic* _charEvents     = nullptr;
    NimBLECharacteristic* _charMode       = nullptr;

    bool        _connected;
    MonitorMode _requestedMode;
};
