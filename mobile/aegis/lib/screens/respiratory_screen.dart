import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/live_waveform.dart';
import '../widgets/biometric_card.dart';
import '../widgets/interpretation_card.dart';
import '../theme.dart';

class RespiratoryScreen extends StatelessWidget {
  const RespiratoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          LiveWaveform(title: 'PNEUMOGRAPHY (RSP)', dataSource: model.rspData, color: AegisTheme.rspColor, height: 200),
          const SizedBox(height: 16),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: [
              BiometricCard(title: 'RESP RATE', value: model.respiratoryRate.toString(), unit: 'bpm', statusColor: AegisTheme.rspColor),
              BiometricCard(title: 'SpO2', value: model.spO2.toString(), unit: '%', statusColor: AegisTheme.primary),
            ],
          ),
          const SizedBox(height: 24),
          const Text('LATEST A.I. ANALYSIS', style: TextStyle(color: AegisTheme.textMuted, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
          const SizedBox(height: 12),
          const InterpretationCard(
            title: "Pulmonology Assessment",
            icon: Icons.air_rounded,
            content: "**Observations:**\n- **Respiratory Rate**: 16 breaths per minute.\n- **SpO2**: Saturated consistently at 98%.\n- **Pneumography**: The waveform exhibits smooth sinusoidal expansion and contraction with zero paradoxical movements.\n\n**Conclusion**:\nAirway function is optimal. No episodes of apnea or dyspnea detected during the observation window.",
          ),
        ],
      ),
    );
  }
}
