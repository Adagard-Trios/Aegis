import 'package:flutter/material.dart';

/// Accessibility helpers — minimum-tap-target enforcement, reduced-motion
/// override, high-contrast surface bumps. Centralised so widgets just
/// wrap themselves in [MinimumTapTarget(child: ...)] without knowing
/// the exact threshold.
class MedverseA11y {
  MedverseA11y._();

  /// Default tap target — Material 3 spec. Bumped to 56 in
  /// large-tap-target mode (set from AccessibilitySettingsScreen).
  static double minTapTarget = 48.0;

  /// True when the user enabled high-contrast mode in
  /// AccessibilitySettingsScreen. Read by [MedverseTheme] when seeding
  /// the ColorScheme so surfaces become more luminance-distinct.
  static bool highContrastOverride = false;
}

/// Wrap an interactive widget so its hit-test area is at least
/// [MedverseA11y.minTapTarget] in both axes. Doesn't change the visual
/// size — just expands the gesture surface.
///
/// Use over IconButtons / Chips / list-trailing widgets when you need
/// to be sure a thumb-tap hits cleanly even when the visual element
/// is smaller (e.g. a 24 px icon).
class MinimumTapTarget extends StatelessWidget {
  final Widget child;
  final double? minSize;

  const MinimumTapTarget({super.key, required this.child, this.minSize});

  @override
  Widget build(BuildContext context) {
    final size = minSize ?? MedverseA11y.minTapTarget;
    return ConstrainedBox(
      constraints: BoxConstraints(
        minWidth: size,
        minHeight: size,
      ),
      child: Center(child: child),
    );
  }
}
