#pragma once
#include <NimBLEDevice.h>
#include "../config.h"
#include "../sensors/sensor_manager.h"
#include "../imu/imu_manager.h"
#include "../temperature/temp_manager.h"
#include "../ecg/ecg_manager.h"
#include "../audio/audio_manager.h"
#include "../environment/env_manager.h"

class BLEManager {
public:
  BLEManager();
  void begin();
  void transmit(const SensorData       &ppg,
                const PostureData      &posture,
                const TempData         &temp,
                const ECGData          &ecg,
                const AudioData        &audio,
                const EnvironmentData  &env,
                bool        anomaly_fired = false,
                const char* anomaly_reason = "none");
  // High-rate ECG burst — drains the manager's ring buffer and emits one
  // notification on the dedicated ECG characteristic. Call at ECG_BURST_INTERVAL.
  void transmitECGBurst(ECGManager &ecg);
  bool isConnected() const { return _connected; }

private:
  NimBLECharacteristic* _pChar    = nullptr;
  NimBLECharacteristic* _pEcgChar = nullptr;
  bool _connected = false;
  friend class AegisBLECallbacks;
};