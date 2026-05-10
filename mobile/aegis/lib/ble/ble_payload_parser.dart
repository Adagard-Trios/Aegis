/// Pure functions that decode the compact-ASCII BLE payloads the vest
/// and the AbdomenMonitor emit. No Flutter / IO imports — these are
/// trivially unit-testable and deterministic.
///
/// Reference implementations (the ground truth):
///   - app.py :: handle_ble_notification     → vest vitals
///   - app.py :: handle_ecg_burst            → vest ECG burst
///   - app.py :: handle_fetal_notification   → abdomen monitor
///
/// Field-for-field parity with the Python parser is the goal — golden
/// fixtures should land identical dicts on both sides.
library;

class VestVitals {
  // PPG (raw counts from the 3 MAX30102s)
  final double ir1, red1, ir2, red2, ira, reda;
  // PPG on-sensor temperatures (°C)
  final double t1, t2;
  // DS18B20 skin temps (°C): left axilla, right axilla, cervical
  final double tl, tr, tc;
  // IMU pitch/roll: upper body, lower body
  final double upperPitch, upperRoll, lowerPitch, lowerRoll;
  // IMU accelerometer (m/s²) — always shows ~9.8 m/s² total magnitude
  // for a working MPU6050 even at rest (gravity acts on at least one
  // axis). Reading exact 0 across all three axes means the sensor is
  // genuinely silent (init failure), not just held still.
  final double upperAccelX, upperAccelY, upperAccelZ;
  final double lowerAccelX, lowerAccelY, lowerAccelZ;
  // IMU gyroscope (deg/s) — reads ~0 at rest but small values when
  // the vest is moved.
  final double upperGyroX, upperGyroY, upperGyroZ;
  final double lowerGyroX, lowerGyroY, lowerGyroZ;
  // Spinal angle (derived) + poor posture flag
  final double spinalAngle;
  final bool poorPosture;
  // BMP180 (chest cavity pressure / temp), BMP280 (env) + DHT11
  final double bmp180Pressure, bmp180Temp;
  final double bmp280Pressure, bmp280Temp;
  final double dht11Humidity, dht11Temp;
  // Single-sample ECG values (legacy fallback — real ECG arrives via burst)
  final double? ecgL1, ecgL2, ecgL3;
  // ECG-derived heart rate (firmware QRS detector)
  final double ecgHr;
  // Audio RMS — analog (MAX9814) + digital (INMP441)
  final double analogRms, digitalRms;
  // Edge anomaly flag (firmware v3.9+) and reason string
  final bool edgeAlert;
  final String edgeAlertReason;
  // Firmware version (`FW` field, e.g., "3.9")
  final String? firmwareVersion;
  // Original full key-value map (useful for debug overlay parity check)
  final Map<String, String> raw;

  const VestVitals({
    required this.ir1,
    required this.red1,
    required this.ir2,
    required this.red2,
    required this.ira,
    required this.reda,
    required this.t1,
    required this.t2,
    required this.tl,
    required this.tr,
    required this.tc,
    required this.upperPitch,
    required this.upperRoll,
    required this.lowerPitch,
    required this.lowerRoll,
    required this.upperAccelX,
    required this.upperAccelY,
    required this.upperAccelZ,
    required this.lowerAccelX,
    required this.lowerAccelY,
    required this.lowerAccelZ,
    required this.upperGyroX,
    required this.upperGyroY,
    required this.upperGyroZ,
    required this.lowerGyroX,
    required this.lowerGyroY,
    required this.lowerGyroZ,
    required this.spinalAngle,
    required this.poorPosture,
    required this.bmp180Pressure,
    required this.bmp180Temp,
    required this.bmp280Pressure,
    required this.bmp280Temp,
    required this.dht11Humidity,
    required this.dht11Temp,
    required this.ecgL1,
    required this.ecgL2,
    required this.ecgL3,
    required this.ecgHr,
    required this.analogRms,
    required this.digitalRms,
    required this.edgeAlert,
    required this.edgeAlertReason,
    required this.firmwareVersion,
    required this.raw,
  });
}

class EcgBurst {
  /// Lead I and Lead II samples in this burst — Lead III is computed at
  /// snapshot time as L3 = L2 - L1 (Einthoven).
  final List<double> lead1;
  final List<double> lead2;

  const EcgBurst({required this.lead1, required this.lead2});

  /// Computed Lead III (same length as L1 + L2). Returns an empty list
  /// when L1 / L2 lengths disagree (corrupt burst).
  List<double> get lead3 {
    if (lead1.length != lead2.length) return const [];
    return [for (var i = 0; i < lead1.length; i++) lead2[i] - lead1[i]];
  }
}

class AbdomenFrame {
  /// Mode byte: 0 = fetal (kicks/contractions/heart-tones), 1 = abdominal
  /// (movement / bowel-sounds / pressure).
  final int mode;
  // 4 piezo channel raw ADC reads (0–4095)
  final List<int> piezoRaw;
  // Per-piezo flags
  final List<bool> kicks;
  final List<bool> movement;
  // 2 mic voltages + heart-tone / bowel-sound flags
  final List<double> micVolts;
  final List<bool> heartTones;
  final List<bool> bowelSounds;
  // 2 flex film readings + per-film contraction flags
  final List<double> filmPressure;
  final List<bool> contractions;
  // Original raw map
  final Map<String, String> raw;

  const AbdomenFrame({
    required this.mode,
    required this.piezoRaw,
    required this.kicks,
    required this.movement,
    required this.micVolts,
    required this.heartTones,
    required this.bowelSounds,
    required this.filmPressure,
    required this.contractions,
    required this.raw,
  });
}

