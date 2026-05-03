#include "imu_manager.h"
#include <math.h>

// ══════════════════════════════════════════════════════════════
// Hardware I2C — TwoWire(2) on IMU_SDA / IMU_SCL (GPIO 6/7)
//
// Replaces the previous bit-banged software I2C. The ESP32-S3 has three
// I2C peripherals; Wire (bus 0) + Wire1 (bus 1) are claimed by the two
// MAX30102 sensors, so the IMU gets bus 2. Hardware I2C cuts a 14-byte
// accel+gyro burst from ~25 ms (bit-bang at 100 kHz with 5 µs slack) to
// ~0.3 ms — and frees the loop to stay close to its declared cadence.
// ══════════════════════════════════════════════════════════════

bool IMUManager::_writeReg(uint8_t devAddr, uint8_t reg, uint8_t val) {
  _wire.beginTransmission(devAddr);
  _wire.write(reg);
  _wire.write(val);
  return (_wire.endTransmission() == 0);
}

bool IMUManager::_readRegs(uint8_t devAddr, uint8_t reg, uint8_t *buf, int len) {
  _wire.beginTransmission(devAddr);
  _wire.write(reg);
  if (_wire.endTransmission(false) != 0) return false;  // repeated start
  uint8_t got = _wire.requestFrom(devAddr, (uint8_t)len);
  if (got != len) return false;
  for (int i = 0; i < len; i++) {
    if (!_wire.available()) return false;
    buf[i] = _wire.read();
  }
  return true;
}

int16_t IMUManager::_read16(uint8_t devAddr, uint8_t reg) {
  uint8_t buf[2];
  if (!_readRegs(devAddr, reg, buf, 2)) return 0;
  return (int16_t)((buf[0] << 8) | buf[1]);
}

// ══════════════════════════════════════════════════════════════
//  MPU6050 init
// ══════════════════════════════════════════════════════════════

bool IMUManager::_initMPU6050() {
  // WHO_AM_I check — should return 0x68
  uint8_t whoami = 0;
  if (!_readRegs(MPU6050_ADDR, MPU6050_WHO_AM_I, &whoami, 1)) {
    Serial.println("[IMU] MPU6050 — no response on software I2C.");
    return false;
  }
  if (whoami != 0x68 && whoami != 0x72 && whoami != 0x70) {
    // 0x68 = genuine MPU6050, 0x70/0x72 = common clones
    Serial.printf("[IMU] MPU6050 unexpected WHO_AM_I: 0x%02X\n", whoami);
    return false;
  }

  // Wake up (clear SLEEP bit)
  _writeReg(MPU6050_ADDR, MPU6050_PWR_MGMT_1, 0x00);
  delay(100);

  // Sample rate divider → 50 Hz  (gyro 1 kHz / (1+19))
  _writeReg(MPU6050_ADDR, MPU6050_SMPLRT_DIV, 19);

  // DLPF config 3 → accel 44 Hz BW, gyro 42 Hz BW (good for posture)
  _writeReg(MPU6050_ADDR, MPU6050_CONFIG, 0x03);

  // Accel ±2 g  (sensitivity 16384 LSB/g)
  _writeReg(MPU6050_ADDR, MPU6050_ACCEL_CONFIG, 0x00);

  // Gyro ±250 °/s  (sensitivity 131 LSB/°/s)
  _writeReg(MPU6050_ADDR, MPU6050_GYRO_CONFIG, 0x00);

  // Enable I2C bypass so we can talk to BMP180 & HMC5883L directly
  _writeReg(MPU6050_ADDR, MPU6050_INT_PIN_CFG, 0x02);
  delay(10);

  Serial.printf("[IMU] MPU6050 OK (WHO_AM_I 0x%02X).\n", whoami);
  return true;
}

// ══════════════════════════════════════════════════════════════
//  BMP180 init — read factory calibration data
// ══════════════════════════════════════════════════════════════

