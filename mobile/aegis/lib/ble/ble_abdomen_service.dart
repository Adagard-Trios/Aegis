import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

import 'ble_constants.dart';
import 'ble_payload_parser.dart';
import 'ble_vest_service.dart' show BleStatus;

class AbdomenEvent {
  final int tsMs;
  final String type;
  final String? detail;
  const AbdomenEvent(this.tsMs, this.type, this.detail);
}

/// Owns one BluetoothDevice — the AbdomenMonitor.
///
/// Symmetric API with [BleVestService]. Two control paths (manual vs
/// auto), three subscriptions on connect (sensor data + events + mode
/// R/W).
class BleAbdomenService extends ChangeNotifier {
  BleStatus _status = BleStatus.idle;
  BleStatus get status => _status;

  AbdomenFrame? _latestFrame;
  AbdomenFrame? get latestFrame => _latestFrame;

  int? _mode;
  int? get mode => _mode;

  BluetoothDevice? _device;
  BluetoothDevice? get device => _device;

  final ValueNotifier<List<ScanResult>> scanResults =
      ValueNotifier<List<ScanResult>>(const []);

  StreamSubscription<List<ScanResult>>? _scanSub;
  StreamSubscription<BluetoothConnectionState>? _connSub;
  StreamSubscription<List<int>>? _sensorSub;
  StreamSubscription<List<int>>? _eventSub;
  BluetoothCharacteristic? _modeChar;

  final _frameCtrl = StreamController<AbdomenFrame>.broadcast();
  Stream<AbdomenFrame> get frameStream => _frameCtrl.stream;

  final _eventCtrl = StreamController<AbdomenEvent>.broadcast();
  Stream<AbdomenEvent> get eventStream => _eventCtrl.stream;

  bool _autoReconnect = false;
  int _retryIdx = 0;

  // ── Manual API ──────────────────────────────────────────────────────

  Future<void> startScan({
    Duration timeout = const Duration(seconds: 10),
  }) async {
    if (_status == BleStatus.scanning) return;
    _setStatus(BleStatus.scanning);
    scanResults.value = const [];
    try {
      await FlutterBluePlus.stopScan();
      await FlutterBluePlus.startScan(
        timeout: timeout,
        withNames: [AbdomenBle.deviceName],
      );
      _scanSub = FlutterBluePlus.scanResults.listen((results) {
        final hits = results
            .where((r) => r.device.platformName == AbdomenBle.deviceName)
            .toList();
        if (!_listEquals(hits, scanResults.value)) {
          scanResults.value = hits;
        }
      });
      FlutterBluePlus.isScanning
          .where((scanning) => scanning == false)
          .first
          .then((_) {
        _scanSub?.cancel();
        _scanSub = null;
        if (_status == BleStatus.scanning) {
          _setStatus(scanResults.value.isEmpty
              ? BleStatus.disconnected
              : BleStatus.idle);
        }
      });
    } catch (e) {
      debugPrint('[BleAbdomen] startScan error: $e');
      _setStatus(BleStatus.error);
    }
  }

  Future<void> stopScan() async {
    try {
      await FlutterBluePlus.stopScan();
    } catch (_) {/* harmless */}
    await _scanSub?.cancel();
    _scanSub = null;
    if (_status == BleStatus.scanning) {
      _setStatus(_device != null ? BleStatus.connected : BleStatus.idle);
    }
  }

  Future<bool> connectTo(BluetoothDevice dev) async {
    await stopScan();
    return _doConnect(dev);
  }

  Future<void> disconnect() async {
    _autoReconnect = false;
    await _cancelConnSubs();
    try {
      await _device?.disconnect();
    } catch (_) {/* best-effort */}
    _device = null;
    _modeChar = null;
    _setStatus(BleStatus.disconnected);
  }

  /// Switch the device between fetal (0) and abdominal (1) mode.
  Future<bool> setMode(int newMode) async {
    if (_modeChar == null || newMode < 0 || newMode > 1) return false;
    try {
      await _modeChar!.write([newMode]);
      _mode = newMode;
      notifyListeners();
      return true;
    } catch (e) {
      debugPrint('[BleAbdomen] mode write failed: $e');
      return false;
    }
  }

  // ── Auto API ────────────────────────────────────────────────────────

  Future<void> start() async {
    if (_autoReconnect) return;
    _autoReconnect = true;
    _retryIdx = 0;
    await _autoCycle();
  }

  Future<void> stop() => disconnect();

  Future<void> _autoCycle() async {
    if (!_autoReconnect) return;
    await startScan();
    await FlutterBluePlus.isScanning
        .where((s) => s == false)
        .first
        .timeout(BleTuning.scanTimeout + const Duration(seconds: 2),
            onTimeout: () => false);
    if (!_autoReconnect) return;
    if (scanResults.value.isEmpty) {
      _scheduleAutoRetry();
      return;
    }
    final ok = await _doConnect(scanResults.value.first.device);
    if (!ok) _scheduleAutoRetry();
  }

