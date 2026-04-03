import 'dart:io';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:image_picker/image_picker.dart';

import '../models/vest_data_model.dart';
import '../widgets/biometric_card.dart';
import '../widgets/interpretation_card.dart';
import '../theme.dart';

class EnvironmentScreen extends StatefulWidget {
  const EnvironmentScreen({super.key});

  @override
  State<EnvironmentScreen> createState() => _EnvironmentScreenState();
}

class _EnvironmentScreenState extends State<EnvironmentScreen> {
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

  Future<void> _sendToAgent() async {
    setState(() => _isUploading = true);
    // TODO: Implement actual upload to backend logic here
    await Future.delayed(const Duration(seconds: 2));
    setState(() => _isUploading = false);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Skin symptom image sent to Dermatology Agent for analysis.')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final model = context.watch<VestDataModel>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        children: [
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.0,
            children: [
              BiometricCard(title: 'CORE TEMP', value: model.temperature.toStringAsFixed(1), unit: '°C', statusColor: AegisTheme.statusWarning),
              BiometricCard(title: 'AMBIENT', value: model.ambientTemp.toStringAsFixed(1), unit: '°C', statusColor: AegisTheme.primary),
              BiometricCard(title: 'HUMIDITY', value: model.humidity.toStringAsFixed(0), unit: '%', statusColor: AegisTheme.primary),
              BiometricCard(title: 'PRESSURE', value: model.pressure.toStringAsFixed(0), unit: 'hPa', statusColor: AegisTheme.textMuted),
              BiometricCard(title: 'SKIN (LEFT)', value: model.skinTempLeft.toStringAsFixed(1), unit: '°C', statusColor: AegisTheme.statusWarning),
              BiometricCard(title: 'SKIN (RIGHT)', value: model.skinTempRight.toStringAsFixed(1), unit: '°C', statusColor: AegisTheme.statusWarning),
            ],
          ),
          const SizedBox(height: 24),
          
          // --- CAMERA INTEGRATION SECTION ---
          _buildCameraSection(),
          const SizedBox(height: 24),

          const Text('LATEST A.I. ANALYSIS', style: TextStyle(color: AegisTheme.textMuted, fontSize: 12, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
          const SizedBox(height: 12),
          const InterpretationCard(
            title: "Dermatology & Environment",
            icon: Icons.thermostat_rounded,
            content: "**Observations:**\n- **Core Temp**: Nominal at 36.6°C.\n- **Skin Thermals**: Symmetrical heat distribution across left and right thoracic nodes.\n- **Ambient Environment**: Controlled room temperature.\n\n**Conclusion**:\nThermoregulation is fully active and preventing hypothermia. No hyperthermic focal points that would indicate localized inflammation.",
          ),
        ],
      ),
    );
  }

  Widget _buildCameraSection() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AegisTheme.surfaceHighlight.withOpacity(0.3),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AegisTheme.primary.withOpacity(0.2)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Row(
            children: [
              Icon(Icons.camera_alt_rounded, color: AegisTheme.primary, size: 20),
              SizedBox(width: 8),
              Text('Skin Symptom Capture', style: TextStyle(color: AegisTheme.textMain, fontWeight: FontWeight.bold, fontSize: 16)),
            ],
          ),
          const SizedBox(height: 16),
          if (_imageFile == null)
            ElevatedButton.icon(
              onPressed: _pickImage,
              icon: const Icon(Icons.add_a_photo_rounded),
              label: const Text('Capture Skin Symptom'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AegisTheme.primary,
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
                          foregroundColor: AegisTheme.textMuted,
                          side: const BorderSide(color: AegisTheme.textMuted),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: _isUploading ? null : _sendToAgent,
                        icon: _isUploading 
                          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Icon(Icons.send_rounded),
                        label: Text(_isUploading ? 'Sending...' : 'Send to Agent'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.green.shade600,
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
