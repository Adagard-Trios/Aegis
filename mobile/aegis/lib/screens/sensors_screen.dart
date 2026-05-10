import 'package:flutter/foundation.dart' show ValueListenable;
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:provider/provider.dart';

import '../ble/ble_abdomen_service.dart';
import '../ble/ble_connection_supervisor.dart';
import '../ble/ble_vest_service.dart';
import '../theme.dart';
import '../widgets/sensor_health_panel.dart';

/// Manual sensor pairing screen.
///
/// Two cards (Vest + Fetal/Abdomen Monitor). Each card:
///   - Shows current connection status (Idle / Scanning / Found N /
///     Connecting / Connected / Disconnected / Error).
///   - "Search" button → calls service.startScan(); the discovered
///     devices stream into a list.
///   - Tapping a discovered device calls service.connectTo(device).
///   - "Disconnect" button when connected.
///
/// Backed by [BleVestService] + [BleAbdomenService] via the
/// [BleConnectionSupervisor] in the provider tree.
class SensorsScreen extends StatelessWidget {
  const SensorsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final supervisor = context.watch<BleConnectionSupervisor>();
    return Scaffold(
      backgroundColor: MedVerseTheme.background,
      appBar: AppBar(
        title: const Text('SENSORS', style: TextStyle(letterSpacing: 1.4)),
        backgroundColor: MedVerseTheme.surface,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _SensorCard(
            title: 'Aegis Vest',
            subtitle: 'PPG · ECG · Temp · IMU · Audio',
            icon: Icons.favorite_outline,
            accent: MedVerseTheme.hrColor,
            service: supervisor.vest,
          ),
          const SizedBox(height: 12),
          _AbdomenCard(
            title: 'Abdomen Monitor',
            subtitle: 'Fetal HR · Kicks · Contractions',
            icon: Icons.pregnant_woman,
            accent: MedVerseTheme.fhrColor,
            service: supervisor.abdomen,
          ),
          const SizedBox(height: 12),
          // Per-probe diagnostic. Stays mounted regardless of connection
          // state — when disconnected, each section shows a "pair to see
          // probe status" hint; when connected, every sensor row updates
          // live as new BLE notifications arrive.
          SensorHealthPanel(
            vest: supervisor.vest,
            abdomen: supervisor.abdomen,
          ),
        ],
      ),
    );
  }
}

// ── Vest card ─────────────────────────────────────────────────────────

class _SensorCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final BleVestService service;
  const _SensorCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.service,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: service,
      builder: (_, _) => _DeviceCardShell(
        title: title,
        subtitle: subtitle,
        icon: icon,
        accent: accent,
        status: service.status,
        deviceName: service.device?.platformName,
        firmwareVersion: service.firmwareVersion,
        scanResults: service.scanResults,
        onScan: () => service.startScan(),
        onStopScan: () => service.stopScan(),
        onConnect: (d) => service.connectTo(d),
        onDisconnect: () => service.disconnect(),
      ),
    );
  }
}

// ── Abdomen card ──────────────────────────────────────────────────────

class _AbdomenCard extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final BleAbdomenService service;
  const _AbdomenCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.service,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: service,
      builder: (_, _) => _DeviceCardShell(
        title: title,
        subtitle: subtitle,
        icon: icon,
        accent: accent,
        status: service.status,
        deviceName: service.device?.platformName,
        firmwareVersion: null,
        scanResults: service.scanResults,
        onScan: () => service.startScan(),
        onStopScan: () => service.stopScan(),
        onConnect: (d) => service.connectTo(d),
        onDisconnect: () => service.disconnect(),
        extraTrailing: service.status == BleStatus.connected
            ? _ModePicker(service: service)
            : null,
      ),
    );
  }
}

// ── Shared card shell ─────────────────────────────────────────────────

