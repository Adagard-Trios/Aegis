import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/live_waveform.dart';
import '../widgets/biometric_card.dart';
import '../widgets/interpretation_card.dart';
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
          LiveWaveform(title: 'FOETAL HEART RATE (CTTG)', dataSource: model.fhrData, color: AegisTheme.fhrColor, height: 200),
          const SizedBox(height: 16),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: [
              BiometricCard(title: 'FOETAL HR', value: '140', unit: 'bpm', statusColor: AegisTheme.fhrColor),
            ],
          ),
          const SizedBox(height: 24),
          const Text('LATEST A.I. ANALYSIS', style: TextStyle(color: AegisTheme.textMuted, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
          const SizedBox(height: 12),
          const InterpretationCard(
            title: "Obstetrics & Fetal Assessment",
            icon: Icons.pregnant_woman_rounded,
            content: "**Observations:**\n- **Fetal Heart Rate**: Baseline holding steady near 140 BPM.\n- **Variability**: Moderate variability observed.\n- **Accelerations**: Presence of sporadic healthy accelerations.\n\n**Conclusion**:\nReassuring fetal status Category I tracing. No late decelerations or concerning patterns.",
          ),
        ],
      ),
    );
  }
}
