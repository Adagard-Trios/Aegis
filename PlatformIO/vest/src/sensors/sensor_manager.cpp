#include "sensor_manager.h"
#include <Arduino.h>

SensorManager::SensorManager()
  : _bus1(0), _bus2(1) {}

// ─── Bus reset ────────────────────────────────────────────────
void SensorManager::_resetBus(int sda, int scl) {
  Serial.printf("  Resetting SDA:%d SCL:%d\n", sda, scl);
  pinMode(sda, INPUT_PULLUP);
  pinMode(scl, OUTPUT);
  for (int i = 0; i < 9; i++) {
    digitalWrite(scl, HIGH); delayMicroseconds(10);
    digitalWrite(scl, LOW);  delayMicroseconds(10);
  }
  pinMode(sda, OUTPUT);
  digitalWrite(sda, LOW);  delayMicroseconds(10);
  digitalWrite(scl, HIGH); delayMicroseconds(10);
  digitalWrite(sda, HIGH); delayMicroseconds(10);
  pinMode(sda, INPUT);
  pinMode(scl, INPUT);
  delay(200);
}

// ─── I2C scan with timeout ────────────────────────────────────
bool SensorManager::_scanBus(TwoWire &bus, const char* label) {
  Serial.printf("[SCAN] %s:\n", label);
  bool found = false;
  for (byte addr = 1; addr < 127; addr++) {
    unsigned long t = millis();
    bus.beginTransmission(addr);
    byte err = bus.endTransmission();
    if (millis() - t > 50) {
      Serial.printf("  Timeout at 0x%02X\n", addr);
      break;
    }
    if (err == 0) {
      Serial.printf("  Found: 0x%02X\n", addr);
      found = true;
    }
  }
  if (!found) Serial.println("  NOTHING FOUND");
  return found;
}

// ─── Sensor init with retries ─────────────────────────────────
bool SensorManager::_initSensor(MAX30105 &sensor, TwoWire &bus,
                                 int sda, int scl, int num) {
  for (int i = 1; i <= 5; i++) {
    Serial.printf("[INIT] Sensor %d attempt %d/5...\n", num, i);
    if (sensor.begin(bus, I2C_SPEED_STANDARD)) return true;
    bus.end();
    delay(100);
    _resetBus(sda, scl);
    bus.begin(sda, scl, 100000);
    delay(200);
  }
  return false;
}

// ─── I2C liveness ping ───────────────────────────────────────────
bool SensorManager::_checkAlive(TwoWire &bus, uint8_t addr) {
  bus.beginTransmission(addr);
  return (bus.endTransmission() == 0);  // 0 = device ACKed
}


// ─── Begin ────────────────────────────────────────────────────
bool SensorManager::begin() {
  Serial.println("\n[SENSOR] Resetting buses...");
  _resetBus(SDA1, SCL1);
  _resetBus(SDA2, SCL2);

  _bus1.begin(SDA1, SCL1, 100000); delay(200);
  _bus2.begin(SDA2, SCL2, 100000); delay(200);
  // Cap blocking time per transaction to 50 ms — prevents the loop from
  // stalling for seconds when a sensor is unresponsive.
  _bus1.setTimeOut(50);
  _bus2.setTimeOut(50);
  Serial.println("[SENSOR] Buses initialized.");

  Serial.println("\n[SENSOR] Scanning...");
  bool b1 = _scanBus(_bus1, "Bus 1 (GPIO 16/21)");
  bool b2 = _scanBus(_bus2, "Bus 2 (GPIO 4/5)");

  // Sensor 1
  if (b1 && _initSensor(_sensor1, _bus1, SDA1, SCL1, 1)) {
    _sensor1.setup(SENSOR_BRIGHTNESS, SENSOR_AVG_SAMPLES,
                   SENSOR_LED_MODE,   SENSOR_SAMPLE_RATE,
                   SENSOR_PULSE_WIDTH, SENSOR_ADC_RANGE);
    _sensor1.enableDIETEMPRDY();
    _s1ok = true;
    Serial.println("[SENSOR] Sensor 1 OK.");
  } else {
    Serial.println("[SENSOR] Sensor 1 UNAVAILABLE.");
  }

  // Sensor 2
  if (b2 && _initSensor(_sensor2, _bus2, SDA2, SCL2, 2)) {
    _sensor2.setup(SENSOR_BRIGHTNESS, SENSOR_AVG_SAMPLES,
                   SENSOR_LED_MODE,   SENSOR_SAMPLE_RATE,
                   SENSOR_PULSE_WIDTH, SENSOR_ADC_RANGE);
    _sensor2.enableDIETEMPRDY();
    _s2ok = true;
    Serial.println("[SENSOR] Sensor 2 OK.");
  } else {
    Serial.println("[SENSOR] Sensor 2 UNAVAILABLE.");
  }

  if (!_s1ok && !_s2ok) {
    Serial.println("[SENSOR] ERROR — no sensors found. Halting.");
    return false;
  }

  if (_s1ok && _s2ok)
    Serial.println("[SENSOR] MODE: DUAL");
  else if (_s1ok)
    Serial.println("[SENSOR] MODE: S1 only — S2 mirrors S1");
  else
    Serial.println("[SENSOR] MODE: S2 only — S1 mirrors S2");

  return true;
}

