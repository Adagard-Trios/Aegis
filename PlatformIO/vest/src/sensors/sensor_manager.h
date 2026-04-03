#pragma once

#include <Wire.h>
#include "MAX30105.h"
#include "../config.h"

// Holds all data from both sensors
struct SensorData {
  uint32_t ir1,  red1;   // Sensor 1 raw
  uint32_t ir2,  red2;   // Sensor 2 raw (normalized)
  uint32_t ira,  reda;   // Averaged
  float    temp1, temp2;
  bool     dualMode;     // true = both sensors active
  bool     calibrated;
};

class SensorManager {
public:
  SensorManager();

  // Call once in setup()
  bool begin();

  // Call every loop() — fills data struct
  void read(SensorData &data);

  bool isSensor1Available() const { return _s1ok; }
  bool isSensor2Available() const { return _s2ok; }

  // Allow other managers to share Bus 1 (e.g. HW-611 BMP280 at 0x76)
  TwoWire& getBus1() { return _bus1; }

private:
  TwoWire   _bus1;
  TwoWire   _bus2;
  MAX30105  _sensor1;
  MAX30105  _sensor2;

  bool _s1ok = false;
  bool _s2ok = false;

  // Runtime health tracking — sensors marked dead after too many consecutive I2C failures
  int  _s1Failures = 0;
  int  _s2Failures = 0;
  static constexpr int MAX_FAILURES = 8;

  float _scale_ir  = 1.0;
  float _scale_red = 1.0;
  bool  _calibrated = false;

  float _cal_ir1  = 0, _cal_ir2  = 0;
  float _cal_red1 = 0, _cal_red2 = 0;
  int   _cal_count = 0;

  int   _tempCounter = 0;
  float _temp1 = 0.0, _temp2 = 0.0;

  void  _resetBus(int sda, int scl);
  bool  _scanBus(TwoWire &bus, const char* label);
  bool  _initSensor(MAX30105 &sensor, TwoWire &bus,
                    int sda, int scl, int num);
  // Quick I2C ping — returns true if device ACKs at 'addr' on 'bus'
  bool  _checkAlive(TwoWire &bus, uint8_t addr);
};