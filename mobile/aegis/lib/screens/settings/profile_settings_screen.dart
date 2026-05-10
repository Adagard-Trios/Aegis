import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show FilteringTextInputFormatter;
import 'package:provider/provider.dart';

import '../../services/ai_assessment_repository.dart';
import '../../services/patient_profile_service.dart';

/// Patient profile editor — backs the `patient_id` field every backend
/// call uses, plus the demographics (age / sex / gestational age) the
/// ML adapters in services/medverse-ai/src/ml/ read from
/// `state['sensor_telemetry']['patient']`. Persists to
/// `flutter_secure_storage` so it survives restarts. Saving the form
/// clears the AI assessment cache so a new patient context doesn't see
/// the previous patient's cached AI text.
class ProfileSettingsScreen extends StatefulWidget {
  const ProfileSettingsScreen({super.key});

  @override
  State<ProfileSettingsScreen> createState() => _ProfileSettingsScreenState();
}

class _ProfileSettingsScreenState extends State<ProfileSettingsScreen> {
  final _patientIdCtrl = TextEditingController();
  final _displayNameCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();
  final _ageCtrl = TextEditingController();
  final _gestCtrl = TextEditingController();
  String? _sex;

  bool _loading = true;
  bool _dirty = false;

  static const _sexOptions = <String>['', 'female', 'male', 'other'];

  @override
  void initState() {
    super.initState();
    _restore();
    for (final c in [_patientIdCtrl, _displayNameCtrl, _notesCtrl, _ageCtrl, _gestCtrl]) {
      c.addListener(() {
        if (!_dirty) setState(() => _dirty = true);
      });
    }
  }

  Future<void> _restore() async {
    final profile = context.read<PatientProfileService>();
    await profile.load();
    _patientIdCtrl.text = profile.patientId;
    _displayNameCtrl.text = profile.displayName;
    _notesCtrl.text = profile.notes;
    _ageCtrl.text = profile.age?.toString() ?? '';
    _sex = profile.sex.isEmpty ? '' : profile.sex;
    _gestCtrl.text = profile.gestationalAgeWeeks?.toString() ?? '';
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _save() async {
    try {
      final ageText = _ageCtrl.text.trim();
      final gestText = _gestCtrl.text.trim();
      await context.read<PatientProfileService>().save(
            patientId: _patientIdCtrl.text,
            displayName: _displayNameCtrl.text,
            notes: _notesCtrl.text,
            age: ageText.isEmpty ? null : int.tryParse(ageText),
            sex: _sex ?? '',
            gestationalAgeWeeks: gestText.isEmpty ? null : int.tryParse(gestText),
          );
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
    _ageCtrl.dispose();
    _gestCtrl.dispose();
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
        const SizedBox(height: 24),
        // ── Demographics — feed the ML adapters that need them ──────
        Text(
          'Demographics',
          style: theme.textTheme.titleSmall?.copyWith(
            fontWeight: FontWeight.w700,
            color: theme.colorScheme.primary,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          'Age + sex feed the cardiology / dermatology / ocular ML adapters. '
          'Gestational age (in weeks) is only used by the obstetrics adapters.',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _ageCtrl,
                keyboardType: TextInputType.number,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(
                  labelText: 'Age (years)',
                  border: OutlineInputBorder(),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: DropdownButtonFormField<String>(
                initialValue: _sexOptions.contains(_sex) ? _sex : '',
                decoration: const InputDecoration(
                  labelText: 'Sex',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: '', child: Text('—')),
                  DropdownMenuItem(value: 'female', child: Text('Female')),
                  DropdownMenuItem(value: 'male', child: Text('Male')),
                  DropdownMenuItem(value: 'other', child: Text('Other')),
                ],
                onChanged: (v) {
                  setState(() {
                    _sex = v ?? '';
                    _dirty = true;
                  });
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _gestCtrl,
          keyboardType: TextInputType.number,
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          decoration: const InputDecoration(
            labelText: 'Gestational age (weeks, OB only)',
            hintText: 'Leave blank if not pregnant',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 24),
        TextField(
          controller: _notesCtrl,
          minLines: 3,
          maxLines: 6,
          decoration: const InputDecoration(
            labelText: 'Notes (conditions, allergies, ongoing meds)',
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
