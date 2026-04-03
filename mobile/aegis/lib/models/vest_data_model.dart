import 'package:flutter/foundation.dart';

class VestDataModel extends ChangeNotifier {
  // High-frequency Waveform Queues (ValueNotifiers prevent massive UI rebuilds)
  final ValueNotifier<List<double>> ecgData = ValueNotifier([]);
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

  void updateConnectionStatus(bool connected, String status) {
    if (isConnected != connected || connectionStatus != status) {
      isConnected = connected;
      connectionStatus = status;
      notifyListeners();
    }
  }

  void updateFromStream(Map<String, dynamic> data) {
    bool shouldNotify = false;

    // Fast-path for waveforms: append arrays directly to the ValueNotifiers
    if (data.containsKey('ecg_raw')) {
      final List<double> newEcg = (data['ecg_raw'] as List).map((e) => (e as num).toDouble()).toList();
      final updatedEcg = List<double>.from(ecgData.value)..addAll(newEcg);
      if (updatedEcg.length > 500) updatedEcg.removeRange(0, updatedEcg.length - 500);
      ecgData.value = updatedEcg;
    }

    if (data.containsKey('ppg_raw')) {
      final List<double> newPpg = (data['ppg_raw'] as List).map((e) => (e as num).toDouble()).toList();
      final updatedPpg = List<double>.from(ppgData.value)..addAll(newPpg);
      if (updatedPpg.length > 500) updatedPpg.removeRange(0, updatedPpg.length - 500);
      ppgData.value = updatedPpg;
    }

    if (data.containsKey('resp_raw')) {
      final List<double> newRsp = (data['resp_raw'] as List).map((e) => (e as num).toDouble()).toList();
      final updatedRsp = List<double>.from(rspData.value)..addAll(newRsp);
      if (updatedRsp.length > 500) updatedRsp.removeRange(0, updatedRsp.length - 500);
      rspData.value = updatedRsp;
    }

    // Biometrics parsing updates the standard state
    if (data.containsKey('heart_rate') && data['heart_rate'] != heartRate) {
      heartRate = (data['heart_rate'] as num).toInt();
      shouldNotify = true;
    }
    if (data.containsKey('spo2') && data['spo2'] != spO2) {
      spO2 = (data['spo2'] as num).toInt();
      shouldNotify = true;
    }
    if (data.containsKey('temperature') && data['temperature'] != temperature) {
      temperature = (data['temperature'] as num).toDouble();
      shouldNotify = true;
    }
    if (data.containsKey('respiratory_rate') && data['respiratory_rate'] != respiratoryRate) {
      respiratoryRate = (data['respiratory_rate'] as num).toInt();
      shouldNotify = true;
    }

    // Expert specific updates
    if (data.containsKey('blood_pressure') && data['blood_pressure'] is Map) {
      systolicBp = (data['blood_pressure']['systolic'] as num?)?.toDouble() ?? systolicBp;
      diastolicBp = (data['blood_pressure']['diastolic'] as num?)?.toDouble() ?? diastolicBp;
      shouldNotify = true;
    }
    if (data.containsKey('posture') && data['posture'] != posture) {
      posture = data['posture'].toString();
      shouldNotify = true;
    }

    if (data.containsKey('environment') && data['environment'] is Map) {
      final env = data['environment'];
      ambientTemp = (env['bmp280_temp'] as num?)?.toDouble() ?? ambientTemp;
      humidity = (env['dht11_humidity'] as num?)?.toDouble() ?? humidity;
      pressure = (env['bmp280_pressure'] as num?)?.toDouble() ?? pressure;
      shouldNotify = true;
    }

    if (data.containsKey('fetal') && data['fetal'] is Map) {
      final fetal = data['fetal'];
      if (fetal.containsKey('kicks')) {
         hasKicks = (fetal['kicks'] as List).any((e) => e == true);
         shouldNotify = true;
      }
      if (fetal.containsKey('contractions')) {
         hasContractions = (fetal['contractions'] as List).any((e) => e == true);
         shouldNotify = true;
      }
    }
    
    // Only call notifyListeners() if low-frequency data actually changed
    // High-frequency waveform updates auto-trigger their own ValueNotifiers independently
    if (shouldNotify) {
      notifyListeners();
    }
  }
}
