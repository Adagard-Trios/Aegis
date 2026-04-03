#pragma once

#include <Arduino.h>
#include <Adafruit_ADS1X15.h>
#include "../config.h"

// ── Film Sensor Data Structure ─────────────────
struct FilmData {
    float volts[2];
    float baseline[2];
    float delta[2];
    bool  contractionDetected[2];
    bool  pressureDetected[2];
    float pressurePercent[2];
};

// ── FilmSensor Class ───────────────────────────
class FilmSensor {
public:
    explicit FilmSensor(Adafruit_ADS1115& ads);

    void begin();
    void update();
    FilmData getData();

private:
    Adafruit_ADS1115& _ads;
    FilmData          _data;

    // Rolling baseline buffers
    float _baselineBuffer[2][ROLLING_WINDOW];
    int   _bufferIndex[2];
    bool  _bufferFull[2];

    void updateBaseline(int index, float volts);
};