class _DeviceCardShell extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;
  final BleStatus status;
  final String? deviceName;
  final String? firmwareVersion;
  final ValueListenable<List<ScanResult>> scanResults;
  final VoidCallback onScan;
  final VoidCallback onStopScan;
  final Future<bool> Function(BluetoothDevice) onConnect;
  final Future<void> Function() onDisconnect;
  final Widget? extraTrailing;

  const _DeviceCardShell({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
    required this.status,
    required this.deviceName,
    required this.firmwareVersion,
    required this.scanResults,
    required this.onScan,
    required this.onStopScan,
    required this.onConnect,
    required this.onDisconnect,
    this.extraTrailing,
  });

  @override
  Widget build(BuildContext context) {
    final isConnected = status == BleStatus.connected;
    final isScanning = status == BleStatus.scanning;
    final isConnecting = status == BleStatus.connecting;

    return Container(
      decoration: BoxDecoration(
        color: MedVerseTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: MedVerseTheme.border, width: 1),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(icon, color: accent),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: const TextStyle(
                            color: MedVerseTheme.textMain,
                            fontWeight: FontWeight.w700,
                            fontSize: 15)),
                    Text(subtitle,
                        style: const TextStyle(
                            color: MedVerseTheme.textMuted, fontSize: 11)),
                  ],
                ),
              ),
              _StatusChip(status: status),
            ],
          ),
          if (isConnected && deviceName != null) ...[
            const SizedBox(height: 12),
            _Row('Device', deviceName!),
            if (firmwareVersion != null) _Row('Firmware', 'v$firmwareVersion'),
          ],
          if (extraTrailing != null) ...[
            const SizedBox(height: 12),
            extraTrailing!,
          ],
          const SizedBox(height: 12),
          if (isConnected)
            _PrimaryButton(
              label: 'Disconnect',
              icon: Icons.link_off,
              color: MedVerseTheme.statusCritical,
              onPressed: onDisconnect,
            )
          else if (isScanning)
            _PrimaryButton(
              label: 'Stop scan',
              icon: Icons.stop_circle_outlined,
              color: MedVerseTheme.statusWarning,
              onPressed: onStopScan,
            )
          else if (isConnecting)
            const _PrimaryButton(
              label: 'Connecting…',
              icon: Icons.bluetooth_connected,
              color: MedVerseTheme.primary,
              onPressed: null,
            )
          else
            _PrimaryButton(
              label: 'Search for device',
              icon: Icons.bluetooth_searching,
              color: accent,
              onPressed: onScan,
            ),
          if (!isConnected)
            ValueListenableBuilder<List<ScanResult>>(
              valueListenable: scanResults,
              builder: (_, results, _) {
                if (results.isEmpty) return const SizedBox.shrink();
                return Container(
                  margin: const EdgeInsets.only(top: 12),
                  decoration: BoxDecoration(
                    color: MedVerseTheme.background,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: MedVerseTheme.border, width: 1),
                  ),
                  child: Column(
                    children: [
                      for (final r in results)
                        InkWell(
                          onTap: () => onConnect(r.device),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 12, vertical: 10),
                            child: Row(
                              children: [
                                const Icon(Icons.bluetooth,
                                    size: 16,
                                    color: MedVerseTheme.textMuted),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        r.device.platformName.isEmpty
                                            ? '<unnamed>'
                                            : r.device.platformName,
                                        style: const TextStyle(
                                            color: MedVerseTheme.textMain,
                                            fontSize: 13,
                                            fontWeight: FontWeight.w600),
                                      ),
                                      Text(
                                        '${r.device.remoteId.str}  ·  ${r.rssi} dBm',
                                        style: const TextStyle(
                                            color:
                                                MedVerseTheme.textMuted,
                                            fontSize: 10),
                                      ),
                                    ],
                                  ),
                                ),
                                const Icon(Icons.chevron_right,
                                    size: 18,
                                    color: MedVerseTheme.textMuted),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}

// ── Tiny pieces ───────────────────────────────────────────────────────

class _StatusChip extends StatelessWidget {
  final BleStatus status;
  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    final (label, color) = switch (status) {
      BleStatus.connected => ('CONNECTED', MedVerseTheme.statusNormal),
      BleStatus.connecting => ('CONNECTING', MedVerseTheme.primary),
      BleStatus.scanning => ('SCANNING', MedVerseTheme.statusWarning),
      BleStatus.disconnected => ('DISCONNECTED', MedVerseTheme.textMuted),
      BleStatus.error => ('ERROR', MedVerseTheme.statusCritical),
      BleStatus.idle => ('IDLE', MedVerseTheme.textMuted),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(label,
          style: TextStyle(
              color: color, fontSize: 9, fontWeight: FontWeight.w800, letterSpacing: 0.8)),
    );
  }
}

class _Row extends StatelessWidget {
  final String k;
  final String v;
  const _Row(this.k, this.v);
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Row(
        children: [
          Text(k,
              style: const TextStyle(
                  color: MedVerseTheme.textMuted, fontSize: 11)),
          const Spacer(),
          Text(v,
              style: const TextStyle(
                  color: MedVerseTheme.textMain,
                  fontSize: 12,
                  fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}

class _PrimaryButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final VoidCallback? onPressed;
  const _PrimaryButton(
      {required this.label,
      required this.icon,
      required this.color,
      required this.onPressed});
  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: FilledButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, size: 16),
        label: Text(label),
        style: FilledButton.styleFrom(
          backgroundColor: color,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
      ),
    );
  }
}

class _ModePicker extends StatelessWidget {
  final BleAbdomenService service;
  const _ModePicker({required this.service});
  @override
  Widget build(BuildContext context) {
    final mode = service.mode ?? 0;
    return Row(
      children: [
        const Text('Mode',
            style: TextStyle(color: MedVerseTheme.textMuted, fontSize: 11)),
        const Spacer(),
        SegmentedButton<int>(
          segments: const [
            ButtonSegment(
                value: 0,
                label: Text('Fetal', style: TextStyle(fontSize: 12))),
            ButtonSegment(
                value: 1,
                label: Text('Abdominal', style: TextStyle(fontSize: 12))),
          ],
          selected: {mode},
          onSelectionChanged: (s) => service.setMode(s.first),
          style: const ButtonStyle(visualDensity: VisualDensity.compact),
        ),
      ],
    );
  }
}
