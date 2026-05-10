import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Material 3 Settings hub.
///
/// Replaces the legacy 3-placeholder ListTile screen. Every tile here
/// pushes to a real sub-route — none of them are dead. Sensors used to
/// be its own bottom-nav tab; it now lives at `/settings/sensors`.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      children: [
        _SectionHeader(label: 'Account', theme: theme),
        _SettingsTile(
          icon: Icons.person_outline,
          title: 'Patient profile',
          subtitle: 'Identifier, name, notes',
          onTap: () => context.go('/settings/profile'),
        ),
        const Divider(height: 1),

        _SectionHeader(label: 'Devices', theme: theme),
        _SettingsTile(
          icon: Icons.bluetooth_searching_rounded,
          title: 'Sensors',
          subtitle: 'Scan, pair, sensor health',
          onTap: () => context.go('/settings/sensors'),
        ),
        const Divider(height: 1),

        _SectionHeader(label: 'Connection', theme: theme),
        _SettingsTile(
          icon: Icons.cloud_outlined,
          title: 'Backend URL',
          subtitle: 'Override the FastAPI endpoint',
          onTap: () => context.go('/settings/backend'),
        ),
        const Divider(height: 1),

        _SectionHeader(label: 'Preferences', theme: theme),
        _SettingsTile(
          icon: Icons.accessibility_new_outlined,
          title: 'Accessibility',
          subtitle: 'Reduced motion, high contrast, large taps',
          onTap: () => context.go('/settings/accessibility'),
        ),
        const Divider(height: 1),

        _SectionHeader(label: 'About', theme: theme),
        _SettingsTile(
          icon: Icons.info_outline,
          title: 'App version & licenses',
          subtitle: 'Build info, firmware, open-source licenses',
          onTap: () => context.go('/settings/about'),
        ),
      ],
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String label;
  final ThemeData theme;
  const _SectionHeader({required this.label, required this.theme});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 20, 24, 8),
      child: Text(
        label.toUpperCase(),
        style: theme.textTheme.labelSmall?.copyWith(
          color: theme.colorScheme.primary,
          fontWeight: FontWeight.w800,
          letterSpacing: 1.1,
        ),
      ),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _SettingsTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Semantics(
      button: true,
      label: '$title. $subtitle',
      child: ListTile(
        leading: Icon(icon, color: theme.colorScheme.primary),
        title: Text(title, style: theme.textTheme.titleMedium),
        subtitle: Text(subtitle, style: theme.textTheme.bodySmall),
        trailing: const Icon(Icons.chevron_right_rounded),
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 4),
      ),
    );
  }
}
