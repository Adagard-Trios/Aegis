import 'package:flutter/material.dart';

/// Pulsing skeleton placeholder bar — Material 3-aligned shimmer
/// substitute used in loading states (e.g. AiAssessmentCard while the
/// /api/agent/ask request is in flight). Single-vsync animation so a
/// stack of three bars only costs one ticker.
///
/// Wrapped in `Semantics(liveRegion: true, label: 'Loading')` so a
/// screen reader announces the load state once when it appears.
class DsLoading extends StatefulWidget {
  /// Number of placeholder bars to draw (default 3).
  final int lineCount;

  /// Fraction-of-width per line. Defaults to a natural-looking
  /// staggered pattern. Pass a custom list to match a specific layout.
  final List<double> lineWidthFractions;

  const DsLoading({
    super.key,
    this.lineCount = 3,
    this.lineWidthFractions = const [0.85, 0.65, 0.75],
  });

  @override
  State<DsLoading> createState() => _DsLoadingState();
}

class _DsLoadingState extends State<DsLoading>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ac;

  @override
  void initState() {
    super.initState();
    _ac = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _ac.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Semantics(
      liveRegion: true,
      label: 'Loading',
      child: AnimatedBuilder(
        animation: _ac,
        builder: (context, _) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: List.generate(widget.lineCount, (i) {
              final fractions = widget.lineWidthFractions;
              final fraction = fractions.isNotEmpty
                  ? fractions[i % fractions.length]
                  : 0.7;
              return Container(
                margin: const EdgeInsets.only(bottom: 8),
                height: 12,
                width: MediaQuery.of(context).size.width * fraction,
                decoration: BoxDecoration(
                  color: cs.surfaceContainerHigh
                      .withValues(alpha: 0.5 + 0.5 * _ac.value),
                  borderRadius: BorderRadius.circular(6),
                ),
              );
            }),
          );
        },
      ),
    );
  }
}
