#include "imu_manager.h"
#include <math.h>

// ══════════════════════════════════════════════════════════════
// Software I2C — bit-bang on IMU_SDA / IMU_SCL
//
// Uses open-drain emulation: to drive HIGH we set the pin as
// INPUT_PULLUP (external 4.7 kΩ or GY-87 on-board pull-ups
// pull the line to 3.3 V).  To drive LOW we set OUTPUT + LOW.
// ══════════════════════════════════════════════════════════════

void IMUManager::_sclHigh() { pinMode(IMU_SCL, INPUT_PULLUP); }
void IMUManager::_sclLow()  { pinMode(IMU_SCL, OUTPUT); digitalWrite(IMU_SCL, LOW); }
void IMUManager::_sdaHigh() { pinMode(IMU_SDA, INPUT_PULLUP); }
void IMUManager::_sdaLow()  { pinMode(IMU_SDA, OUTPUT); digitalWrite(IMU_SDA, LOW); }
int  IMUManager::_sdaRead() { return digitalRead(IMU_SDA); }
void IMUManager::_i2cDelay(){ delayMicroseconds(5); }   // ~100 kHz

void IMUManager::_i2cStart() {
  _sdaHigh(); _i2cDelay();
  _sclHigh(); _i2cDelay();
  _sdaLow();  _i2cDelay();
  _sclLow();  _i2cDelay();
}

void IMUManager::_i2cStop() {
  _sdaLow();  _i2cDelay();
  _sclHigh(); _i2cDelay();
  _sdaHigh(); _i2cDelay();
}

bool IMUManager::_i2cWriteByte(uint8_t b) {
  for (int i = 7; i >= 0; i--) {
    if (b & (1 << i)) _sdaHigh(); else _sdaLow();
    _i2cDelay();
    _sclHigh(); _i2cDelay();
    _sclLow();  _i2cDelay();
  }
  // Read ACK bit (LOW = ACK)
  _sdaHigh(); _i2cDelay();
  _sclHigh(); _i2cDelay();
  bool ack = !_sdaRead();
  _sclLow();  _i2cDelay();
  return ack;
}

uint8_t IMUManager::_i2cReadByte(bool ack) {
  uint8_t b = 0;
  _sdaHigh();
  for (int i = 7; i >= 0; i--) {
    _sclHigh(); _i2cDelay();
    if (_sdaRead()) b |= (1 << i);
    _sclLow();  _i2cDelay();
  }
  // Send ACK/NACK
  if (ack) _sdaLow(); else _sdaHigh();
  _i2cDelay();
  _sclHigh(); _i2cDelay();
  _sclLow();  _i2cDelay();
  _sdaHigh();
  return b;
}

// ── Register-level helpers ────────────────────────────────────

bool IMUManager::_writeReg(uint8_t devAddr, uint8_t reg, uint8_t val) {
  _i2cStart();
  if (!_i2cWriteByte(devAddr << 1))       { _i2cStop(); return false; }
  if (!_i2cWriteByte(reg))                { _i2cStop(); return false; }
  if (!_i2cWriteByte(val))                { _i2cStop(); return false; }
  _i2cStop();
  return true;
}

bool IMUManager::_readRegs(uint8_t devAddr, uint8_t reg, uint8_t *buf, int len) {
  _i2cStart();
  if (!_i2cWriteByte(devAddr << 1))       { _i2cStop(); return false; }
  if (!_i2cWriteByte(reg))                { _i2cStop(); return false; }
  _i2cStart();  // repeated start
  if (!_i2cWriteByte((devAddr << 1) | 1)) { _i2cStop(); return false; }
  for (int i = 0; i < len; i++)
    buf[i] = _i2cReadByte(i < len - 1);   // ACK all except last byte
  _i2cStop();
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
  Serial.println("\n[IMU] Initializing GY-87 on software I2C...");
  Serial.printf("[IMU] SDA=GPIO %d, SCL=GPIO %d\n", IMU_SDA, IMU_SCL);

  // Release both lines HIGH before first transaction
  _sdaHigh();
  _sclHigh();
  delay(10);

  // ── Quick bus scan ─────────────────────────────────────────
  Serial.println("[IMU] Scanning software I2C bus...");
  bool anyFound = false;
  for (uint8_t addr = 1; addr < 127; addr++) {
    _i2cStart();
    bool ack = _i2cWriteByte(addr << 1);
    _i2cStop();
    if (ack) {
      Serial.printf("[IMU]   Found device at 0x%02X\n", addr);
      anyFound = true;
    }
    delayMicroseconds(50);
  }
  if (!anyFound) {
    Serial.println("[IMU]   NOTHING FOUND — check wiring & pull-ups.");
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