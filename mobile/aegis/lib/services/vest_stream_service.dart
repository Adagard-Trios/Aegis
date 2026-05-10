import 'dart:async';

import 'package:flutter/foundation.dart';

import '../ble/ble_connection_supervisor.dart';
import '../models/vest_data_model.dart';
import '../pipeline/ble_telemetry_source.dart';
import '../pipeline/sse_telemetry_source.dart';
import '../pipeline/telemetry_source.dart';
import 'auth_service.dart';
import 'edge_anomaly_service.dart';
import 'local_cache_service.dart';
import 'sync_queue_service.dart';

/// Telemetry plumbing — owns whichever [TelemetrySource] is right for
/// the build target, drains its snapshots, and fans them out to:
///   - the [VestDataModel] (UI bindings)
///   - the Phase 4.3 services (cache + edge anomaly + sync queue)
///   - any caller of [latest] (e.g. SnapshotUploader, agent body)
///
/// Source selection:
///   - Web  → [SseTelemetrySource]  (no Bluetooth)
///   - Mobile (default) → [BleTelemetrySource]  (phone owns BLE)
class VestStreamService {
  final VestDataModel model;
  final AuthService? auth;
  final LocalCacheService? cache;
  final EdgeAnomalyService? anomaly;
  final SyncQueueService? syncQueue;

  /// The BLE supervisor that owns the vest + abdomen device services.
  /// Required on mobile (where the Sensors screen drives it manually);
  /// ignored on web (the SSE source doesn't need a radio).
  final BleConnectionSupervisor? supervisor;

  late final TelemetrySource _source;
  StreamSubscription<Map<String, dynamic>>? _snapSub;
  bool _isListening = false;
  bool _wasConnected = false;

  /// Latest snapshot the source has emitted. Used by `SnapshotUploader`
  /// and `ApiService` agent calls to attach the freshest local data.
  Map<String, dynamic>? get latestSnapshot => _source.latest;

  /// Allow tests / web demos to inject a different source.
  /// On mobile builds the constructor picks BLE by default; pass
  /// `forceSse: true` to fall back to SSE explicitly.
  VestStreamService({
    required this.model,
    this.auth,
    this.cache,
    this.anomaly,
    this.syncQueue,
    this.supervisor,
    TelemetrySource? source,
    bool forceSse = false,
  }) {
    if (source != null) {
      _source = source;
    } else if (kIsWeb || forceSse) {
      _source = SseTelemetrySource(auth: auth);
    } else {
      assert(supervisor != null,
          'BleConnectionSupervisor required on mobile builds');
      _source = BleTelemetrySource(supervisor: supervisor!);
    }
  }

  void startStream() {
    if (_isListening) return;
    _isListening = true;
    _snapSub = _source.snapshots.listen(_handle);
    _source.start();
    model.updateConnectionStatus(false, 'Connecting...');
  }

  Future<void> stopStream() async {
    _isListening = false;
    await _snapSub?.cancel();
    _snapSub = null;
    await _source.stop();
    model.updateConnectionStatus(false, 'Disconnected');
  }

  void _handle(Map<String, dynamic> snapshot) {
    if (!_isListening) return;
    final live = _source.isLive;
    final label = live
        ? (snapshot['connection']?['using_mock'] == true
            ? 'Connected (MOCK)'
            : 'Connected (LIVE)')
        : 'Reconnecting...';
    model.updateConnectionStatus(live, label);
    model.updateFromStream(snapshot);
    _onSnapshot(snapshot);

    if (live && !_wasConnected) {
      _wasConnected = true;
      unawaited(_flushSyncQueue());
    } else if (!live) {
      _wasConnected = false;
    }
  }

  /// Phase 4 hook — preserved verbatim from the SSE-era implementation.
  void _onSnapshot(Map<String, dynamic> snapshot) {
    cache?.push(snapshot);
    anomaly?.ingest(snapshot);
    if (syncQueue != null && !_wasConnected) {
      syncQueue!.enqueue(snapshot);
    }
  }

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

  /// Direct access to the underlying source — used by injection points
  /// like the Obstetrics screen mode picker (writes mode characteristic
  /// on the abdomen device) and by SnapshotUploader.
  TelemetrySource get source => _source;

  void dispose() {
    stopStream();
    _source.dispose();
  }
}
