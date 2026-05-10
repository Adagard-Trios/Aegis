import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';

import '../ble/ble_connection_supervisor.dart';
import '../ble/ble_vest_service.dart';
import '../services/api_config.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../services/vest_stream_service.dart';

/// Material 3 NavigationDrawer — quick-action sidebar.
///
/// Holds operations that don't deserve a top-level tab but should be
/// one-tap reachable: pair vest, view recent alerts, generate FHIR
/// export, fire the multi-agent collaborative diagnosis. Every item
/// hits a real backend (or a real local action) — no placeholders.
///
/// Header: a compact patient-id + connection-status pill so the user
/// always sees who they're operating on without opening Settings.
class AegisAppDrawer extends StatelessWidget {
  const AegisAppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return NavigationDrawer(
      backgroundColor: cs.surfaceContainerLow,
      surfaceTintColor: cs.surfaceTint,
      children: [
        const _DrawerHeader(),
        const SizedBox(height: 8),

        // ── Connectivity ───────────────────────────────────────────
        _SectionLabel(label: 'Sensors', cs: cs),
        const _PairVestTile(),
        const _SensorHealthTile(),

        const Divider(),

        // ── Clinical actions ───────────────────────────────────────
        _SectionLabel(label: 'Clinical', cs: cs),
        const _ComplexDiagnosisTile(),
        const _RecentAlertsTile(),
        const _FhirExportTile(),
      ],
      // Drawer no longer holds any NavigationDrawerDestinations — the
      // tiles above (sensor health / clinical actions) are plain
      // ListTiles, which means M3's "selected pill" highlight never
      // gets stuck on the first destination by default. The bottom-nav
      // owns primary navigation; the drawer is purely a quick-action
      // tray.
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String label;
  final ColorScheme cs;
  const _SectionLabel({required this.label, required this.cs});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(28, 16, 16, 8),
      child: Text(
        label.toUpperCase(),
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: cs.primary,
              letterSpacing: 1.4,
              fontWeight: FontWeight.w800,
            ),
      ),
    );
  }
}

// ── Header ───────────────────────────────────────────────────────────

class _DrawerHeader extends StatefulWidget {
  const _DrawerHeader();
  @override
  State<_DrawerHeader> createState() => _DrawerHeaderState();
}

class _DrawerHeaderState extends State<_DrawerHeader> {
  static const _patientIdKey = 'aegis.patient_id';
  static const _displayNameKey = 'aegis.display_name';
  String _patientId = 'medverse-demo-patient';
  String _displayName = '';

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    const storage = FlutterSecureStorage();
    try {
      final pid = await storage.read(key: _patientIdKey);
      final name = await storage.read(key: _displayNameKey);
      if (mounted) {
        setState(() {
          _patientId = pid ?? 'medverse-demo-patient';
          _displayName = name ?? '';
        });
      }
    } catch (_) {/* non-fatal */}
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final supervisor = context.watch<BleConnectionSupervisor>();
    final vestOk = supervisor.vest.status == BleStatus.connected;
    final abdOk = supervisor.abdomen.status == BleStatus.connected;

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            cs.primary.withValues(alpha: 0.18),
            cs.tertiary.withValues(alpha: 0.10),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: cs.primary.withValues(alpha: 0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: cs.primary.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: cs.primary.withValues(alpha: 0.4)),
                ),
                child: Icon(Icons.person_rounded, color: cs.primary, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _displayName.isEmpty ? 'Patient' : _displayName,
                      style: Theme.of(context).textTheme.titleMedium,
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      _patientId,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: cs.onSurfaceVariant,
                          ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              _StatusDot(active: vestOk, label: 'Vest'),
              const SizedBox(width: 12),
              _StatusDot(active: abdOk, label: 'Abdomen'),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatusDot extends StatelessWidget {
  final bool active;
  final String label;
  const _StatusDot({required this.active, required this.label});
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final color = active ? const Color(0xFF10B981) : cs.onSurfaceVariant;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
            boxShadow: active
                ? [
                    BoxShadow(
                      color: color.withValues(alpha: 0.6),
                      blurRadius: 6,
                      spreadRadius: 1,
                    )
                  ]
                : null,
          ),
        ),
        const SizedBox(width: 6),
        Text(
          label,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: cs.onSurface,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
              ),
        ),
      ],
    );
  }
}

