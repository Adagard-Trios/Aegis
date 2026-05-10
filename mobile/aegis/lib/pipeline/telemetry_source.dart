/// Abstract source of telemetry snapshots.
///
/// Two implementations:
///   - [BleTelemetrySource]: scans BLE devices, runs DSP locally, emits
///     snapshot dicts in the backend's `build_telemetry_snapshot()`
///     shape. Used on Android + iOS.
///   - [SseTelemetrySource]: connects to the FastAPI `/stream` endpoint
///     and forwards backend-built snapshots. Used on web (`kIsWeb`).
///
/// Each emits `Map<String, dynamic>` snapshots that match the existing
/// SSE shape exactly so VestDataModel.updateFromStream + the Phase 4.3
/// services (cache / anomaly / queue) need zero changes.
abstract class TelemetrySource {
  /// Snapshot stream — broadcast, keep-alive across listeners.
  Stream<Map<String, dynamic>> get snapshots;

  /// Latest snapshot, or null if none seen yet. Used by ApiService to
  /// attach the freshest local snapshot in /api/agent/* call bodies.
  Map<String, dynamic>? get latest;

  /// Begin producing snapshots. Idempotent.
  Future<void> start();

  /// Stop and release resources.
  Future<void> stop();

  /// True when the source has at least one upstream input alive
  /// (BLE link up, or SSE connection open).
  bool get isLive;

  /// Tear down. Stops upstreams + closes the snapshot stream.
  void dispose();
}
