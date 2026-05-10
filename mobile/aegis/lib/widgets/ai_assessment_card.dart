import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:provider/provider.dart';

import '../services/ai_assessment_repository.dart';
import '../widgets/chat/experts.dart';

/// Auto-refreshing AI clinical assessment card.
///
/// Drop one onto every specialist screen — replaces the seven static
/// hardcoded `InterpretationCard` instances. Behaviour:
///
///   1. On mount, calls `repository.requestAssessment(specialty)` —
///      the repository decides whether to actually hit the network
///      (cache hit / no telemetry drift = no request).
///   2. Renders the four cache states distinctly: `loading` → shimmer
///      title + linear progress; `loaded` → severity chip + markdown
///      body + freshness ("Updated 12 s ago"); `error` → friendly
///      error + retry; `null` (first ever load) → empty placeholder.
///   3. The "Refresh" button forces a re-fetch regardless of cache.
///
/// Wrapped in `Semantics` so screen readers announce the state +
/// content cleanly.
class AiAssessmentCard extends StatefulWidget {
  /// Backend specialty id — must match `/api/agent/ask`'s `specialty`
  /// field (e.g. "cardiology", "obstetrics", "general physician").
  final String specialty;

  const AiAssessmentCard({super.key, required this.specialty});

  @override
  State<AiAssessmentCard> createState() => _AiAssessmentCardState();
}

class _AiAssessmentCardState extends State<AiAssessmentCard> {
  late final AiAssessmentRepository _repo;

  @override
  void initState() {
    super.initState();
    _repo = context.read<AiAssessmentRepository>();
    // Defer to first frame so context.read is safe + the snapshot
    // stream has had a tick to populate.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _repo.requestAssessment(widget.specialty);
    });
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final persona = expertPersonaById(widget.specialty);

    return AnimatedBuilder(
      animation: _repo,
      builder: (context, _) {
        final entry = _repo.entry(widget.specialty);
        return Card(
          clipBehavior: Clip.antiAlias,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header — icon + title + severity chip + refresh.
                Row(
                  children: [
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: persona.accent.withValues(alpha: 0.14),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(persona.icon, color: persona.accent, size: 20),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${persona.label} Assessment',
                            style: theme.textTheme.titleMedium,
                          ),
                          Text(
                            _subtitleFor(entry),
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: cs.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (entry?.severity != null) _SeverityChip(severity: entry!.severity!),
                    Semantics(
                      button: true,
                      label: 'Refresh ${persona.label} assessment',
                      child: IconButton(
                        icon: const Icon(Icons.refresh_rounded),
                        tooltip: 'Refresh',
                        onPressed: entry?.isLoading == true
                            ? null
                            : () => _repo.requestAssessment(
                                  widget.specialty,
                                  force: true,
                                ),
                      ),
                    ),
                  ],
                ),
                if (entry?.isLoading == true) ...[
                  const SizedBox(height: 8),
                  const LinearProgressIndicator(),
                ],
                const SizedBox(height: 12),
                _Body(entry: entry, personaLabel: persona.label),
              ],
            ),
          ),
        );
      },
    );
  }

  String _subtitleFor(AiAssessmentEntry? e) {
    if (e == null) return 'Initialising…';
    if (e.isLoading) {
      return e.text == null ? 'Analysing live telemetry…' : 'Refreshing…';
    }
    if (e.isError) return 'Connection error';
    final age = DateTime.now().difference(e.fetchedAt);
    if (age.inSeconds < 60) return 'Updated just now';
    if (age.inMinutes < 60) return 'Updated ${age.inMinutes} min ago';
    return 'Updated ${age.inHours} hr ago';
  }
}

class _Body extends StatelessWidget {
  final AiAssessmentEntry? entry;
  final String personaLabel;
  const _Body({required this.entry, required this.personaLabel});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;

    if (entry == null) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Text(
          'Tap refresh to request the first assessment.',
          style: theme.textTheme.bodyMedium?.copyWith(color: cs.onSurfaceVariant),
        ),
      );
    }

    if (entry!.isError) {
      return Semantics(
        liveRegion: true,
        label: '$personaLabel assessment failed: ${entry!.errorMessage}',
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: cs.errorContainer.withValues(alpha: 0.4),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.error_outline, color: cs.error, size: 18),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  entry!.errorMessage ?? 'Unknown error',
                  style: theme.textTheme.bodySmall?.copyWith(color: cs.onErrorContainer),
                ),
              ),
            ],
          ),
        ),
      );
    }

    final body = entry!.text;
    if (body == null || body.isEmpty) {
      return _ShimmerLines(theme: theme);
    }

    return Semantics(
      label: '$personaLabel assessment: $body',
      child: MarkdownBody(
        data: body,
        selectable: true,
        styleSheet: MarkdownStyleSheet.fromTheme(theme).copyWith(
          p: theme.textTheme.bodyMedium,
          strong: theme.textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}

class _ShimmerLines extends StatelessWidget {
  final ThemeData theme;
  const _ShimmerLines({required this.theme});

  @override
  Widget build(BuildContext context) {
    Widget bar(double widthFraction) => Container(
          height: 12,
          width: MediaQuery.of(context).size.width * widthFraction,
          margin: const EdgeInsets.only(bottom: 8),
          decoration: BoxDecoration(
            color: theme.colorScheme.surfaceContainerHigh,
            borderRadius: BorderRadius.circular(6),
          ),
        );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [bar(0.85), bar(0.65), bar(0.75)],
    );
  }
}

class _SeverityChip extends StatelessWidget {
  final String severity;
  const _SeverityChip({required this.severity});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final (bg, fg, label) = switch (severity.toLowerCase()) {
      'critical' || 'severe' => (theme.colorScheme.errorContainer, theme.colorScheme.onErrorContainer, 'CRITICAL'),
      'concerning' || 'warning' || 'elevated' => (theme.colorScheme.tertiaryContainer, theme.colorScheme.onTertiaryContainer, 'WATCH'),
      'normal' || 'nominal' => (theme.colorScheme.secondaryContainer, theme.colorScheme.onSecondaryContainer, 'NORMAL'),
      _ => (theme.colorScheme.surfaceContainerHigh, theme.colorScheme.onSurface, severity.toUpperCase()),
    };
    return Container(
      margin: const EdgeInsets.only(right: 4),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: theme.textTheme.labelSmall?.copyWith(
          color: fg,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.6,
        ),
      ),
    );
  }
}
