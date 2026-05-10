import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../theme.dart';

/// One canvas, three Einthoven leads (L1 / L2 / L3) overlaid with
/// distinct colors and a legend.
///
/// Each lead drives an independent [ValueNotifier<List<double>>] of
/// rolling samples (500-element ring on the model side). The painter
/// scales all three to a shared Y range so the per-lead amplitudes
/// can be compared directly — Lead III amplitude in particular is
/// often smaller than Lead II for upper-body placements.
class MultiLeadEcgWaveform extends StatelessWidget {
  final ValueListenable<List<double>> lead1;
  final ValueListenable<List<double>> lead2;
  final ValueListenable<List<double>> lead3;
  final String title;
  final double height;

  const MultiLeadEcgWaveform({
    super.key,
    required this.lead1,
    required this.lead2,
    required this.lead3,
    this.title = 'ECG — Leads I / II / III',
    this.height = 240,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    style: const TextStyle(
                      color: MedVerseTheme.textMuted,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 1.2,
                    ),
                  ),
                ),
                const _LegendDot(color: _l1Color, label: 'I'),
                const SizedBox(width: 8),
                const _LegendDot(color: _l2Color, label: 'II'),
                const SizedBox(width: 8),
                const _LegendDot(color: _l3Color, label: 'III'),
              ],
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: height,
              child: ClipRect(
                child: _MultiTrace(
                  lead1: lead1,
                  lead2: lead2,
                  lead3: lead3,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  // Distinct colors per lead — colour-blind safe pairs (cyan / amber / fuchsia).
  static const Color _l1Color = MedVerseTheme.primary;       // cyan
  static const Color _l2Color = MedVerseTheme.statusWarning; // amber
  static const Color _l3Color = MedVerseTheme.fhrColor;      // fuchsia
}

class _LegendDot extends StatelessWidget {
  final Color color;
  final String label;
  const _LegendDot({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        Text(label,
            style: const TextStyle(
                color: MedVerseTheme.textMain,
                fontSize: 11,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.6)),
      ],
    );
  }
}

class _MultiTrace extends StatelessWidget {
  final ValueListenable<List<double>> lead1;
  final ValueListenable<List<double>> lead2;
  final ValueListenable<List<double>> lead3;
  const _MultiTrace({
    required this.lead1,
    required this.lead2,
    required this.lead3,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: Listenable.merge([lead1, lead2, lead3]),
      builder: (_, _) {
        final a = lead1.value;
        final b = lead2.value;
        final c = lead3.value;
        if (a.isEmpty && b.isEmpty && c.isEmpty) {
          return Center(
            child: Text(
              'Waiting for ECG burst…',
              style: TextStyle(
                  color: MedVerseTheme.textMuted.withValues(alpha: 0.5)),
            ),
          );
        }
        return CustomPaint(
          painter: _MultiLeadPainter(
            lead1: a,
            lead2: b,
            lead3: c,
          ),
        );
      },
    );
  }
}

class _MultiLeadPainter extends CustomPainter {
  final List<double> lead1;
  final List<double> lead2;
  final List<double> lead3;

  _MultiLeadPainter({
    required this.lead1,
    required this.lead2,
    required this.lead3,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (lead1.isEmpty && lead2.isEmpty && lead3.isEmpty) return;

    // Pick a shared Y range from all three traces so amplitudes are
    // directly comparable. Pad the range by 5% so peaks don't clip.
    final all = <double>[...lead1, ...lead2, ...lead3];
    var minV = all.first, maxV = all.first;
    for (final v in all) {
      if (v < minV) minV = v;
      if (v > maxV) maxV = v;
    }
    var range = maxV - minV;
    if (range < 1e-6) range = 1.0;
    final pad = range * 0.05;
    minV -= pad;
    range += pad * 2;

    // Draw a faint horizontal midline grid for orientation.
    final grid = Paint()
      ..color = MedVerseTheme.textMuted.withValues(alpha: 0.08)
      ..strokeWidth = 1;
    canvas.drawLine(Offset(0, size.height / 2),
        Offset(size.width, size.height / 2), grid);

    _drawTrace(canvas, size, lead1,
        MedLeadStyle.l1, minV, range);
    _drawTrace(canvas, size, lead2,
        MedLeadStyle.l2, minV, range);
    _drawTrace(canvas, size, lead3,
        MedLeadStyle.l3, minV, range);
  }

  void _drawTrace(Canvas canvas, Size size, List<double> data, Color color,
      double minY, double rangeY) {
    if (data.isEmpty) return;
    final stroke = Paint()
      ..color = color
      ..strokeWidth = 1.6
      ..style = PaintingStyle.stroke
      ..strokeJoin = StrokeJoin.round;

    final glow = Paint()
      ..color = color.withValues(alpha: 0.25)
      ..strokeWidth = 4.0
      ..style = PaintingStyle.stroke
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 2.5);

    final path = Path();
    final spacing = size.width / (500 - 1);
    for (var i = 0; i < data.length; i++) {
      final x = i * spacing;
      final norm = ((data[i] - minY) / rangeY).clamp(0.0, 1.0);
      final y = size.height - (norm * size.height);
      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    canvas.drawPath(path, glow);
    canvas.drawPath(path, stroke);
  }

  @override
  bool shouldRepaint(covariant _MultiLeadPainter old) {
    return old.lead1.length != lead1.length ||
        old.lead2.length != lead2.length ||
        old.lead3.length != lead3.length ||
        (lead1.isNotEmpty && lead1.last != old.lead1.lastOrNull) ||
        (lead2.isNotEmpty && lead2.last != old.lead2.lastOrNull) ||
        (lead3.isNotEmpty && lead3.last != old.lead3.lastOrNull);
  }
}

extension<T> on List<T> {
  T? get lastOrNull => isEmpty ? null : last;
}

/// Per-lead colours — kept private to the widget so all consumers
/// render with the same scheme.
class MedLeadStyle {
  static const Color l1 = MedVerseTheme.primary;
  static const Color l2 = MedVerseTheme.statusWarning;
  static const Color l3 = MedVerseTheme.fhrColor;
}
