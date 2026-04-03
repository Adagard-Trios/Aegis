#pragma once

#include <Arduino.h>
#include "../config.h"
#include "../sensors/piezo.h"
#include "../sensors/microphone.h"
#include "../sensors/film.h"
#include "../ble/ble_manager.h"

// Debounce / hold-off intervals (milliseconds)
#define KICK_DEBOUNCE_MS        1000   // Minimum gap between kick events per sensor
#define CONTRACTION_DEBOUNCE_MS 5000   // Minimum gap between contraction events
#define HEART_DEBOUNCE_MS       500    // Minimum gap between heart-tone events

// ── FetalMode Class ───────────────────────────
// Monitors fetal kicks, uterine contractions, and fetal heart tones.
class FetalMode {
public:
    explicit FetalMode(BLEManager& ble);

    // Call every loop iteration; raises BLE events on detection.
    void process(PiezoData& piezo, MicData& mic, FilmData& film);

private:
    BLEManager& _ble;

    int           _kickCount;
    int           _contractionCount;
    unsigned long _lastKickTime[4];
    unsigned long _lastContractionTime[2];
    unsigned long _lastHeartToneTime[2];
};
