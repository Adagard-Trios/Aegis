import 'dart:math';
import 'dart:typed_data';

import 'filters.dart';
import 'peak_finder.dart';

/// Output of one DSP pass — what `LocalSnapshotBuilder` injects into
/// the `vitals` block of the snapshot dict.
class DspMetrics {
  final double heartRate;       // BPM
  final double spo2;            // %
  final double breathingRate;   // breaths / min
  final double hrvRmssd;        // ms
  final double perfusionIndex;  // %

  const DspMetrics({
    required this.heartRate,
    required this.spo2,
    required this.breathingRate,
    required this.hrvRmssd,
    required this.perfusionIndex,
  });

  static const empty = DspMetrics(
    heartRate: 0, spo2: 0, breathingRate: 0, hrvRmssd: 0, perfusionIndex: 0,
  );
}

/// Pure-function ports of the Python DSP in app.py:303–368.
///
/// All inputs are buffers of raw PPG samples (IR / Red counts). Sample
/// rate defaults to 40 Hz to match the firmware payload cadence; pass
/// the firmware-reported `MEDVERSE_SAMPLE_RATE` if that's been bumped.
///
/// Tolerance budget vs. Python (DSP plan):
///   HR ±1 BPM   |  SpO2 ±1   |  BR ±1   |  HRV ±2 ms   |  PI ±0.05
class DspService {
  /// Vest BLE publish rate. Set by `BLE_TX_INTERVAL=40ms` in
  /// [PlatformIO/vest/src/config.h](PlatformIO/vest/src/config.h) →
  /// 25 Hz vitals notifies. The firmware reads PPG internally at 40 Hz
  /// but only forwards the latest sample per BLE notify, so the
  /// effective on-phone sampling rate is 25 Hz. All DSP windows
  /// (BR_WINDOW, SPO2_WINDOW, HR window) and Butterworth filter design
  /// derive from this — so it MUST match the firmware.
  static const int defaultSampleRate = 25;

  /// Firmware default windows (`SPO2_WINDOW = SAMPLE_RATE * 4`,
  /// `BR_WINDOW = SAMPLE_RATE * 10`). If you ingest from a custom
  /// sample-rate firmware, derive these.
  static int spo2Window(int fs) => fs * 4;
  static int brWindow(int fs) => fs * 10;

  /// Empirical SpO2 lookup table — same values as `app.py`. Indexed by
  /// `int((R - 0.4) * 10)`, clamped to the table range.
  static const List<int> _spo2Table = [
    100, 100, 100, 100, 99, 99, 99, 98, 98, 98,
    97, 97, 96, 96, 95, 95, 94, 94, 93, 93,
    92, 92, 91, 90, 89, 88, 86, 85, 83, 81,
  ];

  /// SpO2 estimate from synced IR / Red windows. Returns `0.0` when the
  /// signal is too weak (`mean(IR) < 1000` or `std(IR) < 10`).
  static double calculateSpo2(
    Float64List ir,
    Float64List red, {
    int sampleRate = defaultSampleRate,
  }) {
    final w = spo2Window(sampleRate);
    if (ir.length < w || red.length < w) return 0.0;
    final irW = _tail(ir, w);
    final redW = _tail(red, w);
    final irMean = Filters.mean(irW);
    if (irMean < 1000) return 0.0;
    final irStd = Filters.std(irW);
    final redMean = Filters.mean(redW);
    final redStd = Filters.std(redW);
    if (irMean == 0 || redMean == 0 || irStd < 10) return 0.0;
    final r = (redStd / redMean) / (irStd / irMean);
    final ix = ((r - 0.4) * 10).floor().clamp(0, _spo2Table.length - 1);
    return _spo2Table[ix].toDouble();
  }

  /// Heart rate from an IR PPG buffer. Mirrors `calculate_heart_rate`
  /// in app.py — bandpass 0.5–4 Hz, peak-find on the negative envelope,
  /// average the last 8 inter-peak intervals.
  static double calculateHeartRate(
    Float64List ir, {
    int sampleRate = defaultSampleRate,
  }) {
    if (ir.length < sampleRate * 4) return 0.0;
    final filtered = Filters.bandpass(0.5, 4.0, sampleRate.toDouble()).run(ir);
    final neg = Filters.negate(filtered);
    final minDist = (sampleRate * 60 / 180).round();
    final prominence = Filters.std(filtered) * 0.5;
    final peaks = PeakFinder.findPeaks(neg,
        minDistance: minDist, minProminence: prominence);
    if (peaks.length < 2) return 0.0;
    final lastN = peaks.length > 8 ? peaks.sublist(peaks.length - 8) : peaks;
    final intervals = <double>[];
    for (var i = 1; i < lastN.length; i++) {
      intervals.add((lastN[i] - lastN[i - 1]) / sampleRate);
    }
    final mean = intervals.reduce((a, b) => a + b) / intervals.length;
    if (mean <= 0) return 0.0;
    final bpm = 60.0 / mean;
    return _round1(bpm.clamp(30.0, 220.0));
  }

