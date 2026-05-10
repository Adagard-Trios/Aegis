import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/ai_assessment_card.dart';
import '../widgets/biometric_card.dart';
import '../theme.dart';

class NeurologyScreen extends StatelessWidget {
  const NeurologyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: [
              BiometricCard(title: 'POSTURE', value: model.posture, unit: '', statusColor: MedVerseTheme.primary),
              BiometricCard(title: 'MOTION STATE', value: model.motionState, unit: '', statusColor: MedVerseTheme.primary),
              BiometricCard(title: 'FALL RISK', value: model.fallRiskScore.toStringAsFixed(1), unit: '/10', statusColor: model.fallRiskScore > 5 ? MedVerseTheme.statusWarning : MedVerseTheme.statusNormal),
            ],
          ),
          const SizedBox(height: 24),
          const AiAssessmentCard(specialty: 'neurology'),
        ],
      ),
    );
  }
}
