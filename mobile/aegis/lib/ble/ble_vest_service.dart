import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

import 'ble_constants.dart';
import 'ble_payload_parser.dart';

enum BleStatus { idle, scanning, connecting, connected, disconnected, error }

/// Owns one BluetoothDevice — the Aegis vest.
///
/// Two control paths:
///
///   1. **Manual** (default for the mobile UI):
///        startScan()/stopScan() find candidate devices and surface them
///        on [scanResultsStream]; the user picks one and calls
///        connectTo(device). disconnect() severs the link cleanly.
///
///   2. **Auto** (kept for headless tests / smoke runs):
///        start() = startScan + auto-connect to the first match + retry
///        on disconnect. stop() = full teardown.
///
/// Once connected, vitals (~1 Hz) and ECG burst (~30 Hz) characteristics
/// are subscribed and emit typed events on [vitalsStream] and
/// [ecgBurstStream]. Parsing is delegated to [BlePayloadParser].
class BleVestService extends ChangeNotifier {
  BleStatus _status = BleStatus.idle;
  BleStatus get status => _status;

  String? _firmwareVersion;
  String? get firmwareVersion => _firmwareVersion;

  VestVitals? _latestVitals;
  VestVitals? get latestVitals => _latestVitals;

  EcgBurst? _latestBurst;
  EcgBurst? get latestBurst => _latestBurst;

  /// The currently-connected device, if any.
  BluetoothDevice? _device;
  BluetoothDevice? get device => _device;

  /// Latest list of devices discovered by an active scan, filtered to
  /// the vest's advertised name. Empty when no scan is in progress.
  final ValueNotifier<List<ScanResult>> scanResults =
      ValueNotifier<List<ScanResult>>(const []);

  StreamSubscription<List<ScanResult>>? _scanSub;
  StreamSubscription<BluetoothConnectionState>? _connSub;
  StreamSubscription<List<int>>? _vitalsSub;
  StreamSubscription<List<int>>? _burstSub;

  final _vitalsCtrl = StreamController<VestVitals>.broadcast();
  Stream<VestVitals> get vitalsStream => _vitalsCtrl.stream;

  final _burstCtrl = StreamController<EcgBurst>.broadcast();
  Stream<EcgBurst> get ecgBurstStream => _burstCtrl.stream;

  // Auto-mode state.
  bool _autoReconnect = false;
  int _retryIdx = 0;

  // ── Manual API ──────────────────────────────────────────────────────