class BlePayloadParser {
  /// Internal: split `K1:v1,K2:v2,...` ASCII into a string-keyed map.
  static Map<String, String> _splitKv(String s) {
    final out = <String, String>{};
    for (final p in s.split(',')) {
      final ix = p.indexOf(':');
      if (ix > 0) out[p.substring(0, ix)] = p.substring(ix + 1);
    }
    return out;
  }

  static double _f(Map<String, String> m, String k, [double def = 0.0]) {
    final v = m[k];
    if (v == null) return def;
    return double.tryParse(v) ?? def;
  }

  static int _i(Map<String, String> m, String k, [int def = 0]) {
    final v = m[k];
    if (v == null) return def;
    return int.tryParse(v) ?? def;
  }

  /// Parses the vest vitals characteristic (~1 Hz). Mirrors
  /// `handle_ble_notification` in app.py field-for-field. Tolerates
  /// missing fields by leaving them at their default — older firmware
  /// can omit `AL`/`REASON`/`FW`/`L1..L3`.
  static VestVitals parseVestVitals(String payload) {
    final m = _splitKv(payload.trim());
    return VestVitals(
      ir1: _f(m, 'IR1'),
      red1: _f(m, 'Red1'),
      ir2: _f(m, 'IR2'),
      red2: _f(m, 'Red2'),
      ira: _f(m, 'IRA'),
      reda: _f(m, 'RedA'),
      t1: _f(m, 'T1'),
      t2: _f(m, 'T2'),
      tl: _f(m, 'TL'),
      tr: _f(m, 'TR'),
      tc: _f(m, 'TC'),
      upperPitch: _f(m, 'UP'),
      upperRoll: _f(m, 'UR'),
      lowerPitch: _f(m, 'LP'),
      lowerRoll: _f(m, 'LR'),
      // MPU6050 accel + gyro — emitted by vest firmware in g and °/s.
      // Used by SensorHealthPanel to detect sensor-alive vs init-fail
      // (gravity always shows on at least one accel axis when alive,
      // so the previous "pitch+roll==0 → silent" heuristic was wrong
      // for a vest sitting flat on a desk).
      upperAccelX: _f(m, 'UAX'),
      upperAccelY: _f(m, 'UAY'),
      upperAccelZ: _f(m, 'UAZ'),
      upperGyroX: _f(m, 'UGX'),
      upperGyroY: _f(m, 'UGY'),
      upperGyroZ: _f(m, 'UGZ'),
      lowerAccelX: _f(m, 'LAX'),
      lowerAccelY: _f(m, 'LAY'),
      lowerAccelZ: _f(m, 'LAZ'),
      lowerGyroX: _f(m, 'LGX'),
      lowerGyroY: _f(m, 'LGY'),
      lowerGyroZ: _f(m, 'LGZ'),
      spinalAngle: _f(m, 'SA'),
      poorPosture: _i(m, 'PP') != 0,
      bmp180Pressure: _f(m, 'BPR'),
      bmp180Temp: _f(m, 'BTP'),
      bmp280Pressure: _f(m, 'EP'),
      bmp280Temp: _f(m, 'ET'),
      dht11Humidity: _f(m, 'HUM'),
      dht11Temp: _f(m, 'DT'),
      ecgL1: m.containsKey('L1') ? _f(m, 'L1') : null,
      ecgL2: m.containsKey('L2') ? _f(m, 'L2') : null,
      ecgL3: m.containsKey('L3') ? _f(m, 'L3') : null,
      ecgHr: _f(m, 'EHR'),
      analogRms: _f(m, 'ARMS'),
      digitalRms: _f(m, 'DRMS'),
      edgeAlert: _i(m, 'AL') != 0,
      edgeAlertReason: m['REASON'] ?? 'none',
      firmwareVersion: m['FW'],
      raw: m,
    );
  }

  /// Parses one ECG burst notification: `EB1:v0|v1|...,EB2:v0|v1|...`.
  /// Pipe-delimited integers within each lead. Lead III is derived by
  /// the consumer (see `EcgBurst.lead3`). Tolerates burst with only
  /// L1 or only L2 by emitting empty lists for the missing lead.
  static EcgBurst parseEcgBurst(String payload) {
    final m = _splitKv(payload.trim());
    List<double> vals(String key) {
      final raw = m[key];
      if (raw == null || raw.isEmpty) return const [];
      return [
        for (final s in raw.split('|'))
          if (s.isNotEmpty) (double.tryParse(s) ?? 0.0)
      ];
    }
    return EcgBurst(lead1: vals('EB1'), lead2: vals('EB2'));
  }

  /// Parses the AbdomenMonitor sensor characteristic (~10 Hz). Mirrors
  /// `handle_fetal_notification` in app.py.
  static AbdomenFrame parseAbdomen(String payload) {
    final m = _splitKv(payload.trim());
    return AbdomenFrame(
      mode: _i(m, 'mode'),
      piezoRaw: [for (var i = 0; i < 4; i++) _i(m, 'pz$i')],
      kicks: [for (var i = 0; i < 4; i++) _i(m, 'k$i') != 0],
      movement: [for (var i = 0; i < 4; i++) _i(m, 'm$i') != 0],
      micVolts: [for (var i = 0; i < 2; i++) _f(m, 'mv$i')],
      heartTones: [for (var i = 0; i < 2; i++) _i(m, 'ht$i') != 0],
      bowelSounds: [for (var i = 0; i < 2; i++) _i(m, 'bs$i') != 0],
      filmPressure: [for (var i = 0; i < 2; i++) _f(m, 'fp$i')],
      contractions: [for (var i = 0; i < 2; i++) _i(m, 'c$i') != 0],
      raw: m,
    );
  }
}
