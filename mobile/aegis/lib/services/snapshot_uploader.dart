import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../ble/ble_constants.dart';
import 'api_config.dart';
import 'auth_service.dart';
import 'vest_stream_service.dart';

/// Pushes the latest local snapshot to the backend on a 15 s cadence so
/// `/api/history`, `/api/fhir/*`, the alerts evaluator, and the
/// background agent loop have continuous data when the phone owns the
/// BLE radio.
///
/// Sends header `X-Aegis-Source: mobile-ble` so the backend can suppress
/// its own BLE thread for the next 60 s — see app.py
/// `sqlite_writer_loop` mobile-owns-BLE flag.
///
/// Disabled on web (`kIsWeb`) because there's no local snapshot to push.
class SnapshotUploader {
  final VestStreamService stream;
  final AuthService? auth;
  final Duration interval;

  /// Patient identifier this uploader binds to. Override per-session
  /// once you have multi-patient routing on the mobile side.
  final String patientId;

  Timer? _timer;
  bool _running = false;
  int _consecutiveFailures = 0;
  int get consecutiveFailures => _consecutiveFailures;

  SnapshotUploader({
    required this.stream,
    this.auth,
    this.patientId = 'medverse-demo-patient',
    this.interval = const Duration(seconds: 15),
  });

  /// Begin periodic uploads. No-op on web.
  void start() {
    if (kIsWeb || _running) return;
    _running = true;
    _timer = Timer.periodic(interval, (_) => _push());
  }

  void stop() {
    _running = false;
    _timer?.cancel();
    _timer = null;
  }

  Future<void> _push() async {
    final snap = stream.latestSnapshot;
    if (snap == null) return;
    try {
      final res = await http
          .post(
            Uri.parse('${ApiConfig.baseUrl}/api/snapshot/ingest'),
            headers: {
              'Content-Type': 'application/json',
              BleTuning.mobileSourceHeader: BleTuning.mobileSourceValue,
              if (auth != null) ...auth!.authHeaders(),
            },
            body: jsonEncode({
              'patient_id': patientId,
              'snapshot': snap,
            }),
          )
          // Generous timeout absorbs Render free-tier cold-start
          // (~30 s wake) on the first push of a session. Subsequent
          // pushes are sub-second.
          .timeout(const Duration(seconds: 60));
      if (res.statusCode >= 200 && res.statusCode < 300) {
        _consecutiveFailures = 0;
      } else if (res.statusCode >= 400 && res.statusCode < 500) {
        // 4xx — drop, don't retry. Probably wrong contract.
        debugPrint('[SnapshotUploader] dropped: ${res.statusCode}');
      } else {
        // 5xx — backend hiccup. Bump counter; the next periodic tick retries.
        _consecutiveFailures++;
      }
    } catch (e) {
      _consecutiveFailures++;
      debugPrint('[SnapshotUploader] push failed: $e');
    }
  }

  void dispose() {
    stop();
  }
}
