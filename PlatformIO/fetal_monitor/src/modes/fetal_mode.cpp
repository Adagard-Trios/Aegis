#include "fetal_mode.h"

FetalMode::FetalMode(BLEManager& ble) : _ble(ble), _kickCount(0), _contractionCount(0) {
    unsigned long now = 0;
    for (int i = 0; i < 4; i++) _lastKickTime[i] = now;
    for (int i = 0; i < 2; i++) {
        _lastContractionTime[i] = now;
        _lastHeartToneTime[i] = now;
    }
}

void FetalMode::process(PiezoData& piezo, MicData& mic, FilmData& film) {
    unsigned long now = millis();

    // ── Fetal Kicks ──────────────────────────────────────
    for (int i = 0; i < 4; i++) {
        if (piezo.kickDetected[i] && (now - _lastKickTime[i] > KICK_DEBOUNCE_MS)) {
            _lastKickTime[i] = now;
            _kickCount++;
            char detail[64];
            snprintf(detail, sizeof(detail), "Sensor %d | Count: %d | Raw: %d",
                     i + 1, _kickCount, piezo.raw[i]);
            _ble.publishEvent("FETAL_KICK", detail);
        }
    }

    // ── Uterine Contractions ─────────────────────────────
    for (int i = 0; i < 2; i++) {
        if (film.contractionDetected[i] && (now - _lastContractionTime[i] > CONTRACTION_DEBOUNCE_MS)) {
            _lastContractionTime[i] = now;
            _contractionCount++;
            char detail[64];
            snprintf(detail, sizeof(detail), "Film %d | Pressure: %.1f%% | Count: %d",
                     i + 1, film.pressurePercent[i], _contractionCount);
            _ble.publishEvent("CONTRACTION", detail);
        }
    }

    // ── Fetal Heart Tones ────────────────────────────────
    for (int i = 0; i < 2; i++) {
        if (mic.heartToneDetected[i] && (now - _lastHeartToneTime[i] > HEART_DEBOUNCE_MS)) {
            _lastHeartToneTime[i] = now;
            char detail[64];
            snprintf(detail, sizeof(detail), "Mic %d | Delta: %.3fV", i + 1, mic.delta[i]);
            _ble.publishEvent("HEART_TONE", detail);
        }
    }
}