#include "ecg_manager.h"

ECGManager::ECGManager() {}

void ECGManager::begin() {
  pinMode(ECG1_PIN, INPUT);
  pinMode(ECG2_PIN, INPUT);

  for (int i = 0; i < BUF; i++) {
    _buf1[i] = 2048.0f;
    _buf2[i] = 2048.0f;
  }

  _startTime = millis();
  Serial.println("[ECG] Initialized on GPIO 35/36.");
  Serial.println("[ECG] 90s warmup started — dry electrodes need sweat.");
}

void ECGManager::sample() {
  _buf1[_idx] = (float)analogRead(ECG1_PIN);
  _buf2[_idx] = (float)analogRead(ECG2_PIN);
  _idx = (_idx + 1) % BUF;
  if (_count < BUF) _count++;
}

void ECGManager::process(ECGData &data) {
  data.warmingUp = (millis() - _startTime) < ECG_WARMUP_MS;

  int latest = (_idx - 1 + BUF) % BUF;
  float raw1  = _buf1[latest];
  float raw2  = _buf2[latest];

  // Convert 12-bit ADC → millivolts
  data.lead1_mv = (raw1 / 4095.0f) * 3300.0f;
  data.lead2_mv = (raw2 / 4095.0f) * 3300.0f;

  // Einthoven's equation: III = II - I
  data.lead3_mv = data.lead2_mv - data.lead1_mv;

  // Simple R-peak detection on Lead II
  // Threshold = 60% of supply = ~1980mV
  float threshold = 1980.0f;
  bool  above     = (data.lead2_mv > threshold);

  if (above && !_wasAbove) {
    unsigned long now = millis();
    if (_lastBeat > 0) {
      float interval = (now - _lastBeat) / 1000.0f;
      if (interval > 0.3f && interval < 2.0f) {
        _heartRate = 60.0f / interval;
      }
    }
    _lastBeat      = now;
    data.qrsDetected = true;
  } else {
    data.qrsDetected = false;
  }
  _wasAbove = above;

  data.heartRate = _heartRate;
  data.valid     = !data.warmingUp && (_count > 100);
}