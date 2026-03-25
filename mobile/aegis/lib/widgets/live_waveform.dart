import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import '../theme.dart';

class LiveWaveform extends StatelessWidget {
  final ValueListenable<List<double>> dataSource;
  final Color color;
  final String title;
  final double height;
  final double minY;
  final double maxY;

  const LiveWaveform({
    super.key,
    required this.dataSource,
    required this.color,
    required this.title,
    this.height = 120,
    this.minY = -1.5,
    this.maxY = 2.5,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              title,
              style: TextStyle(
                color: AegisTheme.textMuted,
                fontSize: 12,
                fontWeight: FontWeight.w600,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: height,
              child: ClipRect(
                child: ValueListenableBuilder<List<double>>(
                  valueListenable: dataSource,
                  builder: (context, data, child) {
                    if (data.isEmpty) {
                      return Center(
                        child: Text(
                          'Waiting for data...',
                          style: TextStyle(color: AegisTheme.textMuted.withOpacity(0.5)),
                        ),
                      );
                    }
                    return CustomPaint(
                      painter: _WaveformPainter(
                        data: data,
                        color: color,
                        minY: minY,
                        maxY: maxY,
                      ),
                    );
                  },
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _WaveformPainter extends CustomPainter {
  final List<double> data;
  final Color color;
  final double minY;
  final double maxY;

  _WaveformPainter({
    required this.data,
    required this.color,
    required this.minY,
    required this.maxY,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (data.isEmpty) return;

    final paint = Paint()
      ..color = color
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeJoin = StrokeJoin.round;

    final path = Path();
    final pointSpacing = size.width / (500 - 1); // We keep 500 samples in the model
    
    // Auto-scale Y or use fixed bounds
    final range = maxY - minY;
    
    for (int i = 0; i < data.length; i++) {
      final x = i * pointSpacing;
      // Normalize to 0..1 then invert (because canvas Y goes down)
      final normalizedY = ((data[i] - minY) / range).clamp(0.0, 1.0);
      final y = size.height - (normalizedY * size.height);

      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    // Glow effect
    final glowPaint = Paint()
      ..color = color.withOpacity(0.3)
      ..strokeWidth = 6.0
      ..style = PaintingStyle.stroke
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3.0);

    canvas.drawPath(path, glowPaint);
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _WaveformPainter oldDelegate) {
    // Only repaint if the end of the array changed (new data arrived)
    if (oldDelegate.data.isEmpty && data.isEmpty) return false;
    if (oldDelegate.data.isEmpty != data.isEmpty) return true;
    return oldDelegate.data.last != data.last || oldDelegate.data.length != data.length;
  }
}
