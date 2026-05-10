import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

import 'ble_abdomen_service.dart';
import 'ble_vest_service.dart';

/// Top-level owner of both BLE devices.
///
/// Hides the dual-device dance from the rest of the app — the
/// `BleConnectionSupervisor` is the single ChangeNotifier consumers
/// listen to for "is at least one of my sensors connected?" UX.
///
/// This is intentionally thin — it doesn't try to time-multiplex BLE
/// scans because flutter_blue_plus tolerates concurrent
/// scan-by-name calls and Android's stack will arbitrate. If we hit
/// scan contention in practice, this is the place to add a serialised
/// scan loop.
class BleConnectionSupervisor extends ChangeNotifier {
  final BleVestService vest;
  final BleAbdomenService abdomen;

  bool _started = false;

  BleConnectionSupervisor({
    BleVestService? vest,
    BleAbdomenService? abdomen,
  })  : vest = vest ?? BleVestService(),
        abdomen = abdomen ?? BleAbdomenService() {
    this.vest.addListener(_relay);
    this.abdomen.addListener(_relay);
  }

  void _relay() => notifyListeners();

  bool get vestConnected => vest.status == BleStatus.connected;
  bool get abdomenConnected => abdomen.status == BleStatus.connected;
  bool get anyConnected => vestConnected || abdomenConnected;

  /// Pre-warm the radio so the first user-initiated scan is responsive.
  /// Does NOT auto-scan or auto-connect — the Sensors screen drives the
  /// scan / connect lifecycle explicitly via vest.startScan / connectTo.
  Future<void> start() async {
    if (_started) return;
    _started = true;
    if (!kIsWeb) {
      try {
        if (await FlutterBluePlus.isSupported == false) {
          debugPrint('[BleSupervisor] BLE not supported on this device');
          return;
        }
      } catch (_) {
        // Some platforms throw on isSupported probing — swallow.
      }
    }
  }

  /// Convenience for headless smoke tests / demo seeds — kicks both
  /// services into auto-scan + auto-connect mode. The mobile UI does
  /// NOT call this; Sensors screen drives manual scan/connect instead.
  Future<void> startAuto() async {
    await start();
    await vest.start();
    await abdomen.start();
  }

  Future<void> stop() async {
    if (!_started) return;
    _started = false;
    await vest.stop();
    await abdomen.stop();
  }

  @override
  void dispose() {
    vest.removeListener(_relay);
    abdomen.removeListener(_relay);
    vest.dispose();
    abdomen.dispose();
    super.dispose();
  }
}
