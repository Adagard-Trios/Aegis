import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';
import '../models/vest_data_model.dart';
import '../services/api_service.dart';
import '../theme.dart';

class SimulationControlsPanel extends StatefulWidget {
  const SimulationControlsPanel({super.key});

  @override
  State<SimulationControlsPanel> createState() => _SimulationControlsPanelState();
}

class _SimulationControlsPanelState extends State<SimulationControlsPanel> {
  String _selectedMode = 'Live';
  final List<String> _modes = ['Live', '6h', '12h', '24h', '2w', '4w'];

  Future<void> _changeMode(String mode) async {
    setState(() {
      _selectedMode = mode;
    });
    await ApiService.setSimulationMode(mode);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Simulation mode set to $mode', style: const TextStyle(color: Colors.white)), backgroundColor: MedVerseTheme.primary),
      );
    }
  }

  Future<void> _uploadLabResult() async {
    final ImagePicker picker = ImagePicker();
    final XFile? image = await picker.pickImage(source: ImageSource.gallery);
    
    if (image == null) return;
    
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Processing Labs via MedVerse OCR...')),
      );
    }
    
    final result = await ApiService.uploadLabResults(image.path);
    if (mounted) {
      if (result != null && result['status'] == 'success') {
        final extracted = result['extracted_data'];
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Extraction Complete: CYP2D6 is ${extracted['CYP2D6']}. Matrices updated.'),
            backgroundColor: MedVerseTheme.primary,
            duration: const Duration(seconds: 4),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to upload labs', style: TextStyle(color: Colors.white)), backgroundColor: MedVerseTheme.statusWarning),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Card(
          color: MedVerseTheme.surface,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'SIMULATION & LABS',
                  style: TextStyle(
                    color: MedVerseTheme.textMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 1.5,
                  ),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    const Text('Time:', style: TextStyle(color: MedVerseTheme.textMain, fontWeight: FontWeight.bold)),
                    const SizedBox(width: 8),
                    Expanded(
                      child: SingleChildScrollView(
                        scrollDirection: Axis.horizontal,
                        child: Row(
                          children: _modes.map((mode) {
                            final isSelected = mode == _selectedMode;
                            return Padding(
                              padding: const EdgeInsets.only(right: 8.0),
                              child: ChoiceChip(
                                label: Text(mode),
                                selected: isSelected,
                                selectedColor: MedVerseTheme.primary.withOpacity(0.2),
                                backgroundColor: MedVerseTheme.background,
                                labelStyle: TextStyle(
                                  color: isSelected ? MedVerseTheme.primary : MedVerseTheme.textMuted,
                                  fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                                ),
                                onSelected: (selected) {
                                  if (selected) _changeMode(mode);
                                },
                              ),
                            );
                          }).toList(),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: _uploadLabResult,
                    icon: const Icon(Icons.upload_file),
                    label: const Text('Patient Lab Results (PDF)'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: MedVerseTheme.background,
                      foregroundColor: MedVerseTheme.primary,
                      side: const BorderSide(color: MedVerseTheme.primary),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text('Medication Testing (In-Silico)', style: TextStyle(color: MedVerseTheme.textMain, fontWeight: FontWeight.bold, fontSize: 12)),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () async {
                          await ApiService.injectMedication('Labetalol', 100);
                          if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Simulating Labetalol 100mg')));
                        },
                        style: ElevatedButton.styleFrom(backgroundColor: MedVerseTheme.primary, foregroundColor: Colors.white),
                        child: const Text('Labetalol'),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: ElevatedButton(
                        onPressed: () async {
                          await ApiService.injectMedication('Oxytocin', 10);
                          if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Simulating Oxytocin 10U')));
                        },
                        style: ElevatedButton.styleFrom(backgroundColor: MedVerseTheme.accent, foregroundColor: Colors.white),
                        child: const Text('Oxytocin'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        if (model.activeMedication != null && model.activeMedication != 'null') ...[
          const SizedBox(height: 8),
          Card(
            color: MedVerseTheme.surface,
            shape: RoundedRectangleBorder(
              side: const BorderSide(color: MedVerseTheme.primary, width: 2),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.vaccines, color: MedVerseTheme.primary),
                      const SizedBox(width: 8),
                      const Text(
                        'ACTIVE REACTION',
                        style: TextStyle(
                          color: MedVerseTheme.primary,
                          fontSize: 12,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 1.5,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Medication: ${model.activeMedication}',
                    style: const TextStyle(color: MedVerseTheme.textMain, fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Clearance Profile: ${model.clearanceModel}',
                    style: const TextStyle(color: MedVerseTheme.statusWarning, fontSize: 14),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Simulated Time Elapsed: ${model.medSimTime.toStringAsFixed(1)}s',
                    style: const TextStyle(color: MedVerseTheme.textMuted, fontSize: 13),
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(8)),
                    child: Text(
                      model.activeMedication!.toLowerCase() == 'labetalol' 
                          ? 'Effect: Maternal Heart Rate forcefully suppressed across exponential decay curve (Scaled by ${model.clearanceModel == "Poor Metabolizer" ? "0.1k" : "0.2k"}).'
                          : 'Effect: Strong oxytocic action stimulating immediate uterine contractions and elevating maternal heart rate.',
                      style: const TextStyle(color: Colors.white70, fontStyle: FontStyle.italic, fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ],
    );
  }
}
