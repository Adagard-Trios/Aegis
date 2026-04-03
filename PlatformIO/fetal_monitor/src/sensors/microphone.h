#pragma once

#include <Arduino.h>
#include <Adafruit_ADS1X15.h>
#include "../config.h"

// Energy window: how many update() calls before classifying sound type
#define ENERGY_WINDOW   40

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

    // Energy accumulator for sound classification
    float _energyAccum[2];
    int   _energySamples;

    void updateBaseline(int index, float volts);
};
