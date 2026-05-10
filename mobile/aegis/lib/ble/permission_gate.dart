import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:permission_handler/permission_handler.dart';

/// First-run BLE permission gate.
///
/// Shows a one-time modal explaining that Aegis needs Bluetooth to read
/// sensor data, then requests the platform-appropriate permissions:
///   • Android 12+ : BLUETOOTH_SCAN + BLUETOOTH_CONNECT
///   • Android ≤11 : ACCESS_FINE_LOCATION (BLE scanning was location-derived)
///   • iOS         : Core Bluetooth Always usage description (handled by
///                   the OS prompt at first scan; we surface the rationale
///                   modal first so users understand why it's appearing)
///
/// On approval the gate persists `aegis.ble_consent_v1=true` in
/// [FlutterSecureStorage] and never re-prompts. On permanent denial it
/// renders an "Open Settings" path so the user can recover from the
/// "permanently denied" trap (Android system-settings deep link).
///
/// Mount this widget *above* MainLayout in main.dart so it runs once,
/// before any BLE service tries to scan and silently no-ops.
class PermissionGate extends StatefulWidget {
  final Widget child;

  /// Skip the gate entirely on platforms that don't have BLE
  /// (web / desktop in this build). Defaults to `kIsWeb`.
  final bool skip;

  const PermissionGate({super.key, required this.child, bool? skip})
      : skip = skip ?? kIsWeb;

  @override
  State<PermissionGate> createState() => _PermissionGateState();
}

class _PermissionGateState extends State<PermissionGate> {
  static const _consentKey = 'aegis.ble_consent_v1';
  final _storage = const FlutterSecureStorage();

  /// null  → still loading the prior decision
  /// true  → we have permission OR the user previously consented
  /// false → permanently denied; show recovery UI
  bool? _granted;

  @override
  void initState() {
    super.initState();
    if (widget.skip) {
      _granted = true;
    } else {
      _bootstrap();
    }
  }

  Future<void> _bootstrap() async {
    try {
      final stored = await _storage.read(key: _consentKey);
      if (stored == 'true' && await _alreadyHasPermission()) {
        if (mounted) setState(() => _granted = true);
        return;
      }
    } catch (_) {
      // Secure storage failure is non-fatal — fall through to request
    }
    if (mounted) setState(() => _granted = false);
  }

  Future<bool> _alreadyHasPermission() async {
    if (!_isMobile) return true;
    if (Platform.isAndroid) {
      final scan = await Permission.bluetoothScan.status;
      final connect = await Permission.bluetoothConnect.status;
      return scan.isGranted && connect.isGranted;
    }
    if (Platform.isIOS) {
      // iOS doesn't expose a pre-prompt status accurately for Bluetooth;
      // assume not granted on first run so we surface the rationale
      // modal at least once.
      return false;
    }
    return true;
  }

  bool get _isMobile {
    if (kIsWeb) return false;
    try {
      return Platform.isAndroid || Platform.isIOS;
    } catch (_) {
      return false;
    }
  }

  Future<void> _request() async {
    // The set of permissions that MUST be granted to proceed. We request
    // location too on legacy Android (≤ 11) because BLE scan results were
    // location-derived back then — but we don't gate on it because on
    // Android 12+ the manifest's `neverForLocation` flag means we never
    // actually need location, even though the system might still surface
    // the prompt for some OEM-skinned ROMs.
    final required = <Permission>{};
    final optional = <Permission>{};

    if (Platform.isAndroid) {
      required.addAll([Permission.bluetoothScan, Permission.bluetoothConnect]);
      optional.add(Permission.locationWhenInUse);
    } else if (Platform.isIOS) {
      required.add(Permission.bluetooth);
    } else {
      // Desktop / web — nothing to request, fall straight through.
      if (mounted) setState(() => _granted = true);
      return;
    }

    // Request the union and inspect each set independently.
    final all = {...required, ...optional}.toList();
    final results = await all.request();

    final requiredOk = required.every(
      (p) => (results[p]?.isGranted ?? false) || (results[p]?.isLimited ?? false),
    );

    if (requiredOk) {
      try {
        await _storage.write(key: _consentKey, value: 'true');
      } catch (_) {/* non-fatal */}
      if (mounted) setState(() => _granted = true);
    } else {
      // Stay on the gate — the "Open Settings" path lets the user fix
      // a permanently-denied state.
      if (mounted) setState(() => _granted = false);
    }
  }

  Future<void> _openSettings() async {
    await openAppSettings();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.skip || _granted == true) return widget.child;
    if (_granted == null) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.bluetooth_searching, size: 56),
              const SizedBox(height: 16),
              Text(
                'MedVerse needs Bluetooth',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 12),
              const Text(
                'MedVerse connects directly to your vest and abdomen monitor '
                'over Bluetooth Low Energy to read live vital signs. '
                'Telemetry stays on your device — only AI diagnosis '
                'requests reach the server.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _request,
                icon: const Icon(Icons.check),
                label: const Text('Allow Bluetooth'),
              ),
              const SizedBox(height: 8),
              TextButton.icon(
                onPressed: _openSettings,
                icon: const Icon(Icons.settings_outlined),
                label: const Text('Open system settings'),
              ),
              const SizedBox(height: 4),
              const Text(
                'If you previously denied permission, use settings to '
                're-enable Bluetooth for MedVerse.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
