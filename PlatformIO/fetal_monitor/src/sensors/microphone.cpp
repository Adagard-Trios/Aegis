#include "microphone.h"

// Inter-peak interval window for fetal HR — 110 to 180 bpm
static constexpr unsigned long FETAL_IPI_MIN_MS = 333;   // 180 bpm
static constexpr unsigned long FETAL_IPI_MAX_MS = 545;   // 110 bpm

// Adaptive peak-detection threshold (multiplier on baseline)
static constexpr float PEAK_THRESHOLD_MULT = 1.6f;

// Force-drift the baseline if a "loud" condition holds longer than this
// (otherwise a continuous sound bakes itself into the baseline → classifier
// stops reacting to anything until the sound stops).
static constexpr unsigned long BASELINE_FORCE_MS = 8000;

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
    Serial.println("[Mic] Initialised (adaptive heart-tone classifier).");
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

// True if the recent peak timestamps form ≥3 inter-peak intervals whose
// median lands in the fetal HR window (333-545 ms). Demanding 3 valid
// gaps avoids false positives from one-off taps or thumps.
bool MicrophoneSensor::_checkRhythm(int index) const {
    int n = _peakCount[index];
    if (n < 4) return false;

    unsigned long ipis[PEAK_HISTORY];
    int valid = 0;
    int count = (n < PEAK_HISTORY) ? n : PEAK_HISTORY;
    // Walk the ring buffer in chronological order
    int start = (_peakIdx[index] - count + PEAK_HISTORY) % PEAK_HISTORY;
    for (int i = 1; i < count; i++) {
        int curr = (start + i)     % PEAK_HISTORY;
        int prev = (start + i - 1) % PEAK_HISTORY;
        unsigned long ipi = _peakHistory[index][curr] - _peakHistory[index][prev];
        if (ipi >= FETAL_IPI_MIN_MS && ipi <= FETAL_IPI_MAX_MS) {
            ipis[valid++] = ipi;
        }
    }
    return valid >= 3;
}

void MicrophoneSensor::update() {
    unsigned long nowMs = millis();
    for (int i = 0; i < 2; i++) {
        int16_t raw = _ads.readADC_SingleEnded(i == 0 ? ADS_MIC1 : ADS_MIC2);
        float v = _ads.computeVolts(raw);
        _data.volts[i] = v;
        _data.delta[i] = fabsf(v - _data.baseline[i]);

        // Adaptive deviation gate (kept from the previous design)
        _data.soundDetected[i] = (_data.delta[i] >= MIC_AUDIO_THRESHOLD);

        // ── Peak detection on the raw deviation envelope ──
        // Threshold = baseline * 1.6, so the classifier auto-scales with
        // whatever gain the MAX9814 AGC has settled on.
        float peakThresh = _data.baseline[i] * PEAK_THRESHOLD_MULT;
        bool above = (v > peakThresh);
        if (above && !_wasAbove[i]) {
            // Rising edge — log the peak timestamp
            _peakHistory[i][_peakIdx[i]] = nowMs;
            _peakIdx[i]   = (_peakIdx[i] + 1) % PEAK_HISTORY;
            if (_peakCount[i] < PEAK_HISTORY) _peakCount[i]++;
        }
        _wasAbove[i] = above;

        // Energy accumulator (still used for the bowel/sustained-sound branch)
        _energyAccum[i] += _data.delta[i] * _data.delta[i];
    }

    _energySamples++;

    if (_energySamples >= ENERGY_WINDOW) {
        for (int i = 0; i < 2; i++) {
            // Adaptive energy floor — relative to current baseline so the
            // bowel-sound check works regardless of MAX9814 AGC state.
            float avgEnergy = _energyAccum[i] / ENERGY_WINDOW;
            float baselineEnergy = _data.baseline[i] * _data.baseline[i] * 0.05f;

            bool rhythm    = _checkRhythm(i);
            bool elevated  = (avgEnergy > baselineEnergy * 2.0f);

            // Fetal heart tone: rhythmic peaks at fetal HR rate
            _data.heartToneDetected[i] = rhythm;
            // Bowel sound: sustained elevated energy WITHOUT a heart-rate rhythm
            _data.bowelSoundDetected[i] = elevated && !rhythm;

            _energyAccum[i] = 0.0f;
        }
        _energySamples = 0;
    }

    // Baseline maintenance: update only during quiet periods, but force-drift
    // after BASELINE_FORCE_MS of sustained loud signal so we don't get stuck
    // with a baseline that's permanently below the actual ambient floor.
    for (int i = 0; i < 2; i++) {
        if (!_data.soundDetected[i]) {
            updateBaseline(i, _data.volts[i]);
            _lastBaselineForce[i] = nowMs;
        } else if (nowMs - _lastBaselineForce[i] > BASELINE_FORCE_MS) {
            // Slow drift toward the current reading (5%) — gives the baseline
            // a way to track real ambient shifts without losing sensitivity
            // to the ongoing event.
            _data.baseline[i] = _data.baseline[i] * 0.95f + _data.volts[i] * 0.05f;
            _lastBaselineForce[i] = nowMs;
        }
    }
}

MicData MicrophoneSensor::getData() {
    return _data;
}
