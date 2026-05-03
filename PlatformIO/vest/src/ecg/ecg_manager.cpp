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
  float raw1 = (float)analogRead(ECG1_PIN);
  float raw2 = (float)analogRead(ECG2_PIN);
  _buf1[_idx] = raw1;
  _buf2[_idx] = raw2;
  _idx = (_idx + 1) % BUF;
  if (_count < BUF) _count++;
  if (_pendingCount < BUF) _pendingCount++;

  // ── Adaptive R-peak detection on the dominant lead ─────────
  // Slow IIR baseline tracks DC drift; fast-attack/slow-decay envelope
  // tracks recent peak deviation above baseline. We do this for BOTH
  // leads and detect on whichever currently has the bigger envelope —
  // electrode placement determines which lead carries the cleanest QRS,
  // and locking to a single lead missed beats when the wearer's geometry
  // pushed the strong signal onto the other one.
  float lead1_mv = (raw1 / 4095.0f) * 3300.0f;
  float lead2_mv = (raw2 / 4095.0f) * 3300.0f;

  _baseline1 = _baseline1 * 0.999f + lead1_mv * 0.001f;
  _baseline2 = _baseline2 * 0.999f + lead2_mv * 0.001f;
  float dev1 = lead1_mv - _baseline1;
  float dev2 = lead2_mv - _baseline2;

  if (dev1 > _envelope1) _envelope1 = _envelope1 * 0.85f  + dev1 * 0.15f;   // attack
  else                   _envelope1 = _envelope1 * 0.998f + dev1 * 0.002f;  // decay
  if (dev2 > _envelope2) _envelope2 = _envelope2 * 0.85f  + dev2 * 0.15f;
  else                   _envelope2 = _envelope2 * 0.998f + dev2 * 0.002f;

  // Pick the dominant lead. If both envelopes are near the floor, pick L2
  // (matches the original behaviour so flat-line signals don't trigger noise).
  bool useL1 = (_envelope1 > _envelope2);
  float baseline = useL1 ? _baseline1 : _baseline2;
  float envelope = useL1 ? _envelope1 : _envelope2;
  float signal   = useL1 ? lead1_mv   : lead2_mv;

  float minEnv = R_PEAK_MIN_ENVELOPE_MV;
  float threshold = baseline + 0.5f * (envelope > minEnv ? envelope : minEnv);
  bool above = (signal > threshold);

  if (above && !_wasAbove) {
    unsigned long now = millis();
    if (_lastBeat > 0) {
      float interval = (now - _lastBeat) / 1000.0f;
      if (interval > 0.3f && interval < 2.0f) {
        _heartRate = 60.0f / interval;
      }
    }
    _lastBeat = now;
  }
  _wasAbove = above;
}

int ECGManager::drainSamples(float* lead1_mv, float* lead2_mv, int max) {
  if (_pendingCount <= 0 || max <= 0) return 0;
  int count = (_pendingCount < max) ? _pendingCount : max;
  // The oldest pending sample sits `_pendingCount` slots behind the next-write index
  int startBack = _pendingCount;
  for (int i = 0; i < count; i++) {
    int srcIdx = (_idx - startBack + i + BUF) % BUF;
    lead1_mv[i] = (_buf1[srcIdx] / 4095.0f) * 3300.0f;
    lead2_mv[i] = (_buf2[srcIdx] / 4095.0f) * 3300.0f;
  }
  _pendingCount -= count;
  return count;
}

void ECGManager::process(ECGData &data) {
  // R-peak detection now lives in sample() at 333 Hz so we don't miss QRS
  // complexes between process() ticks. process() just exposes the latest
  // mV scalars + status flags for the BLE vitals payload.
  data.warmingUp = (millis() - _startTime) < ECG_WARMUP_MS;

  int latest = (_idx - 1 + BUF) % BUF;
  data.lead1_mv = (_buf1[latest] / 4095.0f) * 3300.0f;
  data.lead2_mv = (_buf2[latest] / 4095.0f) * 3300.0f;
  data.lead3_mv = data.lead2_mv - data.lead1_mv;  // Einthoven III = II - I

  data.heartRate   = _heartRate;
  data.qrsDetected = false;  // per-tick QRS flag retired with the move to sample()
  data.valid       = !data.warmingUp && (_count > 100);
}