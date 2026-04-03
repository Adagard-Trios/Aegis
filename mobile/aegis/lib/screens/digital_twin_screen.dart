import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../models/vest_data_model.dart';
import '../widgets/simulation_controls_panel.dart';
import '../widgets/biometric_card.dart';
import '../theme.dart';

class DigitalTwinScreen extends StatefulWidget {
  const DigitalTwinScreen({super.key});

  @override
  State<DigitalTwinScreen> createState() => _DigitalTwinScreenState();
}

class _DigitalTwinScreenState extends State<DigitalTwinScreen> {
  late final WebViewController _controller;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(MedVerseTheme.background)
      ..loadRequest(Uri.parse('http://10.0.2.2:3000/vest-viewer')); 
  }

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();
    
    return Scaffold(
      backgroundColor: MedVerseTheme.background,
      body: Stack(
        children: [
          // Full Screen Background 3D Twin
          Positioned.fill(
            child: WebViewWidget(controller: _controller),
          ),
          
          // Floating overlay toggle
          Positioned(
            right: 16,
            bottom: 16,
            child: FloatingActionButton.extended(
              backgroundColor: MedVerseTheme.primary,
              icon: const Icon(Icons.science, color: Colors.white),
              label: const Text('Simulate', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              onPressed: () {
                showModalBottomSheet(
                  context: context,
                  backgroundColor: Colors.transparent,
                  isScrollControlled: true,
                  builder: (context) => Container(
                    height: MediaQuery.of(context).size.height * 0.75,
                    padding: const EdgeInsets.only(top: 16, left: 16, right: 16),
                    decoration: BoxDecoration(
                      color: MedVerseTheme.background.withOpacity(0.95),
                      borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
                      boxShadow: const [BoxShadow(color: Colors.black45, blurRadius: 10)],
                    ),
                    child: SingleChildScrollView(
                      child: Column(
                        children: [
                          Container(width: 40, height: 5, margin: const EdgeInsets.only(bottom: 16), decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(10))),
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
                              BiometricCard(title: 'HEART RATE', value: model.heartRate.toString(), unit: 'bpm', statusColor: MedVerseTheme.ecgColor),
                              BiometricCard(title: 'SpO2', value: model.spO2.toString(), unit: '%', statusColor: MedVerseTheme.primary),
                              BiometricCard(title: 'FETAL KICKS', value: model.hasKicks ? 'ACTIVE' : 'NONE', unit: '', statusColor: model.hasKicks ? Colors.tealAccent : MedVerseTheme.textMuted),
                              BiometricCard(title: 'CONTRACTIONS', value: model.hasContractions ? 'TRUE' : 'FALSE', unit: '', statusColor: model.hasContractions ? MedVerseTheme.statusCritical : MedVerseTheme.textMuted),
                            ],
                          ),
                          const SizedBox(height: 40),
                        ],
                      ),
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
