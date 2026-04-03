import 'package:flutter/material.dart';
import '../theme.dart';
import 'cardiology_screen.dart';
import 'respiratory_screen.dart';
import 'neurology_screen.dart';
import 'obstetrics_screen.dart';
import 'general_physician_screen.dart';

class SpecialistsScreen extends StatelessWidget {
  final Function(String title, Widget view) onSelect;

  const SpecialistsScreen({super.key, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      padding: const EdgeInsets.all(16.0),
      crossAxisCount: 2,
      crossAxisSpacing: 16,
      mainAxisSpacing: 16,
      children: [
        _buildExpertCard(
          'Cardiology',
          Icons.monitor_heart_rounded,
          MedVerseTheme.ecgColor,
          () => onSelect('CARDIOLOGY', const CardiologyScreen()),
        ),
        _buildExpertCard(
          'Respiratory',
          Icons.air_rounded,
          MedVerseTheme.rspColor,
          () => onSelect('RESPIRATORY', const RespiratoryScreen()),
        ),
        _buildExpertCard(
          'Neurology',
          Icons.psychology_rounded,
          MedVerseTheme.accent,
          () => onSelect('NEUROLOGY', const NeurologyScreen()),
        ),
        _buildExpertCard(
          'Obstetrics',
          Icons.pregnant_woman_rounded,
          MedVerseTheme.fhrColor,
          () => onSelect('OBSTETRICS', const ObstetricsScreen()),
        ),
        _buildExpertCard(
          'Gen Physician',
          Icons.medical_information_rounded,
          MedVerseTheme.textMain,
          () => onSelect('GENERAL PHYSICIAN', const GeneralPhysicianScreen()),
        ),
      ],
    );
  }

  Widget _buildExpertCard(String title, IconData icon, Color color, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Card(
        color: MedVerseTheme.surfaceHighlight.withOpacity(0.5),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 48, color: color),
            const SizedBox(height: 16),
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
          ],
        ),
      ),
    );
  }
}
