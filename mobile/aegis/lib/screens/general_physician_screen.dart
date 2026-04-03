import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';

import '../models/vest_data_model.dart';
import '../widgets/system_summary.dart';
import '../theme.dart';

class GeneralPhysicianScreen extends StatefulWidget {
  const GeneralPhysicianScreen({super.key});

  @override
  State<GeneralPhysicianScreen> createState() => _GeneralPhysicianScreenState();
}

class _GeneralPhysicianScreenState extends State<GeneralPhysicianScreen> {
  XFile? _imageFile;
  final ImagePicker _picker = ImagePicker();
  bool _isUploading = false;

  Future<void> _pickImage() async {
    try {
      final XFile? pickedFile = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 85,
      );
      if (pickedFile != null) {
        setState(() {
          _imageFile = pickedFile;
        });
      }
    } catch (e) {
      debugPrint("Error picking image: $e");
    }
  }

  Future<void> _sendToApexAgent() async {
    setState(() => _isUploading = true);
    // TODO: Implement actual upload to backend logic here
    await Future.delayed(const Duration(seconds: 2));
    setState(() => _isUploading = false);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Visual evidence sent to Apex Synthesizer for holistic review.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    context.watch<VestDataModel>(); // Watch model to trigger updates if necessary

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SystemSummary(),
          const SizedBox(height: 24),

          // --- CAMERA INTEGRATION SECTION ---
          _buildCameraSection(),
          const SizedBox(height: 24),

          const Text(
            'LATEST TRIAGE REPORT',
            style: TextStyle(color: MedVerseTheme.textMuted, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.5),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16.0),
            decoration: BoxDecoration(
              color: MedVerseTheme.surfaceHighlight.withOpacity(0.5),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: MedVerseTheme.primary.withOpacity(0.3)),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.check_circle_rounded, color: MedVerseTheme.primary, size: 20),
                    SizedBox(width: 8),
                    Text('Stable Status', style: TextStyle(color: MedVerseTheme.primary, fontWeight: FontWeight.bold, fontSize: 16)),
                  ],
                ),
                SizedBox(height: 12),
                Text(
                  "The patient's continuous 10Hz telemetry indicates nominal cardiovascular baseline operation. The Respiratory rhythms exhibit steady pneumography, and SpO2 is holding identically at nominal levels.\n\nNo immediate physical interventions or specialized triages are required at this very second.",
                  style: TextStyle(color: MedVerseTheme.textMain, height: 1.5),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCameraSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: MedVerseTheme.surfaceHighlight.withOpacity(0.3),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: MedVerseTheme.primary.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Row(
            children: [
              Icon(Icons.camera_alt_rounded, color: MedVerseTheme.primary, size: 20),
              SizedBox(width: 8),
              Text('Capture Evidence', style: TextStyle(color: MedVerseTheme.textMain, fontWeight: FontWeight.bold, fontSize: 16)),
            ],
          ),
          const SizedBox(height: 16),
          if (_imageFile == null)
            ElevatedButton.icon(
              onPressed: _pickImage,
              icon: const Icon(Icons.add_a_photo_rounded),
              label: const Text('Capture Frontal Symptom'),
              style: ElevatedButton.styleFrom(
                backgroundColor: MedVerseTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            )
          else
            Column(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.file(
                    File(_imageFile!.path),
                    height: 200,
                    width: double.infinity,
                    fit: BoxFit.cover,
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _pickImage,
                        icon: const Icon(Icons.refresh_rounded),
                        label: const Text('Retake'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: MedVerseTheme.textMuted,
                          side: const BorderSide(color: MedVerseTheme.textMuted),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: _isUploading ? null : _sendToApexAgent,
                        icon: _isUploading 
                          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Icon(Icons.send_rounded),
                        label: Text(_isUploading ? 'Sending...' : 'Send to GPU'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blue.shade600,
                          foregroundColor: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
        ],
      ),
    );
  }
}
