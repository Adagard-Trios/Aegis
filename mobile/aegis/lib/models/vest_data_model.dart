import 'package:flutter/foundation.dart';

class VestDataModel extends ChangeNotifier {
  // High-frequency Waveform Queues (ValueNotifiers prevent massive UI rebuilds)
  // ecgData = Lead II (kept for backwards compat); the per-lead notifiers
  // power the multi-lead cardiology graph (Einthoven L1 / L2 / L3).
  final ValueNotifier<List<double>> ecgData = ValueNotifier([]);
  final ValueNotifier<List<double>> ecgLead1Data = ValueNotifier([]);
  final ValueNotifier<List<double>> ecgLead2Data = ValueNotifier([]);
  final ValueNotifier<List<double>> ecgLead3Data = ValueNotifier([]);
  final ValueNotifier<List<double>> ppgData = ValueNotifier([]);
  final ValueNotifier<List<double>> rspData = ValueNotifier([]);
  final ValueNotifier<List<double>> fhrData = ValueNotifier([]);

  // Essential Biometrics
  int heartRate = 0;
  int spO2 = 0;
  double temperature = 0.0;
  int respiratoryRate = 0;

  // Cardiology specifics
  double hrvRmssd = 0.0;
  double systolicBp = 0.0;
  double diastolicBp = 0.0;
  double perfusionIndex = 0.0;

  // Neurology specifics
  String posture = 'Unknown';
  String motionState = 'Unknown';
  double fallRiskScore = 0.0;

  // Dermatology specifics
  double skinTempLeft = 0.0;
  double skinTempRight = 0.0;
  double ambientTemp = 0.0;

  // Environment
  double humidity = 0.0;
  double pressure = 0.0;

  // Obstetrics / Fetal
  bool hasKicks = false;
  bool hasContractions = false;

  // System status
  bool isConnected = false;
  String connectionStatus = 'Disconnected';
  
  // Pharmacology
  String? activeMedication;
  double medSimTime = 0.0;
  String clearanceModel = "Normal";

  void updateConnectionStatus(bool connected, String status) {
    if (isConnected != connected || connectionStatus != status) {
      isConnected = connected;
      connectionStatus = status;
      notifyListeners();
    }
  }

  // ── Type-safe extractors ─────────────────────────────────────
  // Defensive helpers — return null when the value is the wrong shape
  // (e.g. a Map where a num is expected) instead of throwing. Everything
  // in updateFromStream goes through these so a single malformed field
  // can't crash the whole stream.

  static int? _asInt(dynamic v) {
    if (v is num) return v.toInt();
    if (v is bool) return v ? 1 : 0;
    if (v is String) return int.tryParse(v);
    return null;
  }

  static double? _asDouble(dynamic v) {
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }

  static Map? _asMap(dynamic v) => v is Map ? v : null;

  static List? _asList(dynamic v) => v is List ? v : null;

  /// Append a fresh batch of samples to a rolling 500-element waveform
  /// notifier. Drops the oldest samples when the buffer overflows so
  /// the widget always renders the most-recent ~500 ticks.
  void _appendWaveform(ValueNotifier<List<double>> sink, List src) {
    final samples = src.map((e) => _asDouble(e) ?? 0.0).toList();
    if (samples.isEmpty) return;
    final updated = List<double>.from(sink.value)..addAll(samples);
    if (updated.length > 500) {
      updated.removeRange(0, updated.length - 500);
    }
    sink.value = updated;
  }

  void updateFromStream(Map<String, dynamic> data) {
    try {
      _updateFromStream(data);
    } catch (e, st) {
      // Belt-and-suspenders: even if a future schema change introduces a
      // shape we didn't anticipate, the BLE stream keeps flowing instead
      // of throwing every tick.
      debugPrint('VestDataModel.updateFromStream skipped tick: $e\n$st');
    }
  }

