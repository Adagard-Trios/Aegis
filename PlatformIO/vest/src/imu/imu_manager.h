#pragma once
#include <Arduino.h>
#include "../config.h"

// ── MPU6050 register map (only what we need) ─────────────────
#define MPU6050_ADDR          0x68
#define MPU6050_WHO_AM_I      0x75
#define MPU6050_PWR_MGMT_1    0x6B
#define MPU6050_SMPLRT_DIV    0x19
#define MPU6050_CONFIG        0x1A
#define MPU6050_GYRO_CONFIG   0x1B
#define MPU6050_ACCEL_CONFIG  0x1C
#define MPU6050_INT_PIN_CFG   0x37
#define MPU6050_ACCEL_XOUT_H  0x3B   // 6 bytes: AX,AY,AZ
#define MPU6050_GYRO_XOUT_H   0x43   // 6 bytes: GX,GY,GZ

// ── BMP180 register map ──────────────────────────────────────
#define BMP180_ADDR           0x77
#define BMP180_CHIP_ID_REG    0xD0
#define BMP180_CTRL_REG       0xF4
#define BMP180_OUT_MSB        0xF6
#define BMP180_READ_TEMP_CMD  0x2E
#define BMP180_CHIP_ID_VAL    0x55

struct IMUReading {
  float pitch;
  float roll;
  float accelX, accelY, accelZ;
  float gyroX,  gyroY,  gyroZ;
  bool  valid;
};

struct PostureData {
  IMUReading upper;
  IMUReading lower;           // unused (single IMU) — zeroed
  float      spinalAngle;     // forward/back lean (pitch)
  float      lateralBend;     // side bend (roll)
  bool       poorPosture;     // |pitch| > 30°
  bool       lateralAlert;    // |roll|  > 20°
  float      pressure_hPa;   // BMP180 atmospheric pressure
  float      bmpTempC;        // BMP180 temperature
};

class IMUManager {
public:
  IMUManager() = default;
  bool begin();
  void read(PostureData &data);

private:
  bool _mpuOk  = false;
  bool _bmpOk  = false;

  // Last-good pressure cache. The BMP180 in the GY-87 module periodically
  // returns nonsense (we observed 1613 hPa with otherwise-correct temp,
  // suggesting a partial calibration-register read failure through the
  // MPU6050 I2C bypass). Anything outside 800-1100 hPa is rejected.
  float _lastGoodPressure_hPa = 0.0f;

  // Software I2C on GPIO 6/7. Tried hardware I2C in v3.4 — that broke
  // because the ESP32-S3 only has TWO I2C peripherals (Wire + Wire1) and
  // both are already claimed by the MAX30102 sensors on bus 0/1.
  // `TwoWire(2)` silently mapped back to bus 0, so the IMU lost its bus
  // and read 0/0 forever. Bit-bang it is.

  // ── BMP180 calibration coefficients ────────────────────────
  int16_t  _ac1, _ac2, _ac3;
  uint16_t _ac4, _ac5, _ac6;
  int16_t  _b1, _b2, _mb, _mc, _md;

  // ── Software I2C primitives (bit-bang on IMU_SDA / IMU_SCL) ─
  void    _sclHigh();
  void    _sclLow();
  void    _sdaHigh();
  void    _sdaLow();
  int     _sdaRead();
  void    _i2cDelay();
  void    _i2cStart();
  void    _i2cStop();
  bool    _i2cWriteByte(uint8_t b);
  uint8_t _i2cReadByte(bool ack);

  // ── Register helpers ───────────────────────────────────────
  bool    _writeReg(uint8_t devAddr, uint8_t reg, uint8_t val);
  bool    _readRegs(uint8_t devAddr, uint8_t reg, uint8_t *buf, int len);
  int16_t _read16(uint8_t devAddr, uint8_t reg);

  // ── Subsystem init ─────────────────────────────────────────
  bool    _initMPU6050();
  bool    _initBMP180();

  // ── Reading helpers ────────────────────────────────────────
  void    _readMPU(IMUReading &r);
  void    _readBMP(float &tempC, float &presHpa);
};