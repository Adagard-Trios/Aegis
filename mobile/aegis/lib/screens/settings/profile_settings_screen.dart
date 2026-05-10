import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:provider/provider.dart';

import '../../services/ai_assessment_repository.dart';

/// Patient profile editor — backs the `patient_id` field every backend
/// call uses. Persists to `flutter_secure_storage` so it survives
/// restarts. Saving the form clears the AI assessment cache so a new
/// patient context doesn't see the previous patient's cached AI text.
class ProfileSettingsScreen extends StatefulWidget {
  const ProfileSettingsScreen({super.key});

  @override
  State<ProfileSettingsScreen> createState() => _ProfileSettingsScreenState();
}

class _ProfileSettingsScreenState extends State<ProfileSettingsScreen> {
  static const _patientIdKey = 'aegis.patient_id';
  static const _displayNameKey = 'aegis.display_name';
  static const _notesKey = 'aegis.patient_notes';
  final _storage = const FlutterSecureStorage();

  final _patientIdCtrl = TextEditingController();
  final _displayNameCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();

  bool _loading = true;
  bool _dirty = false;

  @override
  void initState() {
    super.initState();
    _restore();
    for (final c in [_patientIdCtrl, _displayNameCtrl, _notesCtrl]) {
      c.addListener(() {
        if (!_dirty) setState(() => _dirty = true);
      });
    }
  }

  Future<void> _restore() async {
    try {
      _patientIdCtrl.text = await _storage.read(key: _patientIdKey) ?? 'medverse-demo-patient';
      _displayNameCtrl.text = await _storage.read(key: _displayNameKey) ?? '';
      _notesCtrl.text = await _storage.read(key: _notesKey) ?? '';
    } catch (_) {/* secure storage failure is non-fatal */}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _save() async {
    try {
      await _storage.write(key: _patientIdKey, value: _patientIdCtrl.text.trim());
      await _storage.write(key: _displayNameKey, value: _displayNameCtrl.text.trim());
      await _storage.write(key: _notesKey, value: _notesCtrl.text.trim());
      // Patient changed → flush AI assessment cache so cached text from
      // the previous patient context doesn't leak.
      if (mounted) {
        context.read<AiAssessmentRepository>().clear();
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Profile saved')),
      );
      setState(() => _dirty = false);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Save failed: $e')),
      );
    }
  }

  @override
  void dispose() {
    _patientIdCtrl.dispose();
    _displayNameCtrl.dispose();
    _notesCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 16),
      children: [
        Text(
          'Identifies this patient on every backend call (snapshot ingest, '
          'agent ask, FHIR exports). Free-form — match the MRN your clinical '
          'system uses, or leave the demo default.',
          style: theme.textTheme.bodyMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 24),
        TextField(
          controller: _patientIdCtrl,
          decoration: const InputDecoration(
            labelText: 'Patient ID / MRN',
            hintText: 'medverse-demo-patient',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _displayNameCtrl,
          decoration: const InputDecoration(
            labelText: 'Display name (optional)',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _notesCtrl,
          minLines: 3,
          maxLines: 6,
          decoration: const InputDecoration(
            labelText: 'Notes (optional)',
            hintText: 'Conditions, allergies, ongoing meds…',
            border: OutlineInputBorder(),
            alignLabelWithHint: true,
          ),
        ),
        const SizedBox(height: 32),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                icon: const Icon(Icons.save_outlined),
                label: const Text('Save profile'),
                onPressed: _dirty ? _save : null,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
