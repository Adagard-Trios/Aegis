#include "piezo.h"

PiezoSensor::PiezoSensor() {
    for (int i = 0; i < 4; i++) {
        _data.raw[i] = 0;
        _data.volts[i] = 0.0f;
        _data.baseline[i] = 2047;
        _data.kickDetected[i] = false;
        _data.movementDetected[i] = false;
        _bufferIndex[i] = 0;
        _bufferFull[i] = false;
        for (int j = 0; j < ROLLING_WINDOW; j++)
            _baselineBuffer[i][j] = 2047;
    }
}

void PiezoSensor::begin() {
    for (int i = 0; i < 4; i++)
        pinMode(_selPins[i], OUTPUT);
    pinMode(MUX_SIG, INPUT);
    analogReadResolution(ADC_RESOLUTION);
    // 11 dB attenuation gives the ADC a ~0–3.1 V input range, matching the
    // 3.3 V piezo output. Required so analogReadMilliVolts() returns
    // calibrated voltages rather than raw codes through the nonlinear S-curve.
    analogSetPinAttenuation(MUX_SIG, ADC_11db);
    Serial.println("[Piezo] Initialised (ADC 11 dB attenuation, mV-calibrated reads).");
}

void PiezoSensor::selectChannel(int ch) {
    for (int i = 0; i < 4; i++)
        digitalWrite(_selPins[i], (ch >> i) & 1);
    delayMicroseconds(10);
}

void PiezoSensor::updateBaseline(int index, int raw) {
    _baselineBuffer[index][_bufferIndex[index]] = raw;
    _bufferIndex[index] = (_bufferIndex[index] + 1) % ROLLING_WINDOW;
    if (_bufferIndex[index] == 0) _bufferFull[index] = true;

    int count = _bufferFull[index] ? ROLLING_WINDOW : _bufferIndex[index];
    long sum = 0;
    for (int j = 0; j < count; j++)
        sum += _baselineBuffer[index][j];
    _data.baseline[index] = (int)(sum / count);
}

void PiezoSensor::update() {
    unsigned long nowMs = millis();
    for (int i = 0; i < 4; i++) {
        selectChannel(_muxChannels[i]);
        int raw = analogRead(MUX_SIG);
        _data.raw[i] = raw;
        // analogReadMilliVolts() applies the per-chip ADC calibration burned
        // into eFuse, so this returns a real mV reading despite the ESP32-Classic
        // ADC's nonlinear S-curve. Convert to volts for the published payload.
        _data.volts[i] = analogReadMilliVolts(MUX_SIG) / 1000.0f;

        int delta = abs(raw - _data.baseline[i]);
        _data.kickDetected[i]     = (delta >= PIEZO_KICK_THRESHOLD);
        _data.movementDetected[i] = (delta >= PIEZO_MOVEMENT_THRESHOLD);

        // Baseline drift policy:
        //   • At rest → normal rolling update
        //   • Sustained movement → forced one-step nudge after BASELINE_FORCE_MS
        //     so a long contraction or held kick can't freeze the threshold forever
        if (delta < PIEZO_MOVEMENT_THRESHOLD) {
            updateBaseline(i, raw);
            _lastRestMs[i] = nowMs;
        } else if (nowMs - _lastRestMs[i] > BASELINE_FORCE_MS) {
            // Slow exponential drift toward the current reading (5%) — gives
            // the threshold a way to track real DC shifts without losing
            // sensitivity to the ongoing event.
            int drifted = (int)(_data.baseline[i] * 0.95f + raw * 0.05f);
            _data.baseline[i] = drifted;
            _lastRestMs[i] = nowMs;
        }
    }
}

PiezoData PiezoSensor::getData() {
    return _data;
}