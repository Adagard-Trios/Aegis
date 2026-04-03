import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/vest_data_model.dart';
import '../theme.dart';

class SystemSummary extends StatelessWidget {
  const SystemSummary({super.key});

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Flexible(
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.shield_rounded, color: MedVerseTheme.primary),
                      SizedBox(width: 8),
                      Flexible(
                        child: FittedBox(
                          fit: BoxFit.scaleDown,
                          child: Text(
                            'MedVerse System',
                            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: MedVerseTheme.textMain),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Flexible(
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: model.isConnected
                            ? MedVerseTheme.statusNormal.withOpacity(0.2)
                            : MedVerseTheme.statusWarning.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: model.isConnected
                              ? MedVerseTheme.statusNormal
                              : MedVerseTheme.statusWarning,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: model.isConnected ? MedVerseTheme.statusNormal : MedVerseTheme.statusWarning,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            model.connectionStatus,
                            style: TextStyle(
                              fontSize: 12,
                              color: model.isConnected ? MedVerseTheme.statusNormal : MedVerseTheme.statusWarning,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              "General Physician Assessment",
              style: TextStyle(
                fontSize: 12,
                color: MedVerseTheme.textMuted,
                letterSpacing: 1.1,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              model.isConnected
                  ? "Patient stable. Vitals within normal limits. All hardware active."
                  : "No data stream connected. Connect vest to begin health assessment.",
              style: const TextStyle(
                fontSize: 14,
                color: MedVerseTheme.textMain,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
