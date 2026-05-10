import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/ai_assessment_card.dart';
import '../widgets/biometric_card.dart';
import '../theme.dart';

/// Ocular specialist screen.
///
/// The vest doesn't have eye-tracking or fundus optics — ocular work is
/// driven by uploaded retinal images going through `/api/upload-image`,
/// then routed to the retinal_disease + retinal_age ML adapters
/// server-side. This screen surfaces the available context (HRV +
/// blood-pressure proxies that correlate with retinal vascular health)
/// and the most recent agent narrative.
class OcularScreen extends StatelessWidget {
  const OcularScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();

    // Crude vascular-stress flag: low HRV + high systolic = retinal-risk
    // pattern the agent prompt mentions. Honest stand-in for live ocular
    // signals we don't have hardware for.
    final hrvLow = model.hrvRmssd > 0 && model.hrvRmssd < 20;
    final hrHigh = model.heartRate > 100;
    final stressFlag = hrvLow && hrHigh;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: [
              BiometricCard(
                title: 'HRV (RMSSD)',
                value: model.hrvRmssd > 0
                    ? model.hrvRmssd.toStringAsFixed(1)
                    : '—',
                unit: 'ms',
                statusColor: hrvLow
                    ? MedVerseTheme.statusWarning
                    : MedVerseTheme.primary,
              ),
              BiometricCard(
                title: 'HEART RATE',
                value: model.heartRate > 0 ? model.heartRate.toString() : '—',
                unit: 'bpm',
                statusColor: hrHigh
                    ? MedVerseTheme.statusWarning
                    : MedVerseTheme.hrColor,
              ),
              BiometricCard(
                title: 'PERFUSION INDEX',
                value: model.perfusionIndex > 0
                    ? model.perfusionIndex.toStringAsFixed(2)
                    : '—',
                unit: '%',
                statusColor: MedVerseTheme.primary,
              ),
              BiometricCard(
                title: 'VASCULAR FLAG',
                value: stressFlag ? 'ELEVATED' : 'NOMINAL',
                unit: '',
                statusColor: stressFlag
                    ? MedVerseTheme.statusCritical
                    : MedVerseTheme.statusNormal,
              ),
            ],
          ),
          const SizedBox(height: 24),
          // Image-upload hint card. The vest can't capture fundus —
          // ML adapters need an uploaded retinal photograph from the
          // Diagnostics screen.
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: MedVerseTheme.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: MedVerseTheme.border),
            ),
            child: Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: MedVerseTheme.primary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.upload_file_rounded,
                      color: MedVerseTheme.primary),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Text(
                    'For retinal disease screening + biological retinal-age '
                    'estimation, upload a fundus image from the Diagnostics '
                    'tab. The ODIR-5K + RETFound adapters run server-side.',
                    style: TextStyle(
                        color: MedVerseTheme.textMuted, fontSize: 12),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          const Text(
            'LATEST A.I. ANALYSIS',
            style: TextStyle(
                color: MedVerseTheme.textMuted,
                fontSize: 12,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.5),
          ),
          const SizedBox(height: 12),
          const AiAssessmentCard(specialty: 'ocular'),
        ],
      ),
    );
  }
}
