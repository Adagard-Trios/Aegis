import 'dart:math';
import 'dart:typed_data';

/// Lightweight Butterworth filter implementations sized for live PPG /
/// audio biomedical work — single-pass IIR (introduces phase shift,
/// unlike scipy's `filtfilt` zero-phase). The DSP plan accepts this
/// trade-off; the golden-data tolerance budget (HR ±1 BPM, SpO2 ±1,
/// BR ±1, HRV ±2 ms, PI ±0.05) was chosen to stay within reach.
///
/// All filters here are 2nd-order biquads designed via the bilinear
/// transform with prewarping. The 3rd-order order used in the Python
/// counterpart compounds attenuation slightly more steeply, but the
/// peak-finder downstream is robust to small residual envelope shifts.
class Biquad {
  final double b0, b1, b2, a1, a2;
  double _z1 = 0, _z2 = 0;

  Biquad(this.b0, this.b1, this.b2, this.a1, this.a2);

  double process(double x) {
    final y = b0 * x + _z1;
    _z1 = b1 * x - a1 * y + _z2;
    _z2 = b2 * x - a2 * y;
    return y;
  }

  void reset() {
    _z1 = 0;
    _z2 = 0;
  }

  /// Run a complete signal through this biquad.
  Float64List run(Float64List x) {
    final y = Float64List(x.length);
    for (var i = 0; i < x.length; i++) {
      y[i] = process(x[i]);
    }
    return y;
  }
}

class Filters {
  /// 2nd-order Butterworth band-pass biquad, designed via bilinear
  /// transform with prewarping. `lowHz` and `highHz` are the -3 dB
  /// edges; `fs` is the sample rate.
  ///
  /// Returns a fresh [Biquad] (state-clearing on each call) suitable
  /// for one signal pass.
  static Biquad bandpass(double lowHz, double highHz, double fs) {
    final w0 = 2 * pi * sqrt(lowHz * highHz) / fs;     // geometric centre
    final bw = log(highHz / lowHz) / ln2;              // bandwidth in oct
    final alpha = sin(w0) * sinh(0.5 * ln2 * bw * w0 / sin(w0));

    final cosw = cos(w0);
    final a0 = 1 + alpha;
    final b0 = alpha / a0;
    final b1 = 0.0;
    final b2 = -alpha / a0;
    final a1 = -2 * cosw / a0;
    final a2 = (1 - alpha) / a0;
    return Biquad(b0, b1, b2, a1, a2);
  }

  /// 2nd-order Butterworth low-pass biquad.
  static Biquad lowpass(double cutoffHz, double fs) {
    final w0 = 2 * pi * cutoffHz / fs;
    final cosw = cos(w0);
    final alpha = sin(w0) / (2 * 0.7071067811865476); // Q = 1/√2 (Butterworth)
    final a0 = 1 + alpha;
    final b0 = (1 - cosw) / 2 / a0;
    final b1 = (1 - cosw) / a0;
    final b2 = (1 - cosw) / 2 / a0;
    final a1 = -2 * cosw / a0;
    final a2 = (1 - alpha) / a0;
    return Biquad(b0, b1, b2, a1, a2);
  }

  /// hyperbolic sine — Dart math doesn't ship one.
  static double sinh(double x) => (exp(x) - exp(-x)) / 2;

  /// Mean of a Float64List (NaN-safe — empty input returns 0).
  static double mean(Float64List x) {
    if (x.isEmpty) return 0;
    var s = 0.0;
    for (var i = 0; i < x.length; i++) {
      s += x[i];
    }
    return s / x.length;
  }

  /// Population standard deviation — matches numpy `np.std` default.
  static double std(Float64List x) {
    if (x.isEmpty) return 0;
    final m = mean(x);
    var s = 0.0;
    for (var i = 0; i < x.length; i++) {
      final d = x[i] - m;
      s += d * d;
    }
    return sqrt(s / x.length);
  }

  /// In-place sign flip — used by the HR detector (peaks of -filtered).
  static Float64List negate(Float64List x) {
    final y = Float64List(x.length);
    for (var i = 0; i < x.length; i++) {
      y[i] = -x[i];
    }
    return y;
  }
}