  void _updateFromStream(Map<String, dynamic> data) {
    bool shouldNotify = false;

    // Fast-path for waveforms: append arrays directly to the ValueNotifiers.
    // Lead II legacy alias (drives the single-trace ECG widget).
    final ecgRaw = _asList(data['ecg_raw']);
    if (ecgRaw != null) {
      _appendWaveform(ecgData, ecgRaw);
    }
    // Per-lead streams (drive the multi-lead overlay).
    final lead1 = _asList(data['ecg_lead1_raw']);
    if (lead1 != null) _appendWaveform(ecgLead1Data, lead1);
    final lead2 = _asList(data['ecg_lead2_raw']);
    if (lead2 != null) _appendWaveform(ecgLead2Data, lead2);
    final lead3 = _asList(data['ecg_lead3_raw']);
    if (lead3 != null) _appendWaveform(ecgLead3Data, lead3);
    // Fetal heart-tone CTG-style trace from the AbdomenMonitor mics.
    final fhr = _asList(data['fhr_raw']);
    if (fhr != null) _appendWaveform(fhrData, fhr);

    final ppgRaw = _asList(data['ppg_raw']);
    if (ppgRaw != null) {
      final List<double> newPpg = ppgRaw.map((e) => _asDouble(e) ?? 0.0).toList();
      final updatedPpg = List<double>.from(ppgData.value)..addAll(newPpg);
      if (updatedPpg.length > 500) updatedPpg.removeRange(0, updatedPpg.length - 500);
      ppgData.value = updatedPpg;
    }

    final rspRaw = _asList(data['resp_raw']);
    if (rspRaw != null) {
      final List<double> newRsp = rspRaw.map((e) => _asDouble(e) ?? 0.0).toList();
      final updatedRsp = List<double>.from(rspData.value)..addAll(newRsp);
      if (updatedRsp.length > 500) updatedRsp.removeRange(0, updatedRsp.length - 500);
      rspData.value = updatedRsp;
    }

    // Vitals block (canonical structured shape).
    final vitals = _asMap(data['vitals']);
    if (vitals != null) {
      heartRate = _asInt(vitals['heart_rate']) ?? heartRate;
      spO2 = _asInt(vitals['spo2']) ?? spO2;
      respiratoryRate = _asInt(vitals['breathing_rate']) ?? respiratoryRate;
      hrvRmssd = _asDouble(vitals['hrv_rmssd']) ?? hrvRmssd;
      perfusionIndex = _asDouble(vitals['perfusion_index']) ?? perfusionIndex;
      shouldNotify = true;
    }

    // Top-level scalar fallbacks (legacy mock shapes). Type-checked so
    // a structured Map never trips an `as num` cast.
    final hrTop = _asInt(data['heart_rate']);
    if (hrTop != null && hrTop != heartRate) {
      heartRate = hrTop;
      shouldNotify = true;
    }
    final tempTop = _asDouble(data['temperature']);
    if (tempTop != null && tempTop != temperature) {
      temperature = tempTop;
      shouldNotify = true;
    }

    // Temperature block — three skin-temp fields.
    final tempMap = _asMap(data['temperature']);
    if (tempMap != null) {
      skinTempLeft = _asDouble(tempMap['left_axilla']) ?? skinTempLeft;
      skinTempRight = _asDouble(tempMap['right_axilla']) ?? skinTempRight;
      temperature = _asDouble(tempMap['cervical']) ?? temperature;
      shouldNotify = true;
    }

    // IMU block — posture label + spinal angle.
    final imu = _asMap(data['imu']);
    if (imu != null) {
      posture = imu['posture_label']?.toString() ?? posture;
      fallRiskScore = _asDouble(imu['spinal_angle']) ?? fallRiskScore;
      shouldNotify = true;
    }

    // Environment block.
    final env = _asMap(data['environment']);
    if (env != null) {
      ambientTemp = _asDouble(env['bmp280_temp']) ?? ambientTemp;
      humidity = _asDouble(env['dht11_humidity']) ?? humidity;
      pressure = _asDouble(env['bmp280_pressure']) ?? pressure;
      shouldNotify = true;
    }

    // Fetal block — kicks + contractions arrays.
    final fetal = _asMap(data['fetal']);
    if (fetal != null) {
      final kicks = _asList(fetal['kicks']);
      if (kicks != null) {
        hasKicks = kicks.any((e) => e == true || e == 1);
        shouldNotify = true;
      }
      final contractions = _asList(fetal['contractions']);
      if (contractions != null) {
        hasContractions = contractions.any((e) => e == true || e == 1);
        shouldNotify = true;
      }
    }

    // Pharmacology block.
    final pharm = _asMap(data['pharmacology']);
    if (pharm != null) {
      activeMedication = pharm['active_medication']?.toString();
      medSimTime = _asDouble(pharm['sim_time']) ?? medSimTime;
      clearanceModel = pharm['clearance_model']?.toString() ?? clearanceModel;
      shouldNotify = true;
    }

    // Only call notifyListeners() if low-frequency data actually changed.
    // High-frequency waveform updates auto-trigger their own ValueNotifiers.
    if (shouldNotify) {
      notifyListeners();
    }
  }
}
