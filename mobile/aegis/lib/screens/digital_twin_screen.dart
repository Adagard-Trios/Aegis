import 'package:flutter/material.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import 'package:provider/provider.dart';

import '../models/vest_data_model.dart';
import '../widgets/biometric_card.dart';
import '../widgets/simulation_controls_panel.dart';
import '../theme.dart';

/// 3D digital-twin viewer.
///
/// Renders the bundled `assets/models/human.glb` directly via
/// `model_viewer_plus` (Google's `<model-viewer>` web component embedded
/// in a platform WebView). The previous implementation tried to load the
/// frontend's /vest-viewer page in a WebView; that requires the dev
/// frontend to be reachable from the phone, which usually isn't the
/// case (Android can't reach the laptop's localhost; LAN access needs
/// firewall / IP juggling). Native asset loading removes that
/// dependency — the twin works offline.
class DigitalTwinScreen extends StatelessWidget {
  const DigitalTwinScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();

    return Scaffold(
      backgroundColor: MedVerseTheme.background,
      body: Stack(
        children: [
          // Full-screen 3D twin. Auto-rotate keeps the figure animated;
          // cameraControls lets the clinician orbit / pinch-zoom.
          Positioned.fill(
            child: ModelViewer(
              src: 'assets/models/human.glb',
              alt: 'Patient digital twin',
              ar: false,
              autoRotate: true,
              cameraControls: true,
              disableZoom: false,
              backgroundColor: MedVerseTheme.background,
              loading: Loading.eager,
              autoPlay: true,
            ),
          ),

          // Top-left: live status pill so users know the twin is bound
          // to live telemetry, not a static avatar.
          Positioned(
            top: 16,
            left: 16,
            child: _StatusPill(
              connected: model.isConnected,
              hr: model.heartRate,
              spo2: model.spO2,
            ),
          ),

          // Bottom-right: simulation controls.
          Positioned(
            right: 16,
            bottom: 16,
            child: FloatingActionButton.extended(
              backgroundColor: MedVerseTheme.primary,
              icon: const Icon(Icons.science, color: Colors.white),
              label: const Text(
                'Simulate',
                style: TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
              onPressed: () => _showSimulationSheet(context, model),
            ),
          ),
        ],
      ),
    );
  }

  void _showSimulationSheet(BuildContext context, VestDataModel model) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => Container(
        height: MediaQuery.of(context).size.height * 0.75,
        padding: const EdgeInsets.only(top: 16, left: 16, right: 16),
        decoration: BoxDecoration(
          color: MedVerseTheme.background.withValues(alpha: 0.95),
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          boxShadow: const [BoxShadow(color: Colors.black45, blurRadius: 10)],
        ),
        child: SingleChildScrollView(
          child: Column(
            children: [
              Container(
                width: 40,
                height: 5,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: Colors.white24,
                  borderRadius: BorderRadius.circular(10),
                ),
              ),
              const SimulationControlsPanel(),
              const SizedBox(height: 16),
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                childAspectRatio: 1.5,
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                children: [
                  BiometricCard(
                    title: 'HEART RATE',
                    value: model.heartRate > 0 ? model.heartRate.toString() : '—',
                    unit: 'bpm',
                    statusColor: MedVerseTheme.ecgColor,
                  ),
                  BiometricCard(
                    title: 'SpO2',
                    value: model.spO2 > 0 ? model.spO2.toString() : '—',
                    unit: '%',
                    statusColor: MedVerseTheme.primary,
                  ),
                  BiometricCard(
                    title: 'FETAL KICKS',
                    value: model.hasKicks ? 'ACTIVE' : 'NONE',
                    unit: '',
                    statusColor: model.hasKicks
                        ? Colors.tealAccent
                        : MedVerseTheme.textMuted,
                  ),
                  BiometricCard(
                    title: 'CONTRACTIONS',
                    value: model.hasContractions ? 'TRUE' : 'FALSE',
                    unit: '',
                    statusColor: model.hasContractions
                        ? MedVerseTheme.statusCritical
                        : MedVerseTheme.textMuted,
                  ),
                ],
              ),
              const SizedBox(height: 40),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  final bool connected;
  final int hr;
  final int spo2;

  const _StatusPill({
    required this.connected,
    required this.hr,
    required this.spo2,
  });

  @override
  Widget build(BuildContext context) {
    final color = connected
        ? MedVerseTheme.statusNormal
        : MedVerseTheme.textMuted;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: MedVerseTheme.surface.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 8),
          Text(
            connected
                ? 'LIVE  ·  HR ${hr > 0 ? hr : "—"}  ·  SpO₂ ${spo2 > 0 ? "$spo2%" : "—"}'
                : 'Twin idle — connect a sensor in Sensors',
            style: const TextStyle(
              color: MedVerseTheme.textMain,
              fontSize: 11,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.6,
            ),
          ),
        ],
      ),
    );
  }
}
