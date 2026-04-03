#pragma once
#include <Arduino.h>
#include <Wire.h>
#include "../config.h"

// ── BMP280 registers ─────────────────────────────────────────
#define BMP280_CHIP_ID_REG   0xD0
#define BMP280_RESET_REG     0xE0
#define BMP280_CTRL_MEAS     0xF4
#define BMP280_CONFIG_REG    0xF5
#define BMP280_PRESS_MSB     0xF7   // 3 bytes: press[19:12], [11:4], [3:0]<<4
#define BMP280_TEMP_MSB      0xFA   // 3 bytes: temp [19:12], [11:4], [3:0]<<4
#define BMP280_CALIB_START   0x88   // 26 bytes of calibration data

struct EnvironmentData {
  float    bmp280TempC;       // HW-611 BMP280 temperature
  float    bmp280PressHpa;    // HW-611 BMP280 pressure
  float    dht11TempC;        // DHT11 temperature
  float    dht11Humidity;     // DHT11 relative humidity %
  bool     bmp280Valid;
  bool     dht11Valid;
};

class EnvManager {
public:
  EnvManager() = default;
  bool begin(TwoWire &sharedBus);
  void read(EnvironmentData &data);

private:
  TwoWire *_bus = nullptr;
  bool _bmpOk  = false;
  bool _dhtOk  = false;
  uint8_t _bmpAddr = 0x76;

  // ── BMP280 calibration coefficients ────────────────────────
  uint16_t _dig_T1;
  int16_t  _dig_T2, _dig_T3;
  uint16_t _dig_P1;
  int16_t  _dig_P2, _dig_P3, _dig_P4, _dig_P5;
  int16_t  _dig_P6, _dig_P7, _dig_P8, _dig_P9;
  int32_t  _t_fine;             // shared between temp and pressure compensation

  // ── BMP280 I2C helpers ─────────────────────────────────────
  bool _bmpWriteReg(uint8_t reg, uint8_t val);
  bool _bmpReadRegs(uint8_t reg, uint8_t *buf, uint8_t len);
  bool _initBMP280();
  void _readBMP280(float &tempC, float &pressHpa, bool &valid);

  // ── DHT11 bare-metal GPIO ──────────────────────────────────
  bool _readDHT11(float &tempC, float &humidity);
};
