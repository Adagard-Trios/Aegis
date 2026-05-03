#pragma once

#include <Arduino.h>
#include <Adafruit_ADS1X15.h>
#include "../config.h"

// Energy window: how many update() calls before classifying sound type
#define ENERGY_WINDOW   40

// Peak-tracker history depth — sized to span the slowest fetal HR (110 bpm =
// 545 ms) at the loop rate (~250 ms publish, multiple update() calls between).
// 8 entries gives ~2 s of recent peak timestamps to compute the rate from.
#define PEAK_HISTORY    8

// ── Microphone Sensor Data Structure ──────────
struct MicData {
    float volts[2];
    float baseline[2];
    float delta[2];
    bool  soundDetected[2];
    bool  heartToneDetected[2];
    bool  bowelSoundDetected[2];
};

// ── MicrophoneSensor Class ────────────────────
//
// Sound-type classification rewrite (replaces the previous magic-number
// energy thresholds 0.001 / 0.05 / 0.5 which assumed a fixed MAX9814 gain
// that the chip's AGC actively defeats):
//
//   1. Self-calibrating baseline + adaptive deviation threshold (already
//      mostly in place; tightened so the classifier can't bake a sustained
//      sound into the baseline).
//   2. **Heart tone** = rhythmic peaks within the fetal HR window
//      (110-180 bpm → 333-545 ms inter-peak intervals). Tracked via a
//      rolling buffer of recent peak timestamps; classifier looks for at
//      least 4 inter-peak intervals where the median lands in the band.
//   3. **Bowel sound** = sustained energy elevation that is NOT rhythmic
//      (energy band exceeded but no consistent peak rate found).
//
// Still a heuristic — true clinical fetal-HR extraction needs proper
// band-pass filtering + autocorrelation in the 1.83-3 Hz envelope band.
// But this one actually adapts to the mic's installed gain.
class MicrophoneSensor {
public:
    explicit MicrophoneSensor(Adafruit_ADS1115& ads);

    void begin();
    void update();
    MicData getData();

private:
    Adafruit_ADS1115& _ads;
    MicData           _data;

    // Rolling baseline buffers
    float _baselineBuffer[2][ROLLING_WINDOW];
    int   _bufferIndex[2];
    bool  _bufferFull[2];

    // Energy accumulator for the per-window classifier
    float _energyAccum[2];
    int   _energySamples;

    // Rhythm-rate state — peak timestamps + edge-tracker per channel
    unsigned long _peakHistory[2][PEAK_HISTORY] = {{0}};
    int           _peakIdx[2]    = {0, 0};
    int           _peakCount[2]  = {0, 0};
    bool          _wasAbove[2]   = {false, false};
    unsigned long _lastBaselineForce[2] = {0, 0};

    void updateBaseline(int index, float volts);
    bool _checkRhythm(int index) const;   // true if peak intervals look like fetal HR
};
