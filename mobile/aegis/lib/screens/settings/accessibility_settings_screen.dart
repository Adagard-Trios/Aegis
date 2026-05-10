import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../theme/medverse_a11y.dart';
import '../../theme/medverse_motion.dart';

/// User-facing accessibility toggles. Each switch persists to secure
/// storage + flips a static on the corresponding theme module so the
/// rest of the app picks up the new behaviour the next time a screen
/// rebuilds.
///
/// Settings:
///   - **Reduced motion** — collapses every transition to instant.
///   - **High contrast** — bumps surface luminance for WCAG AAA.
///   - **Large tap targets** — bumps minimum hit area from 48 → 56 px.
class AccessibilitySettingsScreen extends StatefulWidget {
  const AccessibilitySettingsScreen({super.key});

  @override
  State<AccessibilitySettingsScreen> createState() =>
      _AccessibilitySettingsScreenState();
}

class _AccessibilitySettingsScreenState
    extends State<AccessibilitySettingsScreen> {
  static const _reducedKey = 'aegis.a11y.reduced_motion';
  static const _highContrastKey = 'aegis.a11y.high_contrast';
  static const _largeTapsKey = 'aegis.a11y.large_taps';
  final _storage = const FlutterSecureStorage();

  bool _reducedMotion = false;
  bool _highContrast = false;
  bool _largeTaps = false;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    try {
      _reducedMotion = (await _storage.read(key: _reducedKey)) == 'true';
      _highContrast = (await _storage.read(key: _highContrastKey)) == 'true';
      _largeTaps = (await _storage.read(key: _largeTapsKey)) == 'true';
      // Mirror to the theme statics so existing screens see the
      // restored values immediately.
      MedverseMotion.reducedMotionOverride = _reducedMotion;
      MedverseA11y.highContrastOverride = _highContrast;
      MedverseA11y.minTapTarget = _largeTaps ? 56.0 : 48.0;
    } catch (_) {/* non-fatal */}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _set(String key, bool value, void Function(bool) apply) async {
    apply(value);
    try {
      await _storage.write(key: key, value: value ? 'true' : 'false');
    } catch (_) {/* non-fatal */}
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    return ListView(
      padding: const EdgeInsets.symmetric(vertical: 8),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 16),
          child: Text(
            'MedVerse follows your system accessibility settings by default. '
            'Use the toggles below to override per-app behaviour.',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        SwitchListTile(
          secondary: const Icon(Icons.motion_photos_off_outlined),
          title: const Text('Reduced motion'),
          subtitle: const Text(
            'Collapse animations to instant. Useful for vestibular '
            'sensitivity or to save battery.',
          ),
          value: _reducedMotion,
          onChanged: (v) => _set(
            _reducedKey,
            v,
            (b) {
              _reducedMotion = b;
              MedverseMotion.reducedMotionOverride = b;
            },
          ),
        ),
        const Divider(height: 1),
        SwitchListTile(
          secondary: const Icon(Icons.contrast_outlined),
          title: const Text('High contrast'),
          subtitle: const Text(
            'Bump surface luminance for WCAG AAA-grade text contrast.',
          ),
          value: _highContrast,
          onChanged: (v) => _set(
            _highContrastKey,
            v,
            (b) {
              _highContrast = b;
              MedverseA11y.highContrastOverride = b;
            },
          ),
        ),
        const Divider(height: 1),
        SwitchListTile(
          secondary: const Icon(Icons.touch_app_outlined),
          title: const Text('Large tap targets'),
          subtitle: const Text(
            'Expand minimum hit area from 48 to 56 logical pixels.',
          ),
          value: _largeTaps,
          onChanged: (v) => _set(
            _largeTapsKey,
            v,
            (b) {
              _largeTaps = b;
              MedverseA11y.minTapTarget = b ? 56.0 : 48.0;
            },
          ),
        ),
        const SizedBox(height: 24),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Text(
            'Some changes (theme contrast, tap target size) take effect on '
            'next screen open. Restart the app to apply globally.',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
              fontStyle: FontStyle.italic,
            ),
          ),
        ),
      ],
    );
  }
}