  /// HRV (RMSSD ms) from an IR PPG buffer. Mirrors `calculate_hrv`.
  static double calculateHrv(
    Float64List ir, {
    int sampleRate = defaultSampleRate,
  }) {
    if (ir.length < sampleRate * 8) return 0.0;
    final filtered = Filters.bandpass(0.5, 4.0, sampleRate.toDouble()).run(ir);
    final neg = Filters.negate(filtered);
    final minDist = (sampleRate * 60 / 180).round();
    final prominence = Filters.std(filtered) * 0.5;
    final peaks = PeakFinder.findPeaks(neg,
        minDistance: minDist, minProminence: prominence);
    if (peaks.length < 4) return 0.0;
    final rrMs = <double>[
      for (var i = 1; i < peaks.length; i++)
        (peaks[i] - peaks[i - 1]) / sampleRate * 1000,
    ];
    final diff = <double>[
      for (var i = 1; i < rrMs.length; i++) rrMs[i] - rrMs[i - 1],
    ];
    if (diff.isEmpty) return 0.0;
    final meanSq = diff.fold<double>(0, (a, b) => a + b * b) / diff.length;
    return _round1(sqrt(meanSq));
  }

  /// Breathing rate from an IR PPG buffer. Mirrors
  /// `calculate_breathing_rate`. Uses a 0.5 Hz lowpass + peak-find.
  static double calculateBreathingRate(
    Float64List ir, {
    int sampleRate = defaultSampleRate,
  }) {
    final w = brWindow(sampleRate);
    if (ir.length < w) return 0.0;
    final tail = _tail(ir, w);
    final filtered = Filters.lowpass(0.5, sampleRate.toDouble()).run(tail);
    final minDist = (sampleRate * 60 / 40).round();
    final prominence = Filters.std(filtered) * 0.3;
    final peaks = PeakFinder.findPeaks(filtered,
        minDistance: minDist, minProminence: prominence);
    if (peaks.length < 2) return 0.0;
    final intervals = <double>[
      for (var i = 1; i < peaks.length; i++)
        (peaks[i] - peaks[i - 1]) / sampleRate,
    ];
    final meanInt = intervals.reduce((a, b) => a + b) / intervals.length;
    if (meanInt <= 0) return 0.0;
    final bpm = 60.0 / meanInt;
    return _round1(bpm.clamp(4.0, 40.0));
  }

  /// Perfusion index (%). Mirrors `calculate_pi`.
  static double calculatePi(
    Float64List ir, {
    int sampleRate = defaultSampleRate,
  }) {
    final w = spo2Window(sampleRate);
    if (ir.length < 10) return 0.0;
    final tail = _tail(ir, w);
    final m = Filters.mean(tail);
    if (m == 0) return 0.0;
    return _round2((Filters.std(tail) / m) * 100);
  }

  /// Compose all five metrics in one pass, sharing the IR buffer where
  /// possible. Used by `LocalSnapshotBuilder` once per second.
  static DspMetrics computeAll(
    Float64List ir,
    Float64List red, {
    int sampleRate = defaultSampleRate,
  }) {
    return DspMetrics(
      heartRate: calculateHeartRate(ir, sampleRate: sampleRate),
      spo2: calculateSpo2(ir, red, sampleRate: sampleRate),
      breathingRate: calculateBreathingRate(ir, sampleRate: sampleRate),
      hrvRmssd: calculateHrv(ir, sampleRate: sampleRate),
      perfusionIndex: calculatePi(ir, sampleRate: sampleRate),
    );
  }

  // ── helpers ─────────────────────────────────────────────────────────

  static Float64List _tail(Float64List x, int n) {
    if (x.length <= n) return x;
    return Float64List.sublistView(x, x.length - n);
  }

  static double _round1(double v) => (v * 10).round() / 10;
  static double _round2(double v) => (v * 100).round() / 100;
}