// ── Sensor health tile (plain ListTile — no M3 selection state) ─────

class _SensorHealthTile extends StatelessWidget {
  const _SensorHealthTile();
  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(
        Icons.troubleshoot_rounded,
        color: Theme.of(context).colorScheme.primary,
      ),
      title: const Text('Sensor health'),
      subtitle: const Text('Per-probe diagnostic'),
      trailing: const Icon(Icons.chevron_right_rounded),
      onTap: () {
        Navigator.pop(context);
        context.go('/settings/sensors');
      },
    );
  }
}

// ── Pair vest tile ───────────────────────────────────────────────────

class _PairVestTile extends StatelessWidget {
  const _PairVestTile();
  @override
  Widget build(BuildContext context) {
    final supervisor = context.watch<BleConnectionSupervisor>();
    final connected = supervisor.vest.status == BleStatus.connected;
    return ListTile(
      leading: Icon(
        connected ? Icons.bluetooth_connected_rounded : Icons.bluetooth_searching_rounded,
        color: Theme.of(context).colorScheme.primary,
      ),
      title: Text(connected ? 'Vest connected' : 'Quick pair vest'),
      subtitle: Text(
        connected
            ? 'Tap to open Sensors'
            : 'Scan + connect right now',
      ),
      onTap: () {
        Navigator.pop(context);
        if (!connected) {
          // Fire the scan immediately. The user can finish the pair
          // from the Sensors screen which has the full device list.
          supervisor.vest.startScan();
        }
        context.go('/settings/sensors');
      },
    );
  }
}

// ── Complex-diagnosis tile (slow but real) ───────────────────────────

class _ComplexDiagnosisTile extends StatefulWidget {
  const _ComplexDiagnosisTile();
  @override
  State<_ComplexDiagnosisTile> createState() => _ComplexDiagnosisTileState();
}

class _ComplexDiagnosisTileState extends State<_ComplexDiagnosisTile> {
  bool _running = false;

