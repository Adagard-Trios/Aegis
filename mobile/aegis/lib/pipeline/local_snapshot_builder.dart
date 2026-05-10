import 'dart:async';
import 'dart:typed_data';

import '../ble/ble_abdomen_service.dart';
import '../ble/ble_payload_parser.dart';
import '../ble/ble_vest_service.dart';
import '../dsp/dsp_service.dart';
import '../dsp/ring_buffer.dart';

/// Aggregates BLE inputs at 1 Hz into the same snapshot dict shape the
/// FastAPI backend's `build_telemetry_snapshot()` emits.
///
/// Listens to:
///   - vest vitals  (~1 Hz, scalar values)
///   - vest ECG burst (~30 Hz, ~11 samples/burst → ~333 Hz effective)
///   - abdomen frames (~10 Hz)
///
/// Maintains rolling [RingBuffer]s per signal so [DspService] has the
/// 4-s / 8-s / 30-s windows it expects. Snaps + emits at 1 Hz on a
/// `Timer.periodic`.
///
/// The output dict is byte-key-compatible with what `VestStreamService`
/// used to receive over SSE — `VestDataModel.updateFromStream` and
/// the Phase 4.3 services keep working unchanged.
class LocalSnapshotBuilder {
  final BleVestService vest;
  final BleAbdomenService abdomen;
  final int sampleRate;

  static const int _emitIntervalMs = 1000;

  // Rolling buffers sized to satisfy the longest DSP window
  // (BR_WINDOW = 10 s = sampleRate * 10).
  late final RingBuffer _ir1Buf, _redABuf, _iraBuf;
  late final RingBuffer _ecgL1Buf, _ecgL2Buf;

  StreamSubscription<VestVitals>? _vitalsSub;
  StreamSubscription<EcgBurst>? _burstSub;
  StreamSubscription<AbdomenFrame>? _abdomenSub;
  Timer? _emitTimer;

  // Latest scalar values from the per-tick vest payload.
  VestVitals? _lastVitals;
  AbdomenFrame? _lastAbdomenFrame;

  // Streaming-since-last-emit buffers — feed `ecg_lead{1,2,3}_raw` and
  // `ppg_raw` / `resp_raw` / `fhr_raw` top-level lists in each emit so
  // VestDataModel's waveform ValueNotifiers (per-lead ECG, PPG,
  // respiration, fetal HR) keep ticking. Cleared every emit so we
  // never re-send the same sample twice.
  final List<double> _freshLead1 = <double>[];
  final List<double> _freshLead2 = <double>[];
  final List<double> _freshLead3 = <double>[];   // Einthoven: L3 = L2 - L1
  final List<double> _freshPpg = <double>[];     // IR-A normalised
  final List<double> _freshResp = <double>[];    // PPG IR1 trough envelope
  final List<double> _freshFhr = <double>[];     // Fetal mic heart-tone amplitude

  // Snapshot the builder has emitted most recently. Used by the
  // SnapshotUploader (POST /api/snapshot/ingest) and by the agent
  // call body attachment.
  Map<String, dynamic>? _latest;
  Map<String, dynamic>? get latest => _latest;

  // Internal counter: rises by 1 per emit (matches `time_counter` on
  // the backend so existing UI code that reads `data['timestamp']`
  // keeps working as a monotonic clock).
  int _ts = 0;

  // Output stream
  final _ctrl = StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get stream => _ctrl.stream;

  LocalSnapshotBuilder({
    required this.vest,
    required this.abdomen,
    this.sampleRate = DspService.defaultSampleRate,
  }) {
    final brWindow = DspService.brWindow(sampleRate);
    _ir1Buf = RingBuffer(brWindow);
    _redABuf = RingBuffer(brWindow);
    _iraBuf = RingBuffer(brWindow);
    _ecgL1Buf = RingBuffer(sampleRate * 5);  // 5 s ECG window
    _ecgL2Buf = RingBuffer(sampleRate * 5);
  }

  void start() {
    _vitalsSub ??= vest.vitalsStream.listen(_onVitals);
    _burstSub ??= vest.ecgBurstStream.listen(_onBurst);
    _abdomenSub ??= abdomen.frameStream.listen(_onAbdomen);
    _emitTimer ??= Timer.periodic(
      const Duration(milliseconds: _emitIntervalMs),
      (_) => _emit(),
    );
  }

  Future<void> stop() async {
    await _vitalsSub?.cancel();
    await _burstSub?.cancel();
    await _abdomenSub?.cancel();
    _vitalsSub = null;
    _burstSub = null;
    _abdomenSub = null;
    _emitTimer?.cancel();
    _emitTimer = null;
  }

