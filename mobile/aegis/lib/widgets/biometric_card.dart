import 'package:flutter/material.dart';

import '../theme/medverse_typography.dart';

/// Material 3 dashboard tile for one numeric vital. Used everywhere
/// the dashboard / specialist screens render a HR / SpO₂ / Temp /
/// posture / fetal-state value.
///
/// Three accessibility wins over the previous implementation:
///   - Tabular numbers (JetBrainsMono via [MedverseTypography.mono])
///     so the digits don't reflow when the value updates tick-to-tick.
///   - Wrapped in `Semantics(label: '{title}: {value} {unit}')` so
///     TalkBack announces "Heart rate: 72 beats per minute".
///   - `AnimatedSwitcher` on the value text so a live update tweens
///     instead of swapping abruptly. Tween disabled in reduced-motion
///     mode automatically (M3 default behaviour).
///
/// Reads colours from `Theme.of(context).colorScheme` rather than the
/// legacy `MedVerseTheme.*` constants so a future light-theme / high-
/// contrast toggle propagates cleanly.
class BiometricCard extends StatelessWidget {
  final String title;
  final String value;
  final String unit;
  final Color statusColor;

  /// Optional human-friendly description of the vital read aloud by
  /// screen readers. Defaults to a concatenation of [title] / [value] /
  /// [unit] when null. Use this to expand abbreviations (e.g. pass
  /// `semanticUnit: "milliseconds"` when [unit] is "ms").
  final String? semanticUnit;

  const BiometricCard({
    super.key,
    required this.title,
    required this.value,
    required this.unit,
    required this.statusColor,
    this.semanticUnit,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final spokenUnit = semanticUnit ?? unit;
    final spoken = unit.isEmpty
        ? '$title: $value'
        : '$title: $value $spokenUnit';

    return Semantics(
      label: spoken,
      readOnly: true,
      child: Card(
        color: cs.surfaceContainerLow,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 10.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    width: 8,
                    height: 8,
                    decoration:
                        BoxDecoration(shape: BoxShape.circle, color: statusColor),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: FittedBox(
                      fit: BoxFit.scaleDown,
                      alignment: Alignment.centerLeft,
                      child: Text(
                        title,
                        style: theme.textTheme.labelMedium?.copyWith(
                          color: cs.onSurfaceVariant,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
              Expanded(
                child: Align(
                  alignment: Alignment.bottomLeft,
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.baseline,
                      textBaseline: TextBaseline.alphabetic,
                      children: [
                        // Tween the value text on every change. M3
                        // standard duration; collapses to instant
                        // automatically when MediaQuery.disableAnimations
                        // is set.
                        AnimatedSwitcher(
                          duration: const Duration(milliseconds: 250),
                          transitionBuilder: (child, anim) =>
                              FadeTransition(opacity: anim, child: child),
                          child: Text(
                            value,
                            // ValueKey forces a fresh widget instance
                            // for AnimatedSwitcher to detect the change.
                            key: ValueKey<String>(value),
                            style: MedverseTypography.mono(28).copyWith(
                              color: cs.onSurface,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                        if (unit.isNotEmpty) ...[
                          const SizedBox(width: 4),
                          Text(
                            unit,
                            style: theme.textTheme.labelLarge?.copyWith(
                              color: statusColor,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ]
                      ],
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
}
