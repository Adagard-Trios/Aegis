import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import '../models/vest_data_model.dart';
import 'api_config.dart';
import 'auth_service.dart';
import 'local_cache_service.dart';
import 'edge_anomaly_service.dart';
import 'sync_queue_service.dart';

class VestStreamService {
  final VestDataModel model;
  final AuthService? auth;
  // Phase 4 IoMT additions — optional services. Passing them in lets the
  // app keep using VestStreamService directly when offline-mode + edge
  // alerts aren't needed (e.g. tests, mock-data demos).
  final LocalCacheService? cache;
  final EdgeAnomalyService? anomaly;
  final SyncQueueService? syncQueue;
  http.Client? _client;
  bool _isListening = false;
  int _reconnectAttempts = 0;
  bool _wasConnected = false;

  // Set to true to use local 10Hz mock waveforms without connecting to the Python backend
  bool useMockData = true;
  Timer? _mockTimer;
  double _phase = 0;

  VestStreamService({
    required this.model,
    this.auth,
    this.cache,
    this.anomaly,
    this.syncQueue,
  });

  String get baseUrl => ApiConfig.baseUrl;

  void startStream() async {
    if (_isListening) return;
    _isListening = true;
    _reconnectAttempts = 0;

    if (useMockData) {
      _startMockStream();
    } else {
      _connect();
    }
  }

  void stopStream() {
    _isListening = false;
    _client?.close();
    _client = null;
    _mockTimer?.cancel();
    model.updateConnectionStatus(false, 'Disconnected');
  }

  void _startMockStream() {
    model.updateConnectionStatus(true, 'Connected (MOCK DATA)');
    
    // Simulate a 10Hz SSE stream using Timer.periodic (100ms)
    _mockTimer = Timer.periodic(const Duration(milliseconds: 100), (timer) {
      if (!_isListening) {
        timer.cancel();
        return;
      }

      // Generate 5-10 samples per 100ms packet to create smooth wave animations
      List<double> ecgChunk = [];
      List<double> ppgChunk = [];
      List<double> rspChunk = [];
      List<double> fhrChunk = [];

      for (int i = 0; i < 5; i++) {
        _phase += 0.15;
        
        // Complex mocked ECG shape: small p wave, QRS spike, t wave
        double ecgVal = sin(_phase) * 0.2 + // Baseline wander / T-wave
            (sin(_phase * 2) * 0.1) + // P wave
            ((_phase % (pi * 2)) < 0.2 ? 2.5 : 0.0) - // R spike positive
            ((_phase % (pi * 2)) > 0.2 && (_phase % (pi * 2)) < 0.3 ? 0.8 : 0.0); // S spike negative

        ecgChunk.add(ecgVal);
        ppgChunk.add(sin(_phase * 0.8 + 1) * 0.6 + 0.5); // PPG resembles blood volume pressure
        rspChunk.add(sin(_phase * 0.2) * 1.2); // Slower respiratory wave
        fhrChunk.add(sin(_phase * 1.5) * 0.2 + 0.8); // FHR doppler mock
      }

      // Low frequency metrics simulated alongside
      final mockData = {
        'ecg_raw': ecgChunk,
        'ppg_raw': ppgChunk,
        'resp_raw': rspChunk,
        'fhr_raw': fhrChunk, // Appears on Obstetrics Screen
        
        'heart_rate': 72 + (sin(_phase * 0.05) * 4).toInt(),
        'spo2': 98 + (sin(_phase * 0.01) * 1).toInt(),
        'temperature': 36.6 + (sin(_phase * 0.02) * 0.3),
        'respiratory_rate': 16 + (cos(_phase * 0.05) * 2).toInt(),
        
        'blood_pressure': {
          'systolic': 118 + (sin(_phase * 0.05) * 5),
          'diastolic': 78 + (cos(_phase * 0.05) * 4)
        },
        'posture': (sin(_phase * 0.02) > 0) ? 'Sitting' : 'Standing',
      };

      model.updateFromStream(mockData);
      _onSnapshot(mockData);
    });
  }

  /// Phase 4 hook: cache the snapshot, run the edge anomaly detector,
  /// and (when offline) enqueue for later sync. Cheap to call on the
  /// hot path — each service is an in-memory shim.
  void _onSnapshot(Map<String, dynamic> snapshot) {
    cache?.push(snapshot);
    anomaly?.ingest(snapshot);
    if (syncQueue != null && !_wasConnected) {
      syncQueue!.enqueue(snapshot);
    }
  }

  /// Drain anything we cached during a disconnect. Replays each into
  /// the local model so the UI fills in missing samples; backend-side
  /// sync would happen here too once that path is wired.
  Future<void> _flushSyncQueue() async {
    if (syncQueue == null || syncQueue!.length == 0) return;
    try {
      await syncQueue!.flushTo((snapshot) async {
        model.updateFromStream(snapshot);
      });
    } catch (e) {
      debugPrint('sync flush partial: $e');
    }
  }

  Future<void> _connect() async {
    while (_isListening) {
      model.updateConnectionStatus(false, 'Connecting...');
      try {
        _client = http.Client();
        final uri = Uri.parse('$baseUrl/stream');
        final streamUrl = auth != null ? auth!.appendToken(uri) : uri.toString();
        final request = http.Request('GET', Uri.parse(streamUrl));
        if (auth != null) request.headers.addAll(auth!.authHeaders(extra: {}));
        final response = await _client!.send(request);

        if (response.statusCode == 200) {
          model.updateConnectionStatus(true, 'Connected (LIVE)');
          _reconnectAttempts = 0;
          if (!_wasConnected) {
            // Just came back online — drain anything we queued offline.
            _wasConnected = true;
            _flushSyncQueue();
          }

          await response.stream
              .transform(utf8.decoder)
              .transform(const LineSplitter())
              .forEach((line) {
            if (!_isListening) return;
            if (line.startsWith('data: ')) {
              final jsonStr = line.substring(6).trim();
              if (jsonStr.isEmpty) return;
              try {
                final Map<String, dynamic> data = jsonDecode(jsonStr);
                model.updateFromStream(data);
                _onSnapshot(data);
              } catch (e) {
                debugPrint("JSON Parse Error: $e");
              }
            }
          });
        }
      } catch (e) {
        debugPrint('Stream error: $e');
      }

      if (_isListening) {
        _wasConnected = false;
        _reconnectAttempts++;
        model.updateConnectionStatus(false, 'Reconnecting ($_reconnectAttempts)...');
        final delay = (_reconnectAttempts * 1000).clamp(1000, 5000);
        await Future.delayed(Duration(milliseconds: delay));
      }
    }
  }
}
