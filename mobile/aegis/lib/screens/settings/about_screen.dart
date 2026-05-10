import 'package:flutter/material.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:provider/provider.dart';

import '../../ble/ble_connection_supervisor.dart';

/// About screen — app version, vest firmware version, open-source
/// licenses. Pure read-only info, no buttons that don't do real things.
class AboutScreen extends StatefulWidget {
  const AboutScreen({super.key});

  @override
  State<AboutScreen> createState() => _AboutScreenState();
}

class _AboutScreenState extends State<AboutScreen> {
  PackageInfo? _info;

  @override
  void initState() {
    super.initState();
    PackageInfo.fromPlatform().then((info) {
      if (mounted) setState(() => _info = info);
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final supervisor = context.watch<BleConnectionSupervisor>();
    final fw = supervisor.vest.firmwareVersion;

    return ListView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      children: [
        const SizedBox(height: 16),
        Center(
          child: Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Icon(
              Icons.health_and_safety_rounded,
              color: theme.colorScheme.onPrimaryContainer,
              size: 44,
            ),
          ),
        ),
        const SizedBox(height: 16),
        Center(
          child: Text(
            'MedVerse',
            style: theme.textTheme.titleLarge,
          ),
        ),
        Center(
          child: Text(
            _info == null
                ? 'Loading…'
                : 'Version ${_info!.version} (build ${_info!.buildNumber})',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        const SizedBox(height: 24),
        const Divider(height: 1),
        ListTile(
          leading: const Icon(Icons.memory_outlined),
          title: const Text('Connected vest firmware'),
          subtitle: Text(fw == null ? 'No vest connected' : 'v$fw'),
        ),
        const Divider(height: 1),
        ListTile(
          leading: const Icon(Icons.policy_outlined),
          title: const Text('Open-source licenses'),
          subtitle: const Text('Flutter, Material 3, package licenses'),
          trailing: const Icon(Icons.chevron_right_rounded),
          onTap: () => showLicensePage(
            context: context,
            applicationName: 'MedVerse',
            applicationVersion: _info?.version ?? '',
            applicationIcon: Icon(
              Icons.health_and_safety_rounded,
              color: theme.colorScheme.primary,
              size: 32,
            ),
          ),
        ),
        const Divider(height: 1),
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 24),
          child: Text(
            'MedVerse — direct-BLE clinical telemetry + agentic AI '
            'specialty consultation. Mobile build owns the BLE radio; '
            'the FastAPI backend serves AI / FHIR / persistence.',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ],
    );
  }
}
