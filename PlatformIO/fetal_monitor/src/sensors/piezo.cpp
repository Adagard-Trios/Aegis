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
    Serial.println("[Piezo] Initialised.");
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
    for (int i = 0; i < 4; i++) {
        selectChannel(_muxChannels[i]);
        int raw = analogRead(MUX_SIG);
        _data.raw[i] = raw;
        _data.volts[i] = raw * (ADC_VREF / 4095.0f);

        int delta = abs(raw - _data.baseline[i]);
        _data.kickDetected[i]     = (delta >= PIEZO_KICK_THRESHOLD);
        _data.movementDetected[i] = (delta >= PIEZO_MOVEMENT_THRESHOLD);

        // Only update baseline when sensor is at rest
        if (delta < PIEZO_MOVEMENT_THRESHOLD)
            updateBaseline(i, raw);
    }
}

PiezoData PiezoSensor::getData() {
    return _data;
}