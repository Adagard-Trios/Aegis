import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/ai_assessment_card.dart';
import '../widgets/live_waveform.dart';
import '../widgets/biometric_card.dart';
import '../theme.dart';

class ObstetricsScreen extends StatelessWidget {
  const ObstetricsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          LiveWaveform(title: 'FOETAL HEART RATE (CTTG)', dataSource: model.fhrData, color: MedVerseTheme.fhrColor, height: 200),
          const SizedBox(height: 16),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: [
              BiometricCard(title: 'FOETAL HR', value: model.hasKicks ? '145' : '140', unit: 'bpm', statusColor: MedVerseTheme.fhrColor),
              BiometricCard(
                title: 'ACCELERATIONS', 
                value: model.hasKicks ? 'Reactive' : 'Quiet', 
                unit: '', 
                statusColor: model.hasKicks ? MedVerseTheme.statusWarning : MedVerseTheme.primary
              ),
              BiometricCard(
                title: 'UTERINE ACTIVITY', 
                value: model.hasContractions ? 'Elevated' : 'None', 
                unit: '', 
                statusColor: model.hasContractions ? MedVerseTheme.statusCritical : MedVerseTheme.primary
              ),
              BiometricCard(title: 'MATERNAL HR', value: model.heartRate > 0 ? model.heartRate.toString() : '72', unit: 'bpm', statusColor: MedVerseTheme.spo2Color),
            ],
          ),
          const SizedBox(height: 24),
          const AiAssessmentCard(specialty: 'obstetrics'),
        ],
      ),
    );
  }
}
