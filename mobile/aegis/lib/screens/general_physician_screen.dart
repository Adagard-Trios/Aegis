import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';

import '../models/vest_data_model.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../widgets/ai_assessment_card.dart';
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
    final file = _imageFile;
    if (file == null) return;
    setState(() => _isUploading = true);
    try {
      // Real backend: POST /api/upload-lab-results — multipart upload
      // that returns OCR-extracted patient data the agent loop picks
      // up on its next pass. Replaces the previous 2 s mock delay.
      final auth = context.read<AuthService>();
      final result = await ApiService.uploadLabResults(file.path, auth: auth);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            result == null
                ? 'Upload failed — check backend connection in Settings.'
                : 'Sent. Extracted: ${(result['extracted_data'] ?? {}).toString().substring(0, 60)}…',
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Upload failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _isUploading = false);
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

          // Live AI triage — fetches a holistic GP-perspective
          // assessment from `/api/agent/ask` against the current
          // telemetry snapshot. Replaces the previous static "Stable
          // Status" placeholder text.
          const AiAssessmentCard(specialty: 'general physician'),
        ],
      ),
    );
  }

  Widget _buildCameraSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: MedVerseTheme.surfaceHighlight.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: MedVerseTheme.primary.withValues(alpha: 0.2)),
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
