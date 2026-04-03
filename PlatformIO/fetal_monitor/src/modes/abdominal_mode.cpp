#include "abdominal_mode.h"

AbdominalMode::AbdominalMode(BLEManager& ble) : _ble(ble) {
    for (int i = 0; i < 4; i++) _lastMovementTime[i] = 0;
    for (int i = 0; i < 2; i++) {
        _lastBowelTime[i] = 0;
        _lastPressureTime[i] = 0;
    }
}

void AbdominalMode::process(PiezoData& piezo, MicData& mic, FilmData& film) {
    unsigned long now = millis();

    // ── Abdominal Wall Movement ───────────────────────────
    for (int i = 0; i < 4; i++) {
        if (piezo.movementDetected[i] && (now - _lastMovementTime[i] > MOVEMENT_DEBOUNCE_MS)) {
            _lastMovementTime[i] = now;
            char detail[64];
            snprintf(detail, sizeof(detail), "Sensor %d | Raw: %d | Delta: %d",
                     i + 1, piezo.raw[i], abs(piezo.raw[i] - piezo.baseline[i]));
            _ble.publishEvent("ABD_MOVEMENT", detail);
        }
    }

    // ── Bowel Sounds ─────────────────────────────────────
    for (int i = 0; i < 2; i++) {
        if (mic.bowelSoundDetected[i] && (now - _lastBowelTime[i] > BOWEL_DEBOUNCE_MS)) {
            _lastBowelTime[i] = now;
            char detail[64];
            snprintf(detail, sizeof(detail), "Mic %d | Energy delta: %.3fV", i + 1, mic.delta[i]);
            _ble.publishEvent("BOWEL_SOUND", detail);
        }
    }

    // ── Abdominal Pressure ────────────────────────────────
    for (int i = 0; i < 2; i++) {
        if (film.pressureDetected[i] && (now - _lastPressureTime[i] > PRESSURE_DEBOUNCE_MS)) {
            _lastPressureTime[i] = now;
            char detail[64];
            snprintf(detail, sizeof(detail), "Film %d | Pressure: %.1f%%",
                     i + 1, film.pressurePercent[i]);
            _ble.publishEvent("ABD_PRESSURE", detail);
        }
    }
}