import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../services/api_config.dart';
import '../services/auth_service.dart';
import 'telemetry_source.dart';

/// Telemetry source that subscribes to the FastAPI `/stream` SSE
/// endpoint. Web build only — on Android / iOS the BLE source is the
/// canonical path.
///
/// Auto-reconnect on disconnect with linear backoff (1 → 5 s).
class SseTelemetrySource implements TelemetrySource {
  final AuthService? auth;

  http.Client? _client;
  bool _wantConnected = false;
  bool _isLive = false;
  int _reconnectAttempts = 0;
  Map<String, dynamic>? _latest;

  final _ctrl = StreamController<Map<String, dynamic>>.broadcast();

  SseTelemetrySource({this.auth});

  @override
  Stream<Map<String, dynamic>> get snapshots => _ctrl.stream;

  @override
  Map<String, dynamic>? get latest => _latest;

  @override
  bool get isLive => _isLive;

  @override
  Future<void> start() async {
    if (_wantConnected) return;
    _wantConnected = true;
    _reconnectAttempts = 0;
    unawaited(_connect());
  }

  @override
  Future<void> stop() async {
    _wantConnected = false;
    _client?.close();
    _client = null;
    _isLive = false;
  }

  Future<void> _connect() async {
    while (_wantConnected) {
      try {
        _client = http.Client();
        final uri = Uri.parse('${ApiConfig.baseUrl}/stream');
        final url = auth != null ? auth!.appendToken(uri) : uri.toString();
        final request = http.Request('GET', Uri.parse(url));
        if (auth != null) request.headers.addAll(auth!.authHeaders(extra: {}));
        final response = await _client!.send(request);
        if (response.statusCode == 200) {
          _isLive = true;
          _reconnectAttempts = 0;
          await response.stream
              .transform(utf8.decoder)
              .transform(const LineSplitter())
              .forEach((line) {
            if (!_wantConnected) return;
            if (!line.startsWith('data: ')) return;
            final body = line.substring(6).trim();
            if (body.isEmpty) return;
            try {
              final data = jsonDecode(body) as Map<String, dynamic>;
              _latest = data;
              if (!_ctrl.isClosed) _ctrl.add(data);
            } catch (e) {
              debugPrint('[SseSource] JSON parse error: $e');
            }
          });
        }
      } catch (e) {
        debugPrint('[SseSource] stream error: $e');
      }

      if (_wantConnected) {
        _isLive = false;
        _reconnectAttempts++;
        final delay = (_reconnectAttempts * 1000).clamp(1000, 5000);
        await Future.delayed(Duration(milliseconds: delay));
      }
    }
  }

  @override
  void dispose() {
    stop();
    _ctrl.close();
  }
}
