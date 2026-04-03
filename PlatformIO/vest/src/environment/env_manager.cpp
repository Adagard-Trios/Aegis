#include "env_manager.h"

// ══════════════════════════════════════════════════════════════
//  BMP280 I2C helpers — uses hardware I2C Bus 1 (shared with MAX30102 #1)
// ══════════════════════════════════════════════════════════════

bool EnvManager::_bmpWriteReg(uint8_t reg, uint8_t val) {
  _bus->beginTransmission(_bmpAddr);
  _bus->write(reg);
  _bus->write(val);
  return (_bus->endTransmission() == 0);
}

bool EnvManager::_bmpReadRegs(uint8_t reg, uint8_t *buf, uint8_t len) {
  _bus->beginTransmission(_bmpAddr);
  _bus->write(reg);
  if (_bus->endTransmission() != 0) return false;
  _bus->requestFrom((uint8_t)_bmpAddr, len);
  for (uint8_t i = 0; i < len; i++) {
    if (!_bus->available()) return false;
    buf[i] = _bus->read();
  }
  return true;
}

// ══════════════════════════════════════════════════════════════
//  BMP280 initialization — chip ID check + calibration load
// ══════════════════════════════════════════════════════════════

bool EnvManager::_initBMP280() {
  uint8_t addresses[2] = {0x76, 0x77};
  uint8_t chipId = 0;
  bool found = false;

  for (int i = 0; i < 2; i++) {
    _bmpAddr = addresses[i];
    if (_bmpReadRegs(BMP280_CHIP_ID_REG, &chipId, 1)) {
      if (chipId == 0x58 || chipId == 0x60) {
        found = true;
        break;
      }
    }
  }

  if (!found) {
    Serial.println("[ENV] BMP280 — no response on Bus 1 (tried 0x76 and 0x77).");
    return false;
  }

  // Soft reset
  _bmpWriteReg(BMP280_RESET_REG, 0xB6);
  delay(10);

  // Read 26 bytes of calibration data (0x88–0xA1)
  uint8_t cal[26];
  if (!_bmpReadRegs(BMP280_CALIB_START, cal, 26)) {
    Serial.println("[ENV] BMP280 — failed to read calibration.");
    return false;
  }

  _dig_T1 = (uint16_t)(cal[1]  << 8 | cal[0]);
  _dig_T2 = (int16_t) (cal[3]  << 8 | cal[2]);
  _dig_T3 = (int16_t) (cal[5]  << 8 | cal[4]);
  _dig_P1 = (uint16_t)(cal[7]  << 8 | cal[6]);
  _dig_P2 = (int16_t) (cal[9]  << 8 | cal[8]);
  _dig_P3 = (int16_t) (cal[11] << 8 | cal[10]);
  _dig_P4 = (int16_t) (cal[13] << 8 | cal[12]);
  _dig_P5 = (int16_t) (cal[15] << 8 | cal[14]);
  _dig_P6 = (int16_t) (cal[17] << 8 | cal[16]);
  _dig_P7 = (int16_t) (cal[19] << 8 | cal[18]);
  _dig_P8 = (int16_t) (cal[21] << 8 | cal[20]);
  _dig_P9 = (int16_t) (cal[23] << 8 | cal[22]);

  // Configure:
  //   config (0xF5): t_sb=100 (500 ms standby), filter=010 (coeff 4), spi3w_en=0
  //                  → 0b10001000 = 0x88
  //   ctrl_meas (0xF4): osrs_t=001 (×1), osrs_p=011 (×4), mode=11 (normal)
  //                     → 0b00101111 = 0x2F
  // Config must be written first (in sleep mode), then ctrl_meas starts measurements.
  _bmpWriteReg(BMP280_CONFIG_REG, 0x88);
  _bmpWriteReg(BMP280_CTRL_MEAS, 0x2F);

  Serial.printf("[ENV] BMP280 OK on Bus 1 (chip 0x%02X, addr 0x%02X).\n", chipId, _bmpAddr);
  return true;
}

// ══════════════════════════════════════════════════════════════
//  BMP280 read — 20-bit raw temp + pressure, Bosch compensation
// ══════════════════════════════════════════════════════════════

void EnvManager::_readBMP280(float &tempC, float &pressHpa, bool &valid) {
  // Read 6 bytes: press[3] + temp[3]  (registers 0xF7–0xFC)
  uint8_t buf[6];
  if (!_bmpReadRegs(BMP280_PRESS_MSB, buf, 6)) {
    valid = false;
    return;
  }

  int32_t adc_P = ((int32_t)buf[0] << 12) | ((int32_t)buf[1] << 4) | ((int32_t)buf[2] >> 4);
  int32_t adc_T = ((int32_t)buf[3] << 12) | ((int32_t)buf[4] << 4) | ((int32_t)buf[5] >> 4);

  // ── Temperature compensation (Bosch datasheet §8.1) ────────
  int32_t var1 = ((((adc_T >> 3) - ((int32_t)_dig_T1 << 1))) *
                  ((int32_t)_dig_T2)) >> 11;
  int32_t var2 = (((((adc_T >> 4) - ((int32_t)_dig_T1)) *
                    ((adc_T >> 4) - ((int32_t)_dig_T1))) >> 12) *
                  ((int32_t)_dig_T3)) >> 14;
  _t_fine = var1 + var2;
  int32_t T = (_t_fine * 5 + 128) >> 8;    // in 0.01 °C
  tempC = T / 100.0f;

  // ── Pressure compensation (Bosch datasheet §8.1, 64-bit) ──
  int64_t v1 = (int64_t)_t_fine - 128000;
  int64_t v2 = v1 * v1 * (int64_t)_dig_P6;
  v2 = v2 + ((v1 * (int64_t)_dig_P5) << 17);
  v2 = v2 + (((int64_t)_dig_P4) << 35);
  v1 = ((v1 * v1 * (int64_t)_dig_P3) >> 8) +
       ((v1 * (int64_t)_dig_P2) << 12);
  v1 = (((((int64_t)1) << 47) + v1)) * ((int64_t)_dig_P1) >> 33;
  if (v1 == 0) { pressHpa = 0; valid = true; return; }

  int64_t p = 1048576 - adc_P;
  p = (((p << 31) - v2) * 3125) / v1;
  v1 = (((int64_t)_dig_P9) * (p >> 13) * (p >> 13)) >> 25;
  v2 = (((int64_t)_dig_P8) * p) >> 19;
  p = ((p + v1 + v2) >> 8) + (((int64_t)_dig_P7) << 4);
  pressHpa = (uint32_t)p / 25600.0f;       // Pa*256 → hPa

  valid = true;
}

