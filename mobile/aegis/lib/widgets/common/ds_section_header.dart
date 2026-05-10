import 'package:flutter/material.dart';

/// Material 3 section header — uppercase, primary-tinted, used to
/// group cards on the dashboard / specialist screens.
///
/// Replaces the hand-rolled `Text('LATEST A.I. ANALYSIS', style: ...)`
/// pattern that was repeated across 7 specialist screens.
class DsSectionHeader extends StatelessWidget {
  final String label;
  final Widget? trailing;

  const DsSectionHeader({super.key, required this.label, this.trailing});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label.toUpperCase(),
              style: theme.textTheme.labelMedium?.copyWith(
                color: theme.colorScheme.primary,
                letterSpacing: 1.1,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          ?trailing,
        ],
      ),
    );
  }
}
