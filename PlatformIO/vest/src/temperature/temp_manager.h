#pragma once
#include <OneWire.h>
#include <DallasTemperature.h>
#include "../config.h"

struct TempData {
  float leftAxilla;    // Left armpit
  float rightAxilla;   // Right armpit
  float cervical;      // C7 trunk
  bool  valid;
};

class TempManager {
public:
  TempManager();
  bool begin();
  void read(TempData &data);
  void printAddresses();  // Call once to identify which sensor is which

private:
  OneWire        _ow;
  DallasTemperature _dt;
  DeviceAddress  _addr[3];
  int            _sensorCount = 0;
};