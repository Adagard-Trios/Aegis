/// Static identifiers for the two BLE peripherals the Aegis app talks to.
///
/// These mirror exactly what the firmware advertises:
///   - Vest:           PlatformIO/vest/src/config.h
///   - Abdomen monitor: PlatformIO/fetal_monitor/src/config.h
///
/// And exactly what the Python backend scans for in app.py:
///   VEST_DEVICE_NAME  = "Aegis_SpO2_Live"
///   FETAL_DEVICE_NAME = "AbdomenMonitor"
///
/// Keep this file as the single source of truth on the mobile side so the
/// vest_service / abdomen_service / connection_supervisor never hard-code
/// strings. If the firmware ever changes a UUID, only this file moves.
library;

/// ── Vest (Aegis_SpO2_Live, ESP32-S3) ──────────────────────────────────
class VestBle {
  static const String deviceName = 'Aegis_SpO2_Live';

  /// Custom GATT service exposed by the vest firmware.
  static const String serviceUuid = '4fafc201-1fb5-459e-8fcc-c5c9c331914b';

  /// Vitals characteristic — comma-separated KEY:value ASCII at ~1 Hz.
  /// Carries IR1/Red1/IR2/Red2/IRA/RedA, T1/T2, TL/TR/TC, IMU, env,
  /// audio RMS, ECG HR, AL/REASON edge anomaly, FW version, etc.
  static const String vitalsCharUuid = 'beb5483e-36e1-4688-b7f5-ea07361b26a8';

  /// ECG burst characteristic — pipe-delimited samples (`EB1:v0|v1|...`)
  /// at ~30 notifies/s, ~11 samples per burst → effective ~333 Hz.
  /// Lead III computed by the firmware as L3 = L2 - L1.
  static const String ecgBurstCharUuid =
      'beb5483e-36e1-4688-b7f5-ea07361b26a9';
}

/// ── Abdomen monitor (AbdomenMonitor, ESP32) ──────────────────────────
class AbdomenBle {
  static const String deviceName = 'AbdomenMonitor';

  /// Custom GATT service exposed by the fetal monitor firmware.
  static const String serviceUuid = '12345678-1234-1234-1234-123456789abc';

  /// Sensor data characteristic — compact ASCII at ~10 Hz.
  /// Carries pz0..pz3 (piezo raw), k0..k3 (kicks), m0..m3 (movement),
  /// mv0..mv1 (mic volts), ht0..ht1 (heart-tone flags),
  /// bs0..bs1 (bowel sounds), fp0..fp1 (film pressure %),
  /// c0..c1 (contractions), mode (0=fetal, 1=abdominal), ts.
  static const String sensorCharUuid = '12345678-1234-1234-1234-123456789ab1';

  /// Typed event characteristic — `ts:<ms>,type:<eventType>,detail:<...>`.
  /// Event types: kick, movement, contraction, heart_tone, bowel_sound.
  static const String eventsCharUuid = '12345678-1234-1234-1234-123456789ab2';

  /// Mode characteristic (R/W). Write `0` for fetal mode (kicks /
  /// contractions / fetal heart tones), `1` for abdominal mode
  /// (abdominal-wall movement / bowel sounds / pressure).
  static const String modeCharUuid = '12345678-1234-1234-1234-123456789ab3';
}

/// ── Tunables shared across BLE services ──────────────────────────────
class BleTuning {
  /// Time the supervisor waits between scan cycles when it can't find a
  /// target peripheral.
  static const Duration scanTimeout = Duration(seconds: 10);

  /// MTU we request once a device connects. The vest firmware accepts
  /// 247–512; larger MTU = fewer fragmented vitals frames over the air.
  static const int desiredMtu = 512;

  /// Reconnect backoff schedule used by both BleVestService and
  /// BleAbdomenService after an unexpected disconnect or scan-not-found.
  ///
  /// IMPORTANT: Android limits BLE scan starts to **5 per 30 seconds**
  /// (see `BluetoothLeScanner` rate-limiter; status=6 means
  /// `SCAN_FAILED_SCANNING_TOO_FREQUENTLY`). With two devices each
  /// scanning concurrently we can hit that limit fast on a fresh
  /// permission grant — so the schedule is long enough to stay under
  /// 5 starts per 30 s **per service**.
  static const List<Duration> reconnectBackoff = [
    Duration(seconds: 6),
    Duration(seconds: 12),
    Duration(seconds: 20),
    Duration(seconds: 30),
  ];

  /// Marker the mobile app sends on /api/snapshot/ingest and on every
  /// `/api/agent/*` and `/api/digital-twin/*` call so the backend knows
  /// to back off its own BLE thread for the next 60 s.
  static const String mobileSourceHeader = 'X-Aegis-Source';
  static const String mobileSourceValue = 'mobile-ble';
}