  // Running mean of the chosen PPG channel — used to subtract DC so the
  // respiratory waveform widget can plot the AC envelope inside its
  // default −1.5..+2.5 Y range. EWMA gives reasonable adaptive
  // baseline tracking without a separate buffer.
  double _respBaseline = 0.0;
  static const double _respEwma = 0.05;  // ~20-sample time constant

  void _onVitals(VestVitals v) {
    _lastVitals = v;
    _ir1Buf.push(v.ir1);
    _iraBuf.push(v.ira);
    _redABuf.push(v.reda);

    // Pick whichever PPG channel is actually reading. Some vest builds
    // have one or two MAX30102 sensors silent at boot — fall back so
    // the waveform widgets always have a live signal.
    final ppg = v.ir1 > 0 ? v.ir1 : (v.ir2 > 0 ? v.ir2 : v.ira);

    // PPG widget uses minY=0, maxY=1 — typical raw counts are 30k–160k,
    // so divide by a generous max and clamp.
    if (ppg > 0) {
      _freshPpg.add((ppg / 200000.0).clamp(0.0, 1.0));
    }

    // Respiration is the slow chest-expansion modulation of the PPG
    // envelope. Subtract the running mean (DC component) and scale so
    // the AC component lands in the widget's −1.5..+2.5 default Y
    // range. Typical AC swing is a few thousand counts on top of a
    // 50k+ DC; dividing by 5000 gives roughly ±0.5..±1.5 amplitude.
    if (ppg > 0) {
      if (_respBaseline == 0) {
        _respBaseline = ppg.toDouble();
      } else {
        _respBaseline = (1 - _respEwma) * _respBaseline + _respEwma * ppg;
      }
      _freshResp.add((ppg - _respBaseline) / 5000.0);
    }
  }

  void _onBurst(EcgBurst b) {
    _ecgL1Buf.pushAll(b.lead1);
    _ecgL2Buf.pushAll(b.lead2);
    // Fan all three leads into separate streaming buffers so the
    // cardiology screen can overlay L1/L2/L3 (Einthoven triangle) on
    // a single graph. Lead III is computed as L3 = L2 - L1 per sample.
    _freshLead1.addAll(b.lead1);
    _freshLead2.addAll(b.lead2);
    final n = b.lead1.length < b.lead2.length ? b.lead1.length : b.lead2.length;
    for (var i = 0; i < n; i++) {
      _freshLead3.add(b.lead2[i] - b.lead1[i]);
    }
  }

  void _onAbdomen(AbdomenFrame f) {
    _lastAbdomenFrame = f;
    // Fetal heart-tone amplitude — average the two MEMS mics so the
    // CTG-style trace tracks the louder side. The firmware adaptively
    // band-pass filters around 110–180 BPM, so what we get here is
    // a real fetal heart-sound envelope, not a derivation.
    if (f.micVolts.isNotEmpty) {
      double sum = 0;
      var n = 0;
      for (final v in f.micVolts) {
        if (v != 0) {
          sum += v;
          n++;
        }
      }
      if (n > 0) {
        final avg = sum / n;
        // Centre around 0 for the LiveWaveform widget's −1.5..+2.5
        // default Y range. Mic voltages are typically 0.8–1.5 V; we
        // subtract the EWMA baseline so the AC envelope is visible
        // independent of mic gain drift.
        if (_fhrBaseline == 0) {
          _fhrBaseline = avg;
        } else {
          _fhrBaseline = (1 - _fhrEwma) * _fhrBaseline + _fhrEwma * avg;
        }
        // Scale so a typical heart-tone spike (~0.1 V above baseline)
        // lands as ~1.0 amplitude.
        _freshFhr.add((avg - _fhrBaseline) * 10.0);
      }
    }
    // Heart-tone detection flags (ht0 / ht1) — when either flips true
    // we add a spike so the trace shows discrete beat markers even when
    // the mic envelope is faint.
    if (f.heartTones.any((t) => t)) {
      _freshFhr.add(2.0);  // visible spike at the top of the band
    }
  }

  // Running mean of the fetal mic voltage — drives the FHR DC removal.
  double _fhrBaseline = 0.0;
  static const double _fhrEwma = 0.1;

