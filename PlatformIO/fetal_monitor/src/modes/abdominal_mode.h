#pragma once

#include <Arduino.h>
#include "../config.h"
#include "../sensors/piezo.h"
#include "../sensors/microphone.h"
#include "../sensors/film.h"
#include "../ble/ble_manager.h"

// Debounce / hold-off intervals (milliseconds)
#define MOVEMENT_DEBOUNCE_MS    800    // Minimum gap between abdominal movement events
#define BOWEL_DEBOUNCE_MS       2000   // Minimum gap between bowel-sound events
#define PRESSURE_DEBOUNCE_MS    1500   // Minimum gap between pressure events

// ── AbdominalMode Class ───────────────────────
// Monitors abdominal wall movement, bowel sounds, and abdominal pressure.
class AbdominalMode {
public:
    explicit AbdominalMode(BLEManager& ble);

    // Call every loop iteration; raises BLE events on detection.
    void process(PiezoData& piezo, MicData& mic, FilmData& film);

private:
    BLEManager& _ble;

    unsigned long _lastMovementTime[4];
    unsigned long _lastBowelTime[2];
    unsigned long _lastPressureTime[2];
};
