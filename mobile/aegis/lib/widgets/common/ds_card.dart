import 'package:flutter/material.dart';

/// Design-system card. Material 3 tonal surface (`surfaceContainerLow`)
/// with rounded 16-px corners. Use as the wrapper around any
/// dashboard-style content block — replaces ad-hoc `Container(...)`
/// decorations scattered across the app.
///
/// Three variants:
///   - `DsCard.filled` — default, soft tonal surface
///   - `DsCard.outlined` — for content that needs a visible boundary
///     (e.g. sensor health rows, where tonal surface alone isn't
///     distinct enough on `surfaceContainer` parents)
///   - `DsCard.error` — error-tinted container, used by failure states
class DsCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry padding;
  final VoidCallback? onTap;
  final _Variant _variant;

  const DsCard.filled({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.onTap,
  }) : _variant = _Variant.filled;

  const DsCard.outlined({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.onTap,
  }) : _variant = _Variant.outlined;

  const DsCard.error({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(16),
    this.onTap,
  }) : _variant = _Variant.error;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final (bg, border) = switch (_variant) {
      _Variant.filled => (cs.surfaceContainerLow, null),
      _Variant.outlined => (
        cs.surfaceContainerLow,
        Border.all(color: cs.outlineVariant, width: 1)
      ),
      _Variant.error => (cs.errorContainer.withValues(alpha: 0.4), null),
    };

    Widget body = Container(
      padding: padding,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(16),
        border: border,
      ),
      child: child,
    );

    if (onTap != null) {
      body = InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: body,
      );
    }

    return body;
  }
}

enum _Variant { filled, outlined, error }