  void _emit() {
    final v = _lastVitals;
    final f = _lastAbdomenFrame;
    final ir = _iraBuf.toList();
    final red = _redABuf.toList();
    final dsp = ir.isEmpty
        ? DspMetrics.empty
        : DspService.computeAll(ir, red, sampleRate: sampleRate);

    // Pull the freshest single ECG sample from the burst buffers — the
    // backend's `ecg.{}` block uses single-sample scalar values.
    double? ecgL1Latest, ecgL2Latest, ecgL3Latest;
    if (_ecgL1Buf.length > 0) {
      final l1 = _ecgL1Buf.toList();
      ecgL1Latest = l1[l1.length - 1];
    }
    if (_ecgL2Buf.length > 0) {
      final l2 = _ecgL2Buf.toList();
      ecgL2Latest = l2[l2.length - 1];
    }
    if (ecgL1Latest != null && ecgL2Latest != null) {
      ecgL3Latest = ecgL2Latest - ecgL1Latest;  // Einthoven
    }

    // Drain the streaming buffers — VestDataModel.updateFromStream
    // appends each list to its rolling 500-sample ValueNotifiers, so we
    // must NOT re-send samples already emitted last tick.
    final ecgL1Raw = _freshLead1.isEmpty ? null : List<double>.from(_freshLead1);
    final ecgL2Raw = _freshLead2.isEmpty ? null : List<double>.from(_freshLead2);
    final ecgL3Raw = _freshLead3.isEmpty ? null : List<double>.from(_freshLead3);
    final ppgRaw = _freshPpg.isEmpty ? null : List<double>.from(_freshPpg);
    final respRaw = _freshResp.isEmpty ? null : List<double>.from(_freshResp);
    final fhrRaw = _freshFhr.isEmpty ? null : List<double>.from(_freshFhr);
    _freshLead1.clear();
    _freshLead2.clear();
    _freshLead3.clear();
    _freshPpg.clear();
    _freshResp.clear();
    _freshFhr.clear();

    _ts++;
    final snapshot = <String, dynamic>{
      'timestamp': _ts,
      // Per-lead waveform streams. `ecg_raw` aliases Lead II for
      // existing widgets (single-trace cardiology fallback); the
      // multi-lead overlay reads ecg_lead{1,2,3}_raw separately.
      'ecg_raw': ?ecgL2Raw,
      'ecg_lead1_raw': ?ecgL1Raw,
      'ecg_lead2_raw': ?ecgL2Raw,
      'ecg_lead3_raw': ?ecgL3Raw,
      'ppg_raw': ?ppgRaw,
      'resp_raw': ?respRaw,
      // CTG-style fetal heart-tone trace from the AbdomenMonitor mics.
      // VestDataModel.updateFromStream consumes this into model.fhrData
      // for the obstetrics screen's LiveWaveform.
      'fhr_raw': ?fhrRaw,
      'ppg': {
        'ir1': v?.ir1 ?? 0.0,
        'red1': v?.red1 ?? 0.0,
        'ir2': v?.ir2 ?? 0.0,
        'red2': v?.red2 ?? 0.0,
        'ira': v?.ira ?? 0.0,
        'reda': v?.reda ?? 0.0,
        't1': v?.t1 ?? 0.0,
        't2': v?.t2 ?? 0.0,
      },
      'temperature': {
        'left_axilla': v?.tl ?? 0.0,
        'right_axilla': v?.tr ?? 0.0,
        // Cervical is the dashboard's primary "body temperature" reading.
        // If the cervical probe isn't contacting (TC=0), fall back to
        // whichever axilla probe IS reading — better to surface a real
        // skin temp than report 0°C while a different probe is reading
        // 33°C. Threshold 25°C filters out the firmware's "no-contact"
        // sentinel and ambient-equilibrium readings.
        'cervical': _bestSkinTemp(v),
      },
      'imu': {
        'upper_pitch': v?.upperPitch ?? 0.0,
        'upper_roll': v?.upperRoll ?? 0.0,
        'lower_pitch': v?.lowerPitch ?? 0.0,
        'lower_roll': v?.lowerRoll ?? 0.0,
        'spinal_angle': v?.spinalAngle ?? 0.0,
        'poor_posture': v?.poorPosture ?? false,
        // Mirror app.py's `posture_label(sa)` when SA is small;
        // we don't reimplement the full labeller — backend keeps that
        // when it processes the snapshot in /api/agent/* calls.
        'posture_label': _postureLabel(v?.spinalAngle ?? 0.0),
        'bmp180_pressure': v?.bmp180Pressure ?? 0.0,
        'bmp180_temp': v?.bmp180Temp ?? 0.0,
      },
      'environment': {
        'bmp280_pressure': v?.bmp280Pressure ?? 0.0,
        'bmp280_temp': v?.bmp280Temp ?? 0.0,
        'dht11_humidity': v?.dht11Humidity ?? 0.0,
        'dht11_temp': v?.dht11Temp ?? 0.0,
      },
      'ecg': {
        'lead1': ecgL1Latest ?? v?.ecgL1 ?? 0.0,
        'lead2': ecgL2Latest ?? v?.ecgL2 ?? 0.0,
        'lead3': ecgL3Latest ?? v?.ecgL3 ?? 0.0,
        'ecg_hr': v?.ecgHr ?? 0.0,
      },
      'audio': {
        'analog_rms': v?.analogRms ?? 0.0,
        'digital_rms': v?.digitalRms ?? 0.0,
      },
      'vitals': {
        // Prefer the firmware-side ECG HR when present (firmware QRS is
        // very robust); fall back to PPG-derived DSP HR otherwise.
        'heart_rate': (v?.ecgHr ?? 0) > 0 ? v!.ecgHr : dsp.heartRate,
        'spo2': dsp.spo2,
        'breathing_rate': dsp.breathingRate,
        'hrv_rmssd': dsp.hrvRmssd,
        'perfusion_index': dsp.perfusionIndex,
        'signal_quality': _signalQuality(dsp.perfusionIndex),
      },
      'connection': {
        'vest_connected': vest.status == BleStatus.connected,
        'fetal_connected': abdomen.status == BleStatus.connected,
        'using_mock': false,
      },
      'fetal': {
        'mode': f?.mode ?? 0,
        'piezo_raw': f?.piezoRaw ?? const [0, 0, 0, 0],
        'kicks': f?.kicks ?? const [false, false, false, false],
        'movement': f?.movement ?? const [false, false, false, false],
        'mic_volts': f?.micVolts ?? const [0.0, 0.0],
        'heart_tones': f?.heartTones ?? const [false, false],
        'bowel_sounds': f?.bowelSounds ?? const [false, false],
        'film_pressure': f?.filmPressure ?? const [0.0, 0.0],
        'contractions': f?.contractions ?? const [false, false],
        // Dawes-Redman analyser stays server-side (heavy windowed work).
        // The backend re-runs it on the snapshot in /api/agent/* paths.
        'dawes_redman': const <String, dynamic>{},
      },
      // Pharmacology + IMU-derived blocks are produced server-side. We
      // surface empty defaults so the UI's null-safe paths render
      // without exceptions. Once the snapshot lands at /api/agent/*,
      // the backend's full block replaces these.
      'pharmacology': const <String, dynamic>{
        'active_medication': null,
        'dose': 0.0,
        'sim_time': 0.0,
        'clearance_model': 'Normal Metabolizer',
      },
      'imu_derived': const <String, dynamic>{},
      // Edge anomaly flag — exposed so EdgeAnomalyService.ingest() reads it.
      'edge_alert': v?.edgeAlert ?? false,
      'edge_alert_reason': v?.edgeAlertReason ?? 'none',
      'AL': (v?.edgeAlert ?? false) ? 1 : 0,
      'REASON': v?.edgeAlertReason ?? 'none',
      'firmware_version': v?.firmwareVersion,
      // waveform + imaging stay null on mobile (heavy SSE-only fields).
      'waveform': null,
      'imaging': null,
    };

    _latest = snapshot;
    if (!_ctrl.isClosed) _ctrl.add(snapshot);
  }

