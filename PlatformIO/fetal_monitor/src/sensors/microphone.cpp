#include "microphone.h"

MicrophoneSensor::MicrophoneSensor(Adafruit_ADS1115& ads) : _ads(ads) {
    for (int i = 0; i < 2; i++) {
        _data.volts[i] = 0.0f;
        _data.baseline[i] = 1.2f;
        _data.delta[i] = 0.0f;
        _data.soundDetected[i] = false;
        _data.heartToneDetected[i] = false;
        _data.bowelSoundDetected[i] = false;
        _bufferIndex[i] = 0;
        _bufferFull[i] = false;
        _energyAccum[i] = 0.0f;
        for (int j = 0; j < ROLLING_WINDOW; j++)
            _baselineBuffer[i][j] = 1.2f;
    }
    _energySamples = 0;
}

void MicrophoneSensor::begin() {
    Serial.println("[Mic] Initialised.");
}

void MicrophoneSensor::updateBaseline(int index, float volts) {
    _baselineBuffer[index][_bufferIndex[index]] = volts;
    _bufferIndex[index] = (_bufferIndex[index] + 1) % ROLLING_WINDOW;
    if (_bufferIndex[index] == 0) _bufferFull[index] = true;

    int count = _bufferFull[index] ? ROLLING_WINDOW : _bufferIndex[index];
    float sum = 0.0f;
    for (int j = 0; j < count; j++)
        sum += _baselineBuffer[index][j];
    _data.baseline[index] = sum / count;
}

void MicrophoneSensor::update() {
    for (int i = 0; i < 2; i++) {
        int16_t raw = _ads.readADC_SingleEnded(i == 0 ? ADS_MIC1 : ADS_MIC2);
        float v = _ads.computeVolts(raw);
        _data.volts[i] = v;
        _data.delta[i] = fabsf(v - _data.baseline[i]);

        // Generic sound detection
        _data.soundDetected[i] = (_data.delta[i] >= MIC_AUDIO_THRESHOLD);

        // Accumulate energy for band estimation
        _energyAccum[i] += _data.delta[i] * _data.delta[i];
    }

    _energySamples++;

    // Every ENERGY_WINDOW samples, classify the sound type
    if (_energySamples >= ENERGY_WINDOW) {
        for (int i = 0; i < 2; i++) {
            float avgEnergy = _energyAccum[i] / ENERGY_WINDOW;

            // Low energy sustained = heart tone (fetal)
            // Higher energy bursts = bowel sounds
            // These thresholds are calibrated for MAX9814 at 50dB gain
            _data.heartToneDetected[i]  = (avgEnergy > 0.001f && avgEnergy < 0.05f);
            _data.bowelSoundDetected[i] = (avgEnergy >= 0.05f && avgEnergy < 0.5f);

            _energyAccum[i] = 0.0f;
        }
        _energySamples = 0;
    }

    // Update baseline only during quiet periods
    for (int i = 0; i < 2; i++) {
        if (!_data.soundDetected[i])
            updateBaseline(i, _data.volts[i]);
    }
}

MicData MicrophoneSensor::getData() {
    return _data;
}