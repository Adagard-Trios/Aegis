import 'package:flutter/material.dart';

import '../theme.dart';
import 'cardiology_screen.dart';
import 'dermatology_screen.dart';
import 'general_physician_screen.dart';
import 'neurology_screen.dart';
import 'obstetrics_screen.dart';
import 'ocular_screen.dart';
import 'respiratory_screen.dart';

/// Specialists landing — adaptive grid of 7 specialty cards. Tap any
/// card to drill into the matching specialist screen (each one has a
/// live `AiAssessmentCard` auto-fetching against the current snapshot).
///
/// Column count adapts to width:
///   - ≥ 1100 dp → 4 cols (large tablet / desktop)
///   - ≥  800 dp → 3 cols (small tablet / foldable open)
///   - ≥  500 dp → 2 cols (most phones)
///   - <  500 dp → 1 col  (very small phones / split-screen)
///
/// Cards are full-bleed M3 `Card.filled` surfaces with a futuristic
/// linear-gradient overlay tinted by the per-specialty accent colour
/// (cyan / rose / amber / etc.) — the gradient sits at very low alpha
/// so it reads as a soft glow, not a colour wash.
class SpecialistsScreen extends StatelessWidget {
  final Function(String title, Widget view) onSelect;

  const SpecialistsScreen({super.key, required this.onSelect});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final w = constraints.maxWidth;
        final cols = w >= 1100 ? 4 : w >= 800 ? 3 : w >= 500 ? 2 : 1;
        return GridView.count(
          padding: const EdgeInsets.all(16),
          crossAxisCount: cols,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
          childAspectRatio: cols == 1 ? 2.4 : 1.0,
          children: [
            _ExpertCard(
              title: 'Cardiology',
              icon: Icons.monitor_heart_rounded,
              accent: MedVerseTheme.ecgColor,
              onTap: () => onSelect('CARDIOLOGY', const CardiologyScreen()),
            ),
            _ExpertCard(
              title: 'Respiratory',
              icon: Icons.air_rounded,
              accent: MedVerseTheme.rspColor,
              onTap: () => onSelect('RESPIRATORY', const RespiratoryScreen()),
            ),
            _ExpertCard(
              title: 'Neurology',
              icon: Icons.psychology_rounded,
              accent: MedVerseTheme.accent,
              onTap: () => onSelect('NEUROLOGY', const NeurologyScreen()),
            ),
            _ExpertCard(
              title: 'Obstetrics',
              icon: Icons.pregnant_woman_rounded,
              accent: MedVerseTheme.fhrColor,
              onTap: () => onSelect('OBSTETRICS', const ObstetricsScreen()),
            ),
            _ExpertCard(
              title: 'Dermatology',
              icon: Icons.healing_rounded,
              accent: MedVerseTheme.tempColor,
              onTap: () => onSelect('DERMATOLOGY', const DermatologyScreen()),
            ),
            _ExpertCard(
              title: 'Ocular',
              icon: Icons.visibility_outlined,
              accent: MedVerseTheme.spo2Color,
              onTap: () => onSelect('OCULAR', const OcularScreen()),
            ),
            _ExpertCard(
              title: 'Gen Physician',
              icon: Icons.medical_information_rounded,
              accent: MedVerseTheme.statusNormal,
              onTap: () =>
                  onSelect('GENERAL PHYSICIAN', const GeneralPhysicianScreen()),
            ),
          ],
        );
      },
    );
  }
}

class _ExpertCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color accent;
  final VoidCallback onTap;
  const _ExpertCard({
    required this.title,
    required this.icon,
    required this.accent,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      label: '$title specialist',
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                cs.surfaceContainerLow,
                accent.withValues(alpha: 0.16),
              ],
            ),
            border: Border.all(
              color: accent.withValues(alpha: 0.32),
              width: 1,
            ),
          ),
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: accent.withValues(alpha: 0.20),
                  boxShadow: [
                    BoxShadow(
                      color: accent.withValues(alpha: 0.3),
                      blurRadius: 14,
                      spreadRadius: 1,
                    ),
                  ],
                ),
                child: Icon(icon, color: accent, size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      'Live charts · AI assessment',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: cs.onSurfaceVariant,
                          ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right_rounded, color: cs.onSurfaceVariant),
            ],
          ),
        ),
      ),
    );
  }
}