// ─── Read ─────────────────────────────────────────────────────
void SensorManager::read(SensorData &d) {
  uint32_t ir1 = 0, red1 = 0, ir2 = 0, red2 = 0;

  // ── Health-check Sensor 1 ──────────────────────────────────
  if (_s1ok) {
    if (!_checkAlive(_bus1, 0x57)) {
      if (++_s1Failures >= MAX_FAILURES) {
        _s1ok = false;
        Serial.println("[SENSOR] Sensor 1 offline — stopping reads.");
      }
    } else {
      _s1Failures = 0;   // reset on successful ping
      ir1  = _sensor1.getIR();
      red1 = _sensor1.getRed();
    }
  }

  // ── Health-check Sensor 2 ──────────────────────────────────
  if (_s2ok) {
    if (!_checkAlive(_bus2, 0x57)) {
      if (++_s2Failures >= MAX_FAILURES) {
        _s2ok = false;
        Serial.println("[SENSOR] Sensor 2 offline — stopping reads.");
      }
    } else {
      _s2Failures = 0;   // reset on successful ping
      ir2  = _sensor2.getIR();
      red2 = _sensor2.getRed();
    }
  }

  // ── If both offline, bail out early ───────────────────────
  if (!_s1ok && !_s2ok) {
    d = SensorData{0,0,0,0,0,0,0.0f,0.0f,false,false};
    return;
  }

  // ── Average / mirror logic (same as before) ────────────────
  if (_s1ok && _s2ok) {
    // Auto-calibrate
    if (!_calibrated && ir1 > CAL_IR_THRESHOLD && ir2 > CAL_IR_THRESHOLD) {
      _cal_ir1  += ir1;  _cal_ir2  += ir2;
      _cal_red1 += red1; _cal_red2 += red2;
      _cal_count++;
      if (_cal_count >= CAL_SAMPLES) {
        _scale_ir  = (_cal_ir2  > 0) ? _cal_ir1  / _cal_ir2  : 1.0;
        _scale_red = (_cal_red2 > 0) ? _cal_red1 / _cal_red2 : 1.0;
        _calibrated = true;
        Serial.printf("[CAL] Done. IR:%.3f Red:%.3f\n",
          _scale_ir, _scale_red);
      }
    }
    ir2  = (uint32_t)(ir2  * _scale_ir);
    red2 = (uint32_t)(red2 * _scale_red);
    d.ira  = (ir1 + ir2) / 2;
    d.reda = (red1 + red2) / 2;

  } else if (_s1ok) {
    ir2 = ir1; red2 = red1;
    d.ira = ir1; d.reda = red1;

  } else {   // _s2ok only
    ir1 = ir2; red1 = red2;
    d.ira = ir2; d.reda = red2;
  }

  // ── Die temperature (sampled every TEMP_READ_INTERVAL loops) ─
  _tempCounter++;
  if (_tempCounter >= TEMP_READ_INTERVAL) {
    _temp1 = _s1ok ? _sensor1.readTemperature() : 0.0;
    _temp2 = _s2ok ? _sensor2.readTemperature() : 0.0;
    if (!_s1ok) _temp1 = _temp2;
    if (!_s2ok) _temp2 = _temp1;
    _tempCounter = 0;
  }

  d.ir1        = ir1;     d.red1  = red1;
  d.ir2        = ir2;     d.red2  = red2;
  d.temp1      = _temp1;  d.temp2 = _temp2;
  d.dualMode   = (_s1ok && _s2ok);
  d.calibrated = _calibrated;
}