  /// Pick the most plausible "body" reading from the three skin-temp
  /// probes. The DS18B20 firmware filter clamps no-contact reads (-127)
  /// to 0; we treat anything below 25°C as "probe not on skin" and
  /// fall back through cervical → left axilla → right axilla. Returns
  /// 0.0 only when ALL three probes are flat — surfaces honest "no
  /// contact" instead of a misleading single-probe zero.
  static double _bestSkinTemp(VestVitals? v) {
    if (v == null) return 0.0;
    const minPlausible = 25.0;
    if (v.tc >= minPlausible) return v.tc;
    if (v.tl >= minPlausible) return v.tl;
    if (v.tr >= minPlausible) return v.tr;
    // None of the probes are contacting — return whichever probe value is
    // numerically largest so the dashboard at least reflects ambient drift
    // instead of a hard 0. Still 0 when all three are 0.
    final m = [v.tc, v.tl, v.tr].reduce((a, b) => a > b ? a : b);
    return m;
  }

  static String _postureLabel(double sa) {
    final a = sa.abs();
    if (a < 5) return 'Good posture';
    if (a < 15) return 'Slight lean';
    if (a < 30) return 'Forward stoop';
    return 'Significant slouch';
  }

  static String _signalQuality(double pi) {
    if (pi == 0) return 'No contact';
    if (pi < 0.2) return 'Poor';
    if (pi < 0.5) return 'Fair';
    if (pi < 1.0) return 'Good';
    return 'Strong';
  }

  void dispose() {
    stop();
    _ctrl.close();
  }
}

/// Hint to a Float64List equality check used in tests.
extension on Float64List {
  // Kept so `import 'dart:typed_data'` is non-trivially used even if the
  // builder doesn't directly reference it after refactoring.
  // ignore: unused_element
  Float64List _trace() => this;
}
