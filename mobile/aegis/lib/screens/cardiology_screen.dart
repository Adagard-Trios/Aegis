import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/live_waveform.dart';
import '../widgets/biometric_card.dart';
import '../widgets/interpretation_card.dart';
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
          LiveWaveform(title: 'LEAD II ECG (100Hz)', dataSource: model.ecgData, color: MedVerseTheme.ecgColor, height: 180),
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
              BiometricCard(title: 'BLOOD PRESSURE', value: '\${model.systolicBp.toInt()}/\${model.diastolicBp.toInt()}', unit: 'mmHg', statusColor: MedVerseTheme.statusNormal),
              BiometricCard(title: 'HRV (RMSSD)', value: model.hrvRmssd.toStringAsFixed(1), unit: 'ms', statusColor: MedVerseTheme.primary),
            ],
          ),
          const SizedBox(height: 24),
          const Text('LATEST A.I. ANALYSIS', style: TextStyle(color: MedVerseTheme.textMuted, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
          const SizedBox(height: 12),
          const InterpretationCard(
            title: "Cardiology Expert Assessment",
            icon: Icons.monitor_heart_rounded,
            content: "**Observations:**\n- **Heart Rate**: Stable baseline around 72 BPM.\n- **ECG Lead II**: The QRS complexes are sharp with normal amplitude. P-waves are visible and precede every QRS. No ST-segment elevation or depression detected.\n- **HRV**: Root Mean Square of Successive Differences (RMSSD) is normal.\n\n**Conclusion**:\nCardiovascular function is fully nominal with no signs of arrhythmias or ischemic events.",
          ),
        ],
      ),
    );
  }
}