  Future<void> _run() async {
    setState(() => _running = true);
    final stream = context.read<VestStreamService>();
    final auth = context.read<AuthService>();
    try {
      final result = await ApiService.complexDiagnosis(
        snapshot: stream.latestSnapshot,
        auth: auth,
      );
      if (!mounted) return;
      _showResult(result);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Diagnosis failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _running = false);
    }
  }

  void _showResult(Map<String, dynamic>? result) {
    final candidates =
        (result?['final_ranking'] ?? result?['candidates'] ?? []) as List;
    final summary = result?['summary_for_clinician']?.toString() ??
        result?['summary']?.toString() ??
        '(no summary)';
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Theme.of(context).colorScheme.surfaceContainer,
      isScrollControlled: true,
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        builder: (context, scroll) => ListView(
          controller: scroll,
          padding: const EdgeInsets.all(20),
          children: [
            Text('Multi-agent diagnosis',
                style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 12),
            Text(summary, style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 16),
            if (candidates.isNotEmpty) ...[
              Text('Ranked candidates',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              for (final c in candidates.take(5))
                ListTile(
                  dense: true,
                  leading: const Icon(Icons.fiber_manual_record, size: 12),
                  title: Text((c['name'] ?? '?').toString()),
                  subtitle: Text((c['rationale'] ?? '').toString()),
                ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(
        Icons.hub_rounded,
        color: Theme.of(context).colorScheme.tertiary,
      ),
      title: const Text('Run multi-agent diagnosis'),
      subtitle: Text(_running
          ? 'Proposer → Skeptic → Diagnosis…'
          : 'Collaborative graph (~10 s)'),
      trailing: _running
          ? const SizedBox(
              width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
          : const Icon(Icons.chevron_right_rounded),
      onTap: _running ? null : _run,
    );
  }
}

// ── Recent alerts tile ───────────────────────────────────────────────

class _RecentAlertsTile extends StatelessWidget {
  const _RecentAlertsTile();

  Future<void> _open(BuildContext context) async {
    Navigator.pop(context);
    final auth = context.read<AuthService>();
    try {
      final res = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/api/alerts?limit=20'),
        headers: auth.authHeaders(),
      );
      if (!context.mounted) return;
      if (res.statusCode != 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Alerts unreachable: ${res.statusCode}')),
        );
        return;
      }
      final data = jsonDecode(res.body);
      final alerts = (data is List ? data : (data['alerts'] ?? [])) as List;
      if (!context.mounted) return;
      _showAlerts(context, alerts);
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Alerts failed: $e')),
      );
    }
  }

  void _showAlerts(BuildContext context, List alerts) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surfaceContainer,
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.5,
        builder: (context, scroll) {
          if (alerts.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.check_circle_outline,
                        size: 48,
                        color: Theme.of(context).colorScheme.onSurfaceVariant),
                    const SizedBox(height: 12),
                    Text('No alerts',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text('All clinical thresholds nominal.',
                        style: Theme.of(context).textTheme.bodySmall),
                  ],
                ),
              ),
            );
          }
          return ListView.separated(
            controller: scroll,
            padding: const EdgeInsets.all(16),
            itemCount: alerts.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, i) {
              final a = alerts[i] as Map;
              final sev = (a['severity'] ?? 5) as num;
              final color = sev >= 7
                  ? Theme.of(context).colorScheme.error
                  : sev >= 4
                      ? Theme.of(context).colorScheme.tertiary
                      : Theme.of(context).colorScheme.primary;
              return ListTile(
                leading: Icon(Icons.warning_amber_rounded, color: color),
                title: Text((a['message'] ?? a['source'] ?? 'Alert').toString()),
                subtitle: Text(
                  '${a['source'] ?? '?'} · severity $sev · '
                  '${a['ts']?.toString() ?? ''}',
                ),
              );
            },
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(
        Icons.notifications_outlined,
        color: Theme.of(context).colorScheme.error,
      ),
      title: const Text('Recent alerts'),
      subtitle: const Text('Last 20 from /api/alerts'),
      trailing: const Icon(Icons.chevron_right_rounded),
      onTap: () => _open(context),
    );
  }
}

// ── FHIR export tile ─────────────────────────────────────────────────

class _FhirExportTile extends StatelessWidget {
  const _FhirExportTile();

  Future<void> _export(BuildContext context) async {
    final auth = context.read<AuthService>();
    try {
      final res = await http.get(
        Uri.parse('${ApiConfig.baseUrl}/api/fhir/Bundle/latest'),
        headers: auth.authHeaders(),
      );
      if (!context.mounted) return;
      Navigator.pop(context); // close drawer
      if (res.statusCode != 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('FHIR export failed: ${res.statusCode}')),
        );
        return;
      }
      final body = res.body;
      if (!context.mounted) return;
      _showJson(context, body);
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('FHIR export failed: $e')),
      );
    }
  }

  void _showJson(BuildContext context, String json) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Theme.of(context).colorScheme.surfaceContainer,
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.7,
        builder: (context, scroll) => Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text('FHIR R4 Bundle',
                        style: Theme.of(context).textTheme.headlineSmall),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Expanded(
                child: SingleChildScrollView(
                  controller: scroll,
                  child: SelectableText(
                    json,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 11,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(
        Icons.outbox_outlined,
        color: Theme.of(context).colorScheme.primary,
      ),
      title: const Text('Export FHIR Bundle'),
      subtitle: const Text('Latest /api/fhir/Bundle/latest'),
      trailing: const Icon(Icons.chevron_right_rounded),
      onTap: () => _export(context),
    );
  }
}