bool IMUManager::_initBMP180() {
  uint8_t chipId = 0;
  if (!_readRegs(BMP180_ADDR, BMP180_CHIP_ID_REG, &chipId, 1) ||
      chipId != BMP180_CHIP_ID_VAL) {
    Serial.printf("[IMU] BMP180 not found (got 0x%02X, expected 0x55).\n", chipId);
    return false;
  }

  // Read 11 calibration coefficients (22 bytes starting at 0xAA)
  _ac1 = _read16(BMP180_ADDR, 0xAA);
  _ac2 = _read16(BMP180_ADDR, 0xAC);
  _ac3 = _read16(BMP180_ADDR, 0xAE);
  _ac4 = (uint16_t)_read16(BMP180_ADDR, 0xB0);
  _ac5 = (uint16_t)_read16(BMP180_ADDR, 0xB2);
  _ac6 = (uint16_t)_read16(BMP180_ADDR, 0xB4);
  _b1  = _read16(BMP180_ADDR, 0xB6);
  _b2  = _read16(BMP180_ADDR, 0xB8);
  _mb  = _read16(BMP180_ADDR, 0xBA);
  _mc  = _read16(BMP180_ADDR, 0xBC);
  _md  = _read16(BMP180_ADDR, 0xBE);

  Serial.println("[IMU] BMP180 OK — calibration loaded.");
  return true;
}

// ══════════════════════════════════════════════════════════════
//  Public begin()
// ══════════════════════════════════════════════════════════════

bool IMUManager::begin() {
  Serial.println("\n[IMU] Initializing GY-87 on hardware I2C (Wire2)...");
  Serial.printf("[IMU] SDA=GPIO %d, SCL=GPIO %d\n", IMU_SDA, IMU_SCL);

  _wire.begin(IMU_SDA, IMU_SCL, 100000);  // 100 kHz — same speed as the bit-bang
  _wire.setTimeOut(50);                   // hard cap so a stuck bus can't lock the loop

  // Targeted ping at the only two devices we care about (MPU6050 0x68,
  // BMP180 0x77). Skips the wasteful 1-127 scan that previously blocked
  // boot for several seconds even though every iteration except 2 was
  // never going to find anything.
  _wire.beginTransmission(MPU6050_ADDR);
  bool mpuPresent = (_wire.endTransmission() == 0);
  if (!mpuPresent) {
    Serial.printf("[IMU]   MPU6050 not responding at 0x%02X — check wiring & pull-ups.\n", MPU6050_ADDR);
    Serial.println("[IMU] GY-87 init FAILED.\n");
    return false;
  }

  // ── Init MPU6050 ───────────────────────────────────────────
  _mpuOk = _initMPU6050();

  // ── Init BMP180 (through MPU6050's I2C bypass) ─────────────
  if (_mpuOk)
    _bmpOk = _initBMP180();

  if (_mpuOk)
    Serial.println("[IMU] GY-87 ready.\n");
  else
    Serial.println("[IMU] GY-87 init FAILED.\n");

  return _mpuOk;
}

// ══════════════════════════════════════════════════════════════
//  Read MPU6050 accel + gyro
// ══════════════════════════════════════════════════════════════

void IMUManager::_readMPU(IMUReading &r) {
  uint8_t buf[14];   // accel(6) + temp(2) + gyro(6)
  if (!_readRegs(MPU6050_ADDR, MPU6050_ACCEL_XOUT_H, buf, 14)) {
    r.valid = false;
    return;
  }

  // ±2 g → 16384 LSB/g
  r.accelX = (int16_t)((buf[0] << 8) | buf[1])  / 16384.0f;
  r.accelY = (int16_t)((buf[2] << 8) | buf[3])  / 16384.0f;
  r.accelZ = (int16_t)((buf[4] << 8) | buf[5])  / 16384.0f;

  // ±250 °/s → 131 LSB/(°/s)
  r.gyroX  = (int16_t)((buf[8]  << 8) | buf[9])  / 131.0f;
  r.gyroY  = (int16_t)((buf[10] << 8) | buf[11]) / 131.0f;
  r.gyroZ  = (int16_t)((buf[12] << 8) | buf[13]) / 131.0f;

  // Pitch & roll from accelerometer (tilt angles)
  r.pitch = atan2f(r.accelX, sqrtf(r.accelY * r.accelY + r.accelZ * r.accelZ))
            * 180.0f / M_PI;
  r.roll  = atan2f(r.accelY, sqrtf(r.accelX * r.accelX + r.accelZ * r.accelZ))
            * 180.0f / M_PI;

  r.valid = true;
}

