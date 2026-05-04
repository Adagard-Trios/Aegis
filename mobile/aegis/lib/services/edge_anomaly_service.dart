import 'package:flutter/foundation.dart';

/// Phone-side edge anomaly detector.
///
/// Two paths feed this service:
///   1. The vest's own AL/REASON flag (firmware v3.9+) — when the BLE
///      payload reports AL=1 we trust the firmware filter and surface
///      the alert immediately.
///   2. A windowed z-score fallback for older firmware that doesn't
///      emit AL — keeps a 60-sample (≈ 60s @ 1 Hz) HR window and
///      trips when the latest reading exceeds ±3σ.
///
/// Subscribers (the dashboard banner, a future native-notification
/// hook) listen via ChangeNotifier. Resetting `acknowledged()` clears
/// the active flag so the banner can be dismissed without waiting for
/// the underlying signal to return to baseline.
class EdgeAnomalyService extends ChangeNotifier {
  static const int _windowSize = 60;
  static const double _zThreshold = 3.0;

  final List<double> _hrWindow = [];
  bool _active = false;
  String _reason = 'none';
  DateTime? _lastTriggeredAt;

  bool get active => _active;
  String get reason => _reason;
  DateTime? get lastTriggeredAt => _lastTriggeredAt;

  /// Feed one snapshot from the live stream. Always call this — the
  /// service decides internally whether to trip a flag.
  void ingest(Map<String, dynamic> snapshot) {
    // Path 1: firmware-side flag (v3.9+).
    final firmwareFlag = snapshot['edge_alert'] ?? snapshot['AL'];
    if (firmwareFlag == 1 || firmwareFlag == true) {
      final reason = (snapshot['edge_alert_reason'] ??
              snapshot['REASON'] ??
              'firmware_anomaly')
          .toString();
      _trip(reason);
      return;
    }

    // Path 2: phone-side z-score on HR. Skipped when no HR available.
    final hr = _readNum(snapshot['heart_rate']) ??
        _readNum((snapshot['vitals'] as Map?)?['heart_rate']);
    if (hr == null || hr <= 0) return;

    _hrWindow.add(hr);
    if (_hrWindow.length > _windowSize) {
      _hrWindow.removeAt(0);
    }

    // Need a settled window before trusting z-score
    if (_hrWindow.length < _windowSize ~/ 2) {
      _maybeRelease();
      return;
    }

    final mean = _hrWindow.reduce((a, b) => a + b) / _hrWindow.length;
    final variance = _hrWindow
            .map((v) => (v - mean) * (v - mean))
            .reduce((a, b) => a + b) /
        _hrWindow.length;
    final stddev = variance > 0 ? variance.toDouble().abs() : 0.0;
    if (stddev < 1e-3) {
      _maybeRelease();
      return;
    }

    final z = (hr - mean) / _sqrt(stddev);
    if (z.abs() > _zThreshold) {
      _trip(z > 0 ? 'hr_outlier_high' : 'hr_outlier_low');
    } else {
      _maybeRelease();
    }
  }

  /// Dismiss the active alert from the UI without waiting for the
  /// signal to normalise. Doesn't clear the underlying window.
  void acknowledge() {
    if (!_active) return;
    _active = false;
    _reason = 'none';
    notifyListeners();
  }

  void _trip(String reason) {
    if (_active && _reason == reason) return; // dedupe — don't spam
    _active = true;
    _reason = reason;
    _lastTriggeredAt = DateTime.now();
    notifyListeners();
  }

  void _maybeRelease() {
    if (!_active) return;
    // Only auto-release when the firmware flag wasn't the source. The
    // firmware flag is sticky until the band condition clears; we don't
    // want the phone to silently drop a real alarm because the running
    // mean caught up.
    if (_reason.startsWith('firmware')) return;
    _active = false;
    _reason = 'none';
    notifyListeners();
  }

  static double? _readNum(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString());
  }

  // Tiny inline sqrt to avoid an extra import; the math.sqrt would do
  // but importing dart:math just for one call is needless ceremony.
  static double _sqrt(double x) {
    if (x <= 0) return 0;
    double r = x;
    for (int i = 0; i < 16; i++) {
      r = 0.5 * (r + x / r);
    }
    return r;
  }
}
