#pragma once
#include <Arduino.h>
#include "../config.h"

struct ECGData {
  float lead1_mv;       // Lead I  in millivolts
  float lead2_mv;       // Lead II in millivolts
  float lead3_mv;       // Lead III = II - I (Einthoven)
  float heartRate;      // BPM from R-peak detection
  bool  warmingUp;      // true during 90s dry electrode warmup
  bool  qrsDetected;    // true = beat detected this cycle
  bool  valid;
};

class ECGManager {
public:
  ECGManager();
  void begin();
  void sample();                  // Call at ~333Hz in loop
  void process(ECGData &data);    // Call every ECG_PROCESS_INTERVAL

  // Copy up to `max` fresh samples (mV-converted) out of the ring buffer
  // into `lead1_mv` / `lead2_mv`. Returns the number actually written.
  // Any pending samples beyond `max` are kept for the next drain call —
  // we never silently drop ECG data unless the ring buffer overflows.
  int  drainSamples(float* lead1_mv, float* lead2_mv, int max);

  static const int BUF = 1024;   // ~3 seconds at 333Hz

private:
  float  _buf1[BUF];
  float  _buf2[BUF];
  int    _idx          = 0;
  int    _count        = 0;
  int    _pendingCount = 0;      // samples written since last drainSamples()

  // Adaptive R-peak detection state — replaces the broken hard-coded
  // 1980 mV threshold which assumed signals would rail to >60% of supply.
  // We track a slow-moving baseline (low-pass IIR) and a fast-attack /
  // slow-decay envelope of the deviation; threshold = baseline + 50%
  // envelope. Held to a 100 mV minimum so noise alone can't trigger.
  float  _baseline2  = 1650.0f;  // mV — starts at mid-rail
  float  _envelope2  = 100.0f;   // mV — peak deviation tracker
  static constexpr float R_PEAK_MIN_ENVELOPE_MV = 100.0f;

  unsigned long _startTime   = 0;
  unsigned long _lastBeat    = 0;
  float         _lastRaw2    = 0;
  float         _heartRate   = 0;
  bool          _wasAbove    = false;
};