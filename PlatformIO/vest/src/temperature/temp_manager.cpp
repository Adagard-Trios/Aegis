#include "temp_manager.h"
#include <Arduino.h>

TempManager::TempManager()
  : _ow(ONE_WIRE_PIN), _dt(&_ow) {}

bool TempManager::begin() {
  _dt.begin();
  _sensorCount = _dt.getDeviceCount();
  Serial.printf("[TEMP] Found %d DS18B20 sensor(s).\n", _sensorCount);

  if (_sensorCount == 0) {
    Serial.println("[TEMP] ERROR — no DS18B20 found. Check wiring and 4.7k pullup.");
    return false;
  }

  for (int i = 0; i < min(_sensorCount, 3); i++) {
    _dt.getAddress(_addr[i], i);
    Serial.printf("[TEMP] Sensor %d address: ", i);
    for (int b = 0; b < 8; b++)
      Serial.printf("%02X ", _addr[i][b]);
    Serial.println();
  }

  // Set resolution — 11-bit is faster than 12-bit (375ms vs 750ms)
  _dt.setResolution(11);
  // Non-blocking mode — we request and read separately
  _dt.setWaitForConversion(false);
  _dt.requestTemperatures();

  Serial.println("[TEMP] Initialized. Run printAddresses() to identify sensors.");
  return true;
}

void TempManager::printAddresses() {
  Serial.println("\n[TEMP] Tape a label on each sensor and note its address:");
  for (int i = 0; i < _sensorCount; i++) {
    Serial.printf("  Sensor %d: ", i);
    for (int b = 0; b < 8; b++)
      Serial.printf("%02X", _addr[i][b]);
    Serial.println();
  }
  Serial.println("Update config.h with the correct address-to-location mapping.\n");
}

void TempManager::read(TempData &data) {
  if (_sensorCount == 0) {
    data = {0, 0, 0, false};
    return;
  }

  // Read current conversion results
  data.leftAxilla  = (_sensorCount > 0) ? _dt.getTempC(_addr[0]) : 0.0;
  data.rightAxilla = (_sensorCount > 1) ? _dt.getTempC(_addr[1]) : 0.0;
  data.cervical    = (_sensorCount > 2) ? _dt.getTempC(_addr[2]) : 0.0;
  data.valid       = true;

  // Request next conversion (non-blocking — ready in ~375ms)
  _dt.requestTemperatures();
}