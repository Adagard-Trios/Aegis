import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/system_summary.dart';
import '../widgets/vest_3d_viewer.dart';
import '../widgets/biometric_card.dart';
import '../theme.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SystemSummary(),
          const SizedBox(height: 16),
          const Vest3DViewer(),
          const SizedBox(height: 16),
          Text(
            'LIVE BIOMETRICS',
            style: TextStyle(
              color: AegisTheme.textMuted,
              fontSize: 12,
              fontWeight: FontWeight.w600,
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(height: 8),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: [
              BiometricCard(title: 'HEART RATE', value: model.heartRate.toString(), unit: 'bpm', statusColor: AegisTheme.ecgColor),
              BiometricCard(title: 'SpO2', value: model.spO2.toString(), unit: '%', statusColor: AegisTheme.primary),
              BiometricCard(title: 'TEMP', value: model.temperature.toStringAsFixed(1), unit: '°C', statusColor: AegisTheme.statusWarning),
              BiometricCard(title: 'RESP RATE', value: model.respiratoryRate.toString(), unit: 'bpm', statusColor: AegisTheme.accent),
            ],
          ),
        ],
      ),
    );
  }
}
