#pragma once
#include <Arduino.h>
#include <driver/i2s.h>
#include "../config.h"

struct AudioData {
  float analogRMS;      // MAX9814 chest sounds
  float digitalRMS;     // INMP441 lung sounds
  float analogPeak;
  float digitalPeak;
  bool  soundDetected;  // true = significant audio event
  bool  valid;
};

class AudioManager {
public:
  AudioManager();
  bool begin();
  void read(AudioData &data);

private:
  static const int ANALOG_N        = 256;
  static const int I2S_N           = 256;
  static const int BASELINE_WINDOW = 16;   // ~16 s of baseline at 1 Hz audio reads

  bool _i2sOk = false;

  // Rolling baselines for the ambient floor — without these the hard-coded
  // 500 / 200 thresholds either fire constantly or never (depending on the
  // mic's DC bias). Update only during quiet periods so a sustained loud
  // event doesn't bake itself into the baseline.
  float _digitalBuf[BASELINE_WINDOW] = {0};
  int   _digitalIdx = 0;
  bool  _digitalFull = false;
  float _digitalBaseline = 0.0f;

  float _analogBuf[BASELINE_WINDOW] = {0};
  int   _analogIdx = 0;
  bool  _analogFull = false;
  float _analogBaseline = 0.0f;

  void _updateBaseline(float* buf, int& idx, bool& full, float& baseline, float val);
};