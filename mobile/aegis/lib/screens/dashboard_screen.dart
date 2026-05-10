import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/biometric_card.dart';
import '../widgets/simulation_controls_panel.dart';
import '../widgets/system_summary.dart';
import '../widgets/wear_vest_banner.dart';
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

    return LayoutBuilder(
      builder: (context, constraints) {
        // Responsive column count: 2 columns on phones, 3 on
        // foldables / small tablets, 4 on wide tablets / desktop. Each
        // tile keeps its 1.2 aspect so wider columns mean shorter rows.
        final w = constraints.maxWidth;
        final cols = w >= 1100 ? 4 : w >= 800 ? 3 : 2;

        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(0, 0, 0, 16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Wear-vest banner — surfaces only when the vest is
              // connected but all PPG channels read at the no-contact
              // baseline. Self-hides when at least one MAX30102
              // reports tissue contact. Owns its own horizontal margin.
              const WearVestBanner(),
              const SizedBox(height: 16),
              // Everything else under a shared horizontal padding so
              // grids + section labels align consistently with the
              // 16-px page gutter.
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const SystemSummary(),
                    const SizedBox(height: 16),
                    const SimulationControlsPanel(),
                    const SizedBox(height: 16),
                    _SectionLabel(text: 'LIVE BIOMETRICS'),
                    const SizedBox(height: 8),
                    _BiometricGrid(cols: cols, children: [
                      BiometricCard(title: 'HEART RATE', value: model.heartRate.toString(), unit: 'bpm', statusColor: MedVerseTheme.ecgColor),
                      BiometricCard(title: 'SpO2', value: model.spO2.toString(), unit: '%', statusColor: MedVerseTheme.primary),
                      BiometricCard(title: 'TEMP', value: model.temperature.toStringAsFixed(1), unit: '°C', statusColor: MedVerseTheme.statusWarning),
                      BiometricCard(title: 'RESP RATE', value: model.respiratoryRate.toString(), unit: 'bpm', statusColor: MedVerseTheme.accent),
                    ]),
                    const SizedBox(height: 16),
                    _SectionLabel(text: 'FETAL & POSTURE'),
                    const SizedBox(height: 8),
                    _BiometricGrid(cols: cols, children: [
                      BiometricCard(title: 'FETAL KICKS', value: model.hasKicks ? 'ACTIVE' : 'NONE', unit: '', statusColor: model.hasKicks ? Colors.tealAccent : MedVerseTheme.textMuted),
                      BiometricCard(title: 'CONTRACTIONS', value: model.hasContractions ? 'TRUE' : 'FALSE', unit: '', statusColor: model.hasContractions ? MedVerseTheme.statusCritical : MedVerseTheme.textMuted),
                      BiometricCard(title: 'SPINAL ANGLE', value: model.fallRiskScore.toStringAsFixed(1), unit: '°', statusColor: MedVerseTheme.primary),
                      BiometricCard(title: 'ENV TEMP', value: model.ambientTemp.toStringAsFixed(1), unit: '°C', statusColor: MedVerseTheme.statusWarning),
                    ]),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel({required this.text});
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Text(
      text,
      style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: cs.primary,
            letterSpacing: 1.4,
            fontWeight: FontWeight.w800,
          ),
    );
  }
}

class _BiometricGrid extends StatelessWidget {
  final int cols;
  final List<Widget> children;
  const _BiometricGrid({required this.cols, required this.children});
  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: cols,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      // Aspect tightens slightly when columns multiply so rows don't
      // look stretched on tablets.
      childAspectRatio: cols >= 4 ? 1.15 : (cols == 3 ? 1.1 : 1.2),
      children: children,
    );
  }
}
