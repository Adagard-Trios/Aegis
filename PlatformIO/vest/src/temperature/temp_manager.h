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
  // Last-good cache. DallasTemperature returns -127 when a sensor
  // momentarily fails to respond; we hold the previous value rather than
  // letting that sentinel reach the BLE payload (where it'd render as a
  // huge red spike on the dashboard).
  float          _lastGood[3] = {0.0f, 0.0f, 0.0f};
};