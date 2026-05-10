import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/ai_assessment_card.dart';
import '../widgets/biometric_card.dart';
import '../theme.dart';

/// Dermatology specialist screen.
///
/// The vest doesn't carry a dermatoscope; dermatology context comes from
/// the three skin-temperature probes (left axilla / right axilla /
/// cervical). The web Dermatology Expert reasons on these gradients +
/// uploaded skin images. This screen surfaces the live values and the
/// most-recent agent narrative; image upload is handled separately by
/// the Diagnostics screen / `/api/upload-image` endpoint.
class DermatologyScreen extends StatelessWidget {
  const DermatologyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();
    // Asymmetry between the two axillas — a clinically useful signal.
    final asymmetry = (model.skinTempLeft - model.skinTempRight).abs();
    final asymmetryFlag = asymmetry > 1.0;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: [
              BiometricCard(
                title: 'L AXILLA',
                value: model.skinTempLeft.toStringAsFixed(1),
                unit: '°C',
                statusColor: MedVerseTheme.tempColor,
              ),
              BiometricCard(
                title: 'R AXILLA',
                value: model.skinTempRight.toStringAsFixed(1),
                unit: '°C',
                statusColor: MedVerseTheme.tempColor,
              ),
              BiometricCard(
                title: 'CERVICAL',
                value: model.temperature.toStringAsFixed(1),
                unit: '°C',
                statusColor: MedVerseTheme.statusWarning,
              ),
              BiometricCard(
                title: 'ASYMMETRY',
                value: asymmetry.toStringAsFixed(2),
                unit: '°C',
                statusColor: asymmetryFlag
                    ? MedVerseTheme.statusCritical
                    : MedVerseTheme.statusNormal,
              ),
            ],
          ),
          const SizedBox(height: 16),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.2,
            children: [
              BiometricCard(
                title: 'AMBIENT TEMP',
                value: model.ambientTemp.toStringAsFixed(1),
                unit: '°C',
                statusColor: MedVerseTheme.primary,
              ),
              BiometricCard(
                title: 'HUMIDITY',
                value: model.humidity.toStringAsFixed(0),
                unit: '%',
                statusColor: MedVerseTheme.primary,
              ),
            ],
          ),
          const SizedBox(height: 24),
          const AiAssessmentCard(specialty: 'dermatology'),
        ],
      ),
    );
  }
}