  /// Begin a one-shot scan. Found devices stream into [scanResults]; the
  /// caller decides when to stop and whom to connect to.
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
        withNames: [VestBle.deviceName],
      );
      _scanSub = FlutterBluePlus.scanResults.listen((results) {
        // Filter just in case the platform ignores `withNames` on older
        // Android stacks.
        final hits = results
            .where((r) => r.device.platformName == VestBle.deviceName)
            .toList();
        if (!_listEquals(hits, scanResults.value)) {
          scanResults.value = hits;
        }
      });
      // Auto-flip status back to idle when the timer elapses.
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
      debugPrint('[BleVest] startScan error: $e');
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

  /// Connect to a specific device — typically picked from
  /// [scanResults] by the user. Sets up vitals + ECG burst subscriptions
  /// on success.
  Future<bool> connectTo(BluetoothDevice dev) async {
    await stopScan();
    return _doConnect(dev);
  }

  /// Sever the active connection. Doesn't retry.
  Future<void> disconnect() async {
    _autoReconnect = false;
    await _cancelConnSubs();
    try {
      await _device?.disconnect();
    } catch (_) {/* best-effort */}
    _device = null;
    _setStatus(BleStatus.disconnected);
  }

  // ── Auto API (smoke tests / headless runs) ──────────────────────────

  /// Auto-scan, auto-connect to the first match, retry on disconnect.
  Future<void> start() async {
    if (_autoReconnect) return;
    _autoReconnect = true;
    _retryIdx = 0;
    await _autoCycle();
  }

  /// Stop auto-mode and disconnect.
  Future<void> stop() => disconnect();

  Future<void> _autoCycle() async {
    if (!_autoReconnect) return;
    await startScan();
    // Wait for the scan to finish.
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

  // ── Internal connect path (shared by manual + auto) ─────────────────

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
      } catch (_) {
        // Some Android stacks reject above-default MTU — vest still streams.
      }

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
        if (s.uuid.str.toLowerCase() == VestBle.serviceUuid.toLowerCase()) {
          service = s;
          break;
        }
      }
      if (service == null) {
        debugPrint('[BleVest] expected service not found on device');
        await dev.disconnect();
        _setStatus(BleStatus.error);
        return false;
      }

      BluetoothCharacteristic? vitals, burst;
      for (final c in service.characteristics) {
        final id = c.uuid.str.toLowerCase();
        if (id == VestBle.vitalsCharUuid.toLowerCase()) vitals = c;
        if (id == VestBle.ecgBurstCharUuid.toLowerCase()) burst = c;
      }
      if (vitals == null) {
        debugPrint('[BleVest] vitals characteristic missing');
        _setStatus(BleStatus.error);
        return false;
      }

      await vitals.setNotifyValue(true);
      _vitalsSub = vitals.lastValueStream.listen(_onVitals);

      if (burst != null) {
        try {
          await burst.setNotifyValue(true);
          _burstSub = burst.lastValueStream.listen(_onBurst);
        } catch (e) {
          debugPrint('[BleVest] burst subscribe failed (legacy fw?): $e');
        }
      }

      _retryIdx = 0;
      _setStatus(BleStatus.connected);
      return true;
    } catch (e) {
      debugPrint('[BleVest] connect error: $e');
      _setStatus(BleStatus.error);
      return false;
    }
  }

  // ── Notification handlers ───────────────────────────────────────────

  // Debug log throttle — print one parsed vitals frame per second so we
  // can verify on-device what the vest is actually sending.
  DateTime _lastDebugLog = DateTime.fromMillisecondsSinceEpoch(0);

  void _onVitals(List<int> bytes) {
    if (bytes.isEmpty) return;
    try {
      final payload = utf8.decode(bytes, allowMalformed: true);
      final v = BlePayloadParser.parseVestVitals(payload);
      _latestVitals = v;
      if (v.firmwareVersion != null && v.firmwareVersion != _firmwareVersion) {
        _firmwareVersion = v.firmwareVersion;
        debugPrint('[BleVest] firmware version: $_firmwareVersion');
      }
      // Throttled per-second dump of every key field so users can spot
      // sensor-side problems (TC=0 → cervical probe not contacting,
      // EHR=0 → ECG warming up, etc.) without DevTools.
      final now = DateTime.now();
      if (now.difference(_lastDebugLog).inMilliseconds >= 1000) {
        _lastDebugLog = now;
        debugPrint('[BleVest] '
            'HR(EHR)=${v.ecgHr.toStringAsFixed(1)}  '
            'temps[L/R/C]=${v.tl.toStringAsFixed(1)}/${v.tr.toStringAsFixed(1)}/${v.tc.toStringAsFixed(1)}°C  '
            'PPG IR1=${v.ir1.toStringAsFixed(0)} IR2=${v.ir2.toStringAsFixed(0)} IRA=${v.ira.toStringAsFixed(0)}  '
            'env=${v.bmp280Pressure.toStringAsFixed(0)}hPa/${v.bmp280Temp.toStringAsFixed(1)}°C/${v.dht11Humidity.toStringAsFixed(0)}%  '
            'audio[A/D]=${v.analogRms.toStringAsFixed(0)}/${v.digitalRms.toStringAsFixed(0)}  '
            'IMU pitch[U/L]=${v.upperPitch.toStringAsFixed(1)}/${v.lowerPitch.toStringAsFixed(1)}  '
            '${v.edgeAlert ? "AL=1(${v.edgeAlertReason})" : ""}');
      }
      _vitalsCtrl.add(v);
      notifyListeners();
    } catch (e) {
      debugPrint('[BleVest] vitals parse error: $e');
    }
  }

  void _onBurst(List<int> bytes) {
    if (bytes.isEmpty) return;
    try {
      final payload = utf8.decode(bytes, allowMalformed: true);
      final b = BlePayloadParser.parseEcgBurst(payload);
      _latestBurst = b;
      _burstCtrl.add(b);
    } catch (e) {
      debugPrint('[BleVest] burst parse error: $e');
    }
  }

  Future<void> _cancelConnSubs() async {
    await _vitalsSub?.cancel();
    _vitalsSub = null;
    await _burstSub?.cancel();
    _burstSub = null;
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
    _vitalsCtrl.close();
    _burstCtrl.close();
    scanResults.dispose();
    super.dispose();
  }
}
