import 'dart:async';

import '../ble/ble_connection_supervisor.dart';
import '../ble/ble_vest_service.dart';
import 'local_snapshot_builder.dart';
import 'telemetry_source.dart';

/// Telemetry source backed by direct BLE.
///
/// Holds a reference to the [BleConnectionSupervisor] (which owns the
/// vest + abdomen services) and the [LocalSnapshotBuilder] that turns
/// raw BLE streams into the SSE-shaped snapshot dict the rest of the
/// app expects.
///
/// The supervisor is now expected to be owned by the provider tree
/// (so the Sensors screen can drive scan/connect manually); this
/// source does NOT auto-start scanning. It just keeps the snapshot
/// builder ticking — empty snapshots flow until the user connects a
/// device, after which the builder picks up its event streams.
class BleTelemetrySource implements TelemetrySource {
  final BleConnectionSupervisor supervisor;
  late final LocalSnapshotBuilder builder;

  BleTelemetrySource({
    required this.supervisor,
    LocalSnapshotBuilder? builder,
  }) {
    this.builder = builder ??
        LocalSnapshotBuilder(
          vest: supervisor.vest,
          abdomen: supervisor.abdomen,
        );
  }

  @override
  Stream<Map<String, dynamic>> get snapshots => builder.stream;

  @override
  Map<String, dynamic>? get latest => builder.latest;

  @override
  bool get isLive =>
      supervisor.vest.status == BleStatus.connected ||
      supervisor.abdomen.status == BleStatus.connected;

  @override
  Future<void> start() async {
    builder.start();
    await supervisor.start();
  }

  @override
  Future<void> stop() async {
    await supervisor.stop();
    await builder.stop();
  }

  @override
  void dispose() {
    builder.dispose();
    // The supervisor is owned by the provider tree (registered in
    // main.dart) — disposing it here would break the Sensors screen,
    // which still needs it after this source is torn down.
  }
}
