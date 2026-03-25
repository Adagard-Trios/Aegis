import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../theme.dart';

class InterpretationCard extends StatelessWidget {
  final String title;
  final String content;
  final IconData icon;

  const InterpretationCard({
    super.key,
    required this.title,
    required this.content,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: AegisTheme.surfaceHighlight.withOpacity(0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AegisTheme.primary.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: AegisTheme.primary, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(color: AegisTheme.primary, fontWeight: FontWeight.bold, fontSize: 16),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          MarkdownBody(
            data: content,
            styleSheet: MarkdownStyleSheet(
              p: const TextStyle(color: AegisTheme.textMain, height: 1.5, fontSize: 14),
              strong: const TextStyle(color: AegisTheme.accent, fontWeight: FontWeight.bold),
              listBullet: const TextStyle(color: AegisTheme.primary),
            ),
          ),
        ],
      ),
    );
  }
}