// ══════════════════════════════════════════════════════════════
//  DHT11 bare-metal read — single-wire protocol on GPIO 17
//
//  Protocol:  MCU LOW 18 ms → release → DHT responds →
//             40 data bits (5 bytes: hum_int, hum_dec,
//             temp_int, temp_dec, checksum)
// ══════════════════════════════════════════════════════════════

bool EnvManager::_readDHT11(float &tempC, float &humidity) {
  // ── Start signal ───────────────────────────────────────────
  pinMode(DHT11_PIN, OUTPUT);
  digitalWrite(DHT11_PIN, LOW);
  delay(20);                        // hold LOW ≥ 18 ms
  digitalWrite(DHT11_PIN, HIGH);
  delayMicroseconds(30);
  pinMode(DHT11_PIN, INPUT_PULLUP);

  // ── Wait for DHT11 response (LOW 80 µs + HIGH 80 µs) ─────
  unsigned long timeout;

  timeout = micros() + 200;
  while (digitalRead(DHT11_PIN) == HIGH) {
    if (micros() > timeout) return false;
  }
  timeout = micros() + 100;
  while (digitalRead(DHT11_PIN) == LOW) {
    if (micros() > timeout) return false;
  }
  timeout = micros() + 100;
  while (digitalRead(DHT11_PIN) == HIGH) {
    if (micros() > timeout) return false;
  }

  // ── Read 40 bits ───────────────────────────────────────────
  uint8_t data[5] = {0};
  for (int i = 0; i < 40; i++) {
    // Each bit: LOW ~50 µs, then HIGH (26–28 µs = 0, 70 µs = 1)
    timeout = micros() + 80;
    while (digitalRead(DHT11_PIN) == LOW) {
      if (micros() > timeout) return false;
    }

    unsigned long risingEdge = micros();
    timeout = risingEdge + 100;
    while (digitalRead(DHT11_PIN) == HIGH) {
      if (micros() > timeout) return false;
    }

    // HIGH duration > 40 µs → bit is 1
    if ((micros() - risingEdge) > 40)
      data[i / 8] |= (1 << (7 - (i % 8)));
  }

  // ── Verify checksum ────────────────────────────────────────
  uint8_t checksum = data[0] + data[1] + data[2] + data[3];
  if (checksum != data[4]) {
    Serial.printf("[ENV] DHT11 checksum fail: calc=%d got=%d\n", checksum, data[4]);
    return false;
  }

  humidity = data[0] + data[1] * 0.1f;
  tempC    = data[2] + data[3] * 0.1f;
  return true;
}

// ══════════════════════════════════════════════════════════════
//  Public begin()
// ══════════════════════════════════════════════════════════════

bool EnvManager::begin(TwoWire &sharedBus) {
  _bus = &sharedBus;

  Serial.println("\n[ENV] Initializing environment sensors...");

  // ── BMP280 (HW-611) on shared I2C Bus 1 ────────────────────
  _bmpOk = _initBMP280();

  // ── DHT11 — just configure pin, first read after 1 s ───────
  pinMode(DHT11_PIN, INPUT_PULLUP);
  delay(1000);   // DHT11 needs 1 s after power-on before first read
  float tTest, hTest;
  _dhtOk = _readDHT11(tTest, hTest);
  if (_dhtOk)
    Serial.printf("[ENV] DHT11 OK on GPIO %d (%.1f°C, %.0f%% RH).\n",
                  DHT11_PIN, tTest, hTest);
  else
    Serial.printf("[ENV] DHT11 not responding on GPIO %d — check wiring & 10kΩ pull-up.\n",
                  DHT11_PIN);

  if (_bmpOk || _dhtOk)
    Serial.println("[ENV] Environment sensors ready.\n");
  else
    Serial.println("[ENV] No environment sensors available.\n");

  return (_bmpOk || _dhtOk);
}

// ══════════════════════════════════════════════════════════════
//  Public read()
// ══════════════════════════════════════════════════════════════

void EnvManager::read(EnvironmentData &data) {
  // ── BMP280 ────────────────────────────────────────────────
  if (_bmpOk) {
    _readBMP280(data.bmp280TempC, data.bmp280PressHpa, data.bmp280Valid);
  } else {
    data.bmp280TempC    = 0;
    data.bmp280PressHpa = 0;
    data.bmp280Valid    = false;
  }

  // ── DHT11 — retry once on failure ─────────────────────────
  if (_dhtOk) {
    data.dht11Valid = _readDHT11(data.dht11TempC, data.dht11Humidity);
    if (!data.dht11Valid) {
      delay(100);
      data.dht11Valid = _readDHT11(data.dht11TempC, data.dht11Humidity);
    }
  } else {
    data.dht11TempC    = 0;
    data.dht11Humidity = 0;
    data.dht11Valid    = false;
  }
}
