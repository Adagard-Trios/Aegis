#pragma once

#include <Arduino.h>
#include "../config.h"

// ── Piezo Sensor Data Structure ───────────────
struct PiezoData {
    int   raw[4];
    float volts[4];
    int   baseline[4];
    bool  kickDetected[4];
    bool  movementDetected[4];
};

// ── PiezoSensor Class ─────────────────────────
class PiezoSensor {
public:
    PiezoSensor();

    void begin();
    void update();
    PiezoData getData();

private:
    PiezoData _data;

    // MUX channel assignments (from config.h)
    const int _muxChannels[4] = { MUX_PIEZO1, MUX_PIEZO2, MUX_PIEZO3, MUX_PIEZO4 };

    // MUX select pins (S0–S3)
    const int _selPins[4] = { MUX_S0, MUX_S1, MUX_S2, MUX_S3 };

    // Rolling baseline buffers
    int  _baselineBuffer[4][ROLLING_WINDOW];
    int  _bufferIndex[4];
    bool _bufferFull[4];

    // Per-channel "last time the sensor was at rest" tracker. If a channel
    // sits above the movement threshold for longer than BASELINE_FORCE_MS,
    // the baseline is force-drifted toward the current reading so a sustained
    // contraction (30-60 s) can't freeze the detection threshold.
    unsigned long _lastRestMs[4] = {0};
    static constexpr unsigned long BASELINE_FORCE_MS = 30000;

    void selectChannel(int ch);
    void updateBaseline(int index, int raw);
};
