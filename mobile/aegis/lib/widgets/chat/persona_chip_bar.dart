import 'package:flutter/material.dart';

import 'experts.dart';

/// Horizontal scrollable row of M3 [FilterChip]s — one per specialty
/// persona. Selecting a chip swaps the active persona for the chat
/// thread; the parent screen persists that selection across sessions.
class PersonaChipBar extends StatelessWidget {
  final ExpertPersona selected;
  final ValueChanged<ExpertPersona> onSelected;

  const PersonaChipBar({
    super.key,
    required this.selected,
    required this.onSelected,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SizedBox(
      height: 56,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        itemCount: expertPersonas.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final p = expertPersonas[i];
          final isSelected = p.id == selected.id;
          return FilterChip(
            selected: isSelected,
            onSelected: (_) => onSelected(p),
            avatar: Icon(
              p.icon,
              size: 18,
              color: isSelected ? theme.colorScheme.onSecondaryContainer : p.accent,
            ),
            label: Text(p.label),
            labelStyle: theme.textTheme.labelLarge?.copyWith(
              color: isSelected
                  ? theme.colorScheme.onSecondaryContainer
                  : theme.colorScheme.onSurface,
            ),
            tooltip: 'Talk to ${p.label}',
            side: BorderSide(
              color: isSelected
                  ? Colors.transparent
                  : theme.colorScheme.outlineVariant,
            ),
          );
        },
      ),
    );
  }
}
