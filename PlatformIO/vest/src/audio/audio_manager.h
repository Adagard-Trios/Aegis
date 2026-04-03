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
  static const int ANALOG_N = 256;
  static const int I2S_N    = 256;
  bool _i2sOk = false;
};