  void _scheduleAutoRetry() {
    if (!_autoReconnect) return;
    final delay = BleTuning.reconnectBackoff[
        _retryIdx.clamp(0, BleTuning.reconnectBackoff.length - 1)];
    _retryIdx++;
    Timer(delay, () {
      if (_autoReconnect) _autoCycle();
    });
  }

  // ── Internal connect path ───────────────────────────────────────────

  Future<bool> _doConnect(BluetoothDevice dev) async {
    _device = dev;
    _setStatus(BleStatus.connecting);
    try {
      await dev.connect(
        timeout: const Duration(seconds: 15),
        autoConnect: false,
      );
      try {
        await dev.requestMtu(BleTuning.desiredMtu);
      } catch (_) {/* non-fatal on Android */}

      _connSub = dev.connectionState.listen((state) {
        if (state == BluetoothConnectionState.disconnected) {
          _cancelConnSubs();
          _setStatus(BleStatus.disconnected);
          if (_autoReconnect) _scheduleAutoRetry();
        }
      });

      final services = await dev.discoverServices();
      BluetoothService? service;
      for (final s in services) {
        if (s.uuid.str.toLowerCase() == AbdomenBle.serviceUuid.toLowerCase()) {
          service = s;
          break;
        }
      }
      if (service == null) {
        debugPrint('[BleAbdomen] expected service not found');
        await dev.disconnect();
        _setStatus(BleStatus.error);
        return false;
      }

      BluetoothCharacteristic? sensor, events, modeC;
      for (final c in service.characteristics) {
        final id = c.uuid.str.toLowerCase();
        if (id == AbdomenBle.sensorCharUuid.toLowerCase()) sensor = c;
        if (id == AbdomenBle.eventsCharUuid.toLowerCase()) events = c;
        if (id == AbdomenBle.modeCharUuid.toLowerCase()) modeC = c;
      }
      if (sensor == null) {
        debugPrint('[BleAbdomen] sensor characteristic missing');
        _setStatus(BleStatus.error);
        return false;
      }

      await sensor.setNotifyValue(true);
      _sensorSub = sensor.lastValueStream.listen(_onSensor);

      if (events != null) {
        try {
          await events.setNotifyValue(true);
          _eventSub = events.lastValueStream.listen(_onEvent);
        } catch (e) {
          debugPrint('[BleAbdomen] event subscribe failed: $e');
        }
      }

      _modeChar = modeC;
      if (_modeChar != null) {
        try {
          final raw = await _modeChar!.read();
          if (raw.isNotEmpty) _mode = raw.first;
        } catch (_) {/* harmless */}
      }

      _retryIdx = 0;
      _setStatus(BleStatus.connected);
      return true;
    } catch (e) {
      debugPrint('[BleAbdomen] connect error: $e');
      _setStatus(BleStatus.error);
      return false;
    }
  }

  // ── Notification handlers ───────────────────────────────────────────

  void _onSensor(List<int> bytes) {
    if (bytes.isEmpty) return;
    try {
      final payload = utf8.decode(bytes, allowMalformed: true);
      final f = BlePayloadParser.parseAbdomen(payload);
      _latestFrame = f;
      _frameCtrl.add(f);
      notifyListeners();
    } catch (e) {
      debugPrint('[BleAbdomen] sensor parse error: $e');
    }
  }

  void _onEvent(List<int> bytes) {
    if (bytes.isEmpty) return;
    try {
      final s = utf8.decode(bytes, allowMalformed: true).trim();
      int ts = 0;
      String type = '';
      String? detail;
      for (final p in s.split(',')) {
        final ix = p.indexOf(':');
        if (ix < 0) continue;
        final k = p.substring(0, ix);
        final v = p.substring(ix + 1);
        if (k == 'ts') {
          ts = int.tryParse(v) ?? 0;
        } else if (k == 'type') {
          type = v;
        } else if (k == 'detail') {
          detail = v;
        }
      }
      _eventCtrl.add(AbdomenEvent(ts, type, detail));
    } catch (e) {
      debugPrint('[BleAbdomen] event parse error: $e');
    }
  }

  Future<void> _cancelConnSubs() async {
    await _sensorSub?.cancel();
    _sensorSub = null;
    await _eventSub?.cancel();
    _eventSub = null;
    await _connSub?.cancel();
    _connSub = null;
  }

  void _setStatus(BleStatus s) {
    if (_status == s) return;
    _status = s;
    notifyListeners();
  }

  static bool _listEquals<T>(List<T> a, List<T> b) {
    if (a.length != b.length) return false;
    for (var i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }

  @override
  void dispose() {
    _autoReconnect = false;
    _cancelConnSubs();
    _scanSub?.cancel();
    _frameCtrl.close();
    _eventCtrl.close();
    scanResults.dispose();
    super.dispose();
  }
}
