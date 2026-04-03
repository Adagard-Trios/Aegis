#include "film.h"

FilmSensor::FilmSensor(Adafruit_ADS1115& ads) : _ads(ads) {
    for (int i = 0; i < 2; i++) {
        _data.volts[i] = 0.0f;
        _data.baseline[i] = 0.4f;
        _data.delta[i] = 0.0f;
        _data.contractionDetected[i] = false;
        _data.pressureDetected[i] = false;
        _data.pressurePercent[i] = 0.0f;
        _bufferIndex[i] = 0;
        _bufferFull[i] = false;
        for (int j = 0; j < ROLLING_WINDOW; j++)
            _baselineBuffer[i][j] = 0.4f;
    }
}

void FilmSensor::begin() {
    Serial.println("[Film] Initialised.");
}

void FilmSensor::updateBaseline(int index, float volts) {
    _baselineBuffer[index][_bufferIndex[index]] = volts;
    _bufferIndex[index] = (_bufferIndex[index] + 1) % ROLLING_WINDOW;
    if (_bufferIndex[index] == 0) _bufferFull[index] = true;

    int count = _bufferFull[index] ? ROLLING_WINDOW : _bufferIndex[index];
    float sum = 0.0f;
    for (int j = 0; j < count; j++)
        sum += _baselineBuffer[index][j];
    _data.baseline[index] = sum / count;
}

void FilmSensor::update() {
    int adsCh[2] = {ADS_FILM1, ADS_FILM2};

    for (int i = 0; i < 2; i++) {
        int16_t raw = _ads.readADC_SingleEnded(adsCh[i]);
        float v = _ads.computeVolts(raw);
        _data.volts[i] = v;
        _data.delta[i] = v - _data.baseline[i];

        // Normalise to 0-100% where 0V=0% and 3.3V=100%
        _data.pressurePercent[i] = constrain((v / ADC_VREF) * 100.0f, 0.0f, 100.0f);

        // Event detection
        _data.contractionDetected[i] = (v >= FILM_CONTRACTION_THRESHOLD);
        _data.pressureDetected[i]    = (v >= FILM_PRESSURE_THRESHOLD);

        // Only update baseline when at rest
        if (!_data.pressureDetected[i])
            updateBaseline(i, v);
    }
}

FilmData FilmSensor::getData() {
    return _data;
}