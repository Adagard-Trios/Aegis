import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

/// One message bubble in the chat list. Material 3 shape: outgoing
/// bubbles get a rounded-trailing tail (a tighter bottom-right corner),
/// incoming get a rounded-leading tail. Both surfaces use M3 tonal
/// containers (primaryContainer / surfaceContainerHigh) so they pick
/// up high-contrast / light-mode tweaks automatically.
class ChatMessageBubble extends StatelessWidget {
  /// True if the message came from the user (rendered right-aligned in
  /// the primary container). False = AI assistant reply.
  final bool isUser;

  /// Markdown body. Empty string is allowed when only an image is sent.
  final String text;

  /// Optional locally-captured image attached to the message.
  final String? imagePath;

  /// Specialty persona the message was sent to / from. Used in the
  /// Semantics label so screen readers announce "Cardiologist replied:"
  /// instead of just "AI replied:".
  final String? personaLabel;

  const ChatMessageBubble({
    super.key,
    required this.isUser,
    required this.text,
    this.imagePath,
    this.personaLabel,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final bg = isUser ? cs.primaryContainer : cs.surfaceContainerHigh;
    final fg = isUser ? cs.onPrimaryContainer : cs.onSurface;

    final radius = isUser
        ? const BorderRadius.only(
            topLeft: Radius.circular(18),
            topRight: Radius.circular(18),
            bottomLeft: Radius.circular(18),
            bottomRight: Radius.circular(4),
          )
        : const BorderRadius.only(
            topLeft: Radius.circular(18),
            topRight: Radius.circular(18),
            bottomRight: Radius.circular(18),
            bottomLeft: Radius.circular(4),
          );

    final maxWidth = MediaQuery.of(context).size.width * 0.78;
    final speakerLabel = isUser
        ? 'You said'
        : '${personaLabel ?? "Assistant"} replied';

    return Semantics(
      label: '$speakerLabel: $text',
      child: Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(
          mainAxisAlignment:
              isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
          children: [
            Flexible(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: maxWidth),
                child: Column(
                  crossAxisAlignment: isUser
                      ? CrossAxisAlignment.end
                      : CrossAxisAlignment.start,
                  children: [
                    if (imagePath != null) ...[
                      ClipRRect(
                        borderRadius: BorderRadius.circular(14),
                        child: Image.file(
                          File(imagePath!),
                          fit: BoxFit.cover,
                          width: maxWidth,
                          errorBuilder: (_, _, _) => Container(
                            width: maxWidth,
                            height: 120,
                            color: cs.surfaceContainer,
                            child: Icon(
                              Icons.broken_image_outlined,
                              color: cs.onSurfaceVariant,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                    ],
                    if (text.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 14, vertical: 10),
                        decoration: BoxDecoration(
                          color: bg,
                          borderRadius: radius,
                        ),
                        child: MarkdownBody(
                          data: text,
                          selectable: true,
                          styleSheet: MarkdownStyleSheet.fromTheme(theme).copyWith(
                            p: theme.textTheme.bodyMedium?.copyWith(color: fg),
                            strong: theme.textTheme.bodyMedium?.copyWith(
                              color: fg,
                              fontWeight: FontWeight.w700,
                            ),
                            listBullet: theme.textTheme.bodyMedium?.copyWith(color: fg),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Standalone "AI is typing…" pill — rendered while a request is in
/// flight so the user sees feedback. Pulses opacity for liveness.
class ChatTypingIndicator extends StatefulWidget {
  final String personaLabel;
  const ChatTypingIndicator({super.key, required this.personaLabel});

  @override
  State<ChatTypingIndicator> createState() => _ChatTypingIndicatorState();
}

class _ChatTypingIndicatorState extends State<ChatTypingIndicator>
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
    final theme = Theme.of(context);
    return Semantics(
      label: '${widget.personaLabel} is typing',
      liveRegion: true,
      child: Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(
          children: [
            AnimatedBuilder(
              animation: _ac,
              builder: (_, _) => Container(
                padding: const EdgeInsets.symmetric(
                    horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  color: theme.colorScheme.surfaceContainerHigh
                      .withValues(alpha: 0.4 + 0.6 * _ac.value),
                  borderRadius: const BorderRadius.only(
                    topLeft: Radius.circular(18),
                    topRight: Radius.circular(18),
                    bottomRight: Radius.circular(18),
                    bottomLeft: Radius.circular(4),
                  ),
                ),
                child: Text(
                  '${widget.personaLabel} is thinking…',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