// ══════════════════════════════════════════════════════════════
//  Read BMP180 temperature + pressure (blocking, OSS=0 mode)
// ══════════════════════════════════════════════════════════════

void IMUManager::_readBMP(float &tempC, float &presHpa) {
  if (!_bmpOk) { tempC = 0; presHpa = 0; return; }

  // ── Read raw temperature ───────────────────────────────────
  _writeReg(BMP180_ADDR, BMP180_CTRL_REG, BMP180_READ_TEMP_CMD);
  delay(5);   // 4.5 ms max conversion time
  int32_t ut = _read16(BMP180_ADDR, BMP180_OUT_MSB);

  // ── Read raw pressure (OSS = 0 → ultra-low power) ─────────
  _writeReg(BMP180_ADDR, BMP180_CTRL_REG, 0x34);   // 0x34 = read pressure OSS=0
  delay(5);
  int32_t up = _read16(BMP180_ADDR, BMP180_OUT_MSB);

  // ── Compensate temperature ─────────────────────────────────
  int32_t x1 = ((ut - (int32_t)_ac6) * (int32_t)_ac5) >> 15;
  int32_t x2 = ((int32_t)_mc << 11) / (x1 + (int32_t)_md);
  int32_t b5 = x1 + x2;
  tempC = (b5 + 8) / 160.0f;   // in 0.1 °C units → °C

  // ── Compensate pressure ────────────────────────────────────
  int32_t b6  = b5 - 4000;
  x1 = ((int32_t)_b2 * ((b6 * b6) >> 12)) >> 11;
  x2 = ((int32_t)_ac2 * b6) >> 11;
  int32_t x3 = x1 + x2;
  int32_t b3 = ((((int32_t)_ac1 * 4 + x3)) + 2) / 4;
  x1 = ((int32_t)_ac3 * b6) >> 13;
  x2 = ((int32_t)_b1 * ((b6 * b6) >> 12)) >> 16;
  x3 = ((x1 + x2) + 2) >> 2;
  uint32_t b4 = ((uint32_t)_ac4 * (uint32_t)(x3 + 32768)) >> 15;
  uint32_t b7 = ((uint32_t)up - b3) * 50000UL;
  int32_t  p  = (b7 < 0x80000000UL) ? (b7 * 2) / b4 : (b7 / b4) * 2;
  x1 = (p >> 8) * (p >> 8);
  x1 = (x1 * 3038) >> 16;
  x2 = (-7357 * p) >> 16;
  p  = p + ((x1 + x2 + 3791) >> 4);
  presHpa = p / 100.0f;
}

// ══════════════════════════════════════════════════════════════
//  Public read()
// ══════════════════════════════════════════════════════════════

void IMUManager::read(PostureData &data) {
  if (!_mpuOk) {
    data.upper        = IMUReading{0,0,0,0,0,0,0,0,false};
    data.lower        = IMUReading{0,0,0,0,0,0,0,0,false};
    data.spinalAngle  = 0;
    data.lateralBend  = 0;
    data.poorPosture  = false;
    data.lateralAlert = false;
    data.pressure_hPa = 0;
    data.bmpTempC     = 0;
    return;
  }

  _readMPU(data.upper);
  data.lower = IMUReading{0,0,0,0,0,0,0,0,false};   // single IMU — lower unused

  if (data.upper.valid) {
    data.spinalAngle  = data.upper.pitch;
    data.lateralBend  = data.upper.roll;
    data.poorPosture  = fabsf(data.spinalAngle) > 30.0f;
    data.lateralAlert = fabsf(data.lateralBend) > 20.0f;
  } else {
    data.spinalAngle  = 0;
    data.lateralBend  = 0;
    data.poorPosture  = false;
    data.lateralAlert = false;
  }

  _readBMP(data.bmpTempC, data.pressure_hPa);
}