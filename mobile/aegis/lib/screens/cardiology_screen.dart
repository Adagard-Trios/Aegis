import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/ai_assessment_card.dart';
import '../widgets/live_waveform.dart';
import '../widgets/multi_lead_ecg_waveform.dart';
import '../widgets/biometric_card.dart';
import '../theme.dart';

class CardiologyScreen extends StatelessWidget {
  const CardiologyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          MultiLeadEcgWaveform(
            title: 'ECG — LEADS I / II / III  (Einthoven, ~333 Hz)',
            lead1: model.ecgLead1Data,
            lead2: model.ecgLead2Data,
            lead3: model.ecgLead3Data,
            height: 240,
          ),
          const SizedBox(height: 16),
          LiveWaveform(title: 'PHOTOPLETHYSMOGRAPHY (PPG)', dataSource: model.ppgData, color: MedVerseTheme.ppgColor, height: 120, minY: 0, maxY: 1.0),
          const SizedBox(height: 16),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: [
              // BP source: the vest has no cuff. Until a manual-entry
              // path or the backend's PK/PD-derived estimate lands,
              // show "—/—" instead of literal-string '0/0'. The earlier
              // implementation had escaped '$' tokens so the screen was
              // rendering the source text — fixed here.
              BiometricCard(
                title: 'BLOOD PRESSURE',
                value: (model.systolicBp > 0 && model.diastolicBp > 0)
                    ? '${model.systolicBp.toInt()}/${model.diastolicBp.toInt()}'
                    : '—/—',
                unit: 'mmHg',
                statusColor: (model.systolicBp > 0 && model.diastolicBp > 0)
                    ? MedVerseTheme.statusNormal
                    : MedVerseTheme.textMuted,
              ),
              BiometricCard(
                title: 'HRV (RMSSD)',
                value: model.hrvRmssd > 0
                    ? model.hrvRmssd.toStringAsFixed(1)
                    : '—',
                unit: 'ms',
                statusColor: MedVerseTheme.primary,
              ),
            ],
          ),
          const SizedBox(height: 24),
          // Live AI assessment — auto-refreshes against the current
          // telemetry snapshot via the AiAssessmentRepository cache.
          // Replaces the previous static hardcoded "Cardiology Expert
          // Assessment" placeholder text.
          const AiAssessmentCard(specialty: 'cardiology'),
        ],
      ),
    );
  }
}
