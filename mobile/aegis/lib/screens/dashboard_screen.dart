import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/system_summary.dart';
import '../widgets/vest_3d_viewer.dart';
import '../widgets/biometric_card.dart';
import '../widgets/simulation_controls_panel.dart';
import '../theme.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
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
          const SimulationControlsPanel(),
          const SizedBox(height: 16),
          Text(
            'LIVE BIOMETRICS',
            style: TextStyle(
              color: MedVerseTheme.textMuted,
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
              BiometricCard(title: 'HEART RATE', value: model.heartRate.toString(), unit: 'bpm', statusColor: MedVerseTheme.ecgColor),
              BiometricCard(title: 'SpO2', value: model.spO2.toString(), unit: '%', statusColor: MedVerseTheme.primary),
              BiometricCard(title: 'TEMP', value: model.temperature.toStringAsFixed(1), unit: '°C', statusColor: MedVerseTheme.statusWarning),
              BiometricCard(title: 'RESP RATE', value: model.respiratoryRate.toString(), unit: 'bpm', statusColor: MedVerseTheme.accent),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'FETAL & POSTURE',
            style: TextStyle(
              color: MedVerseTheme.textMuted,
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
              BiometricCard(title: 'FETAL KICKS', value: model.hasKicks ? 'ACTIVE' : 'NONE', unit: '', statusColor: model.hasKicks ? Colors.tealAccent : MedVerseTheme.textMuted),
              BiometricCard(title: 'CONTRACTIONS', value: model.hasContractions ? 'TRUE' : 'FALSE', unit: '', statusColor: model.hasContractions ? MedVerseTheme.statusCritical : MedVerseTheme.textMuted),
              BiometricCard(title: 'SPINAL ANGLE', value: model.fallRiskScore.toStringAsFixed(1), unit: '°', statusColor: MedVerseTheme.primary),
              BiometricCard(title: 'ENV TEMP', value: model.ambientTemp.toStringAsFixed(1), unit: '°C', statusColor: MedVerseTheme.statusWarning),
            ],
          ),
        ],
      ),
    );
  }
}
