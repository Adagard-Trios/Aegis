import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../services/ai_assessment_repository.dart';
import '../../services/auth_service.dart';

/// Material 3 Settings hub.
///
/// Replaces the legacy 3-placeholder ListTile screen. Every tile here
/// pushes to a real sub-route — none of them are dead. Sensors used to
/// be its own bottom-nav tab; it now lives at `/settings/sensors`.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  Future<void> _confirmLogout(BuildContext context) async {
    final theme = Theme.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Sign out?'),
        content: const Text(
          'Your session token will be cleared. You can sign in again to '
          'reconnect to the backend.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: theme.colorScheme.error,
              foregroundColor: theme.colorScheme.onError,
            ),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Sign out'),
          ),
        ],
      ),
    );
    if (ok != true || !context.mounted) return;
    // Clear the AI assessment cache so cached text from the previous
    // session doesn't bleed into the next user's view.
    context.read<AiAssessmentRepository>().clear();
    await context.read<AuthService>().logout();
    // The router's redirect callback (driven by AuthService as
    // refreshListenable) will bounce to /login automatically.
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final auth = context.watch<AuthService>();
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
        if (auth.isAuthenticated)
          _SettingsTile(
            icon: Icons.logout_rounded,
            title: 'Sign out',
            subtitle: auth.username == null
                ? 'Clear session token'
                : 'Signed in as ${auth.username}',
            destructive: true,
            onTap: () => _confirmLogout(context),
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
  final bool destructive;

  const _SettingsTile({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
    this.destructive = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final accent = destructive ? theme.colorScheme.error : theme.colorScheme.primary;
    return Semantics(
      button: true,
      label: '$title. $subtitle',
      child: ListTile(
        leading: Icon(icon, color: accent),
        title: Text(
          title,
          style: theme.textTheme.titleMedium?.copyWith(
            color: destructive ? theme.colorScheme.error : null,
          ),
        ),
        subtitle: Text(subtitle, style: theme.textTheme.bodySmall),
        trailing: destructive
            ? null
            : const Icon(Icons.chevron_right_rounded),
        onTap: onTap,
        contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 4),
      ),
    );
  }
}
