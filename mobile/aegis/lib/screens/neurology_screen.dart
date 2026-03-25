import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/biometric_card.dart';
import '../widgets/interpretation_card.dart';
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
              BiometricCard(title: 'POSTURE', value: model.posture, unit: '', statusColor: AegisTheme.primary),
              BiometricCard(title: 'MOTION STATE', value: model.motionState, unit: '', statusColor: AegisTheme.primary),
              BiometricCard(title: 'FALL RISK', value: model.fallRiskScore.toStringAsFixed(1), unit: '/10', statusColor: model.fallRiskScore > 5 ? AegisTheme.statusWarning : AegisTheme.statusNormal),
            ],
          ),
          const SizedBox(height: 24),
          const Text('LATEST A.I. ANALYSIS', style: TextStyle(color: AegisTheme.textMuted, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
          const SizedBox(height: 12),
          const InterpretationCard(
            title: "Neurological & Balance Assessment",
            icon: Icons.psychology_rounded,
            content: "**Observations:**\n- **IMU Posture**: Alignment is upright.\n- **Motion State**: Static / Minimal noise.\n- **Fall Risk Score**: Extremely low probability.\n\n**Conclusion**:\nMotor control and vestibular balance are stable. No tremors or sudden orthostatic anomalies detected.",
          ),
        ],
      ),
    );
  }
}
