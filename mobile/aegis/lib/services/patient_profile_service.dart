import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// In-memory mirror of the patient-profile fields persisted by
/// [ProfileSettingsScreen] in `flutter_secure_storage`.
///
/// Loaded once at cold start (see `_restorePreferences` in main.dart).
/// Refreshed when the profile screen calls [save]. Agent calls read
/// [patientId] + [agentPayload] without hitting secure storage on the
/// hot path.
class PatientProfileService extends ChangeNotifier {
  PatientProfileService();

  static const _patientIdKey = 'aegis.patient_id';
  static const _displayNameKey = 'aegis.display_name';
  static const _notesKey = 'aegis.patient_notes';
  static const _ageKey = 'aegis.patient_age';
  static const _sexKey = 'aegis.patient_sex';
  static const _gestKey = 'aegis.patient_gestational_age_weeks';

  final _storage = const FlutterSecureStorage();

  String _patientId = 'medverse-demo-patient';
  String _displayName = '';
  String _notes = '';
  // Demographics — the ML adapters in services/medverse-ai/src/ml/
  // (ecg_arrhythmia, cardiac_age, skin_disease, retinal_*) all read
  // `patient.age` + `patient.sex` from the snapshot. Without them, the
  // adapters' `_to_feature_row` returns nothing and the prediction
  // silently no-ops. Stored as nullable so an empty profile doesn't
  // shove placeholder zeros into the model.
  int? _age;
  String _sex = '';
  int? _gestationalAgeWeeks;

  String get patientId => _patientId;
  String get displayName => _displayName;
  String get notes => _notes;
  int? get age => _age;
  String get sex => _sex;
  int? get gestationalAgeWeeks => _gestationalAgeWeeks;

  /// Map shape sent in agent request bodies as `patient_profile`.
  /// Empty fields are omitted so the AI graph's
  /// `shared.get('patient_profile')` truthy check still no-ops cleanly
  /// when nothing's been entered.
  ///
  /// Demographics (age, sex, gestational_age_weeks) are also exposed
  /// here — the AI service splices them into
  /// `state['sensor_telemetry']['patient']` so the ML adapters that
  /// expect those exact keys can read them.
  Map<String, dynamic>? get agentPayload {
    final out = <String, dynamic>{};
    if (_displayName.isNotEmpty) out['display_name'] = _displayName;
    if (_notes.isNotEmpty) out['notes'] = _notes;
    if (_age != null) out['age'] = _age;
    if (_sex.isNotEmpty) out['sex'] = _sex;
    if (_gestationalAgeWeeks != null) out['gestational_age_weeks'] = _gestationalAgeWeeks;
    return out.isEmpty ? null : out;
  }

  /// Read all six keys from secure storage. Safe to call repeatedly.
  Future<void> load() async {
    try {
      _patientId = (await _storage.read(key: _patientIdKey)) ?? 'medverse-demo-patient';
      _displayName = (await _storage.read(key: _displayNameKey)) ?? '';
      _notes = (await _storage.read(key: _notesKey)) ?? '';
      final ageRaw = await _storage.read(key: _ageKey);
      _age = (ageRaw == null || ageRaw.isEmpty) ? null : int.tryParse(ageRaw);
      _sex = (await _storage.read(key: _sexKey)) ?? '';
      final gestRaw = await _storage.read(key: _gestKey);
      _gestationalAgeWeeks = (gestRaw == null || gestRaw.isEmpty) ? null : int.tryParse(gestRaw);
      notifyListeners();
    } catch (_) {/* secure storage failure is non-fatal — keep defaults */}
  }

  /// Persist new values + notify listeners. Called by ProfileSettingsScreen
  /// after the user taps Save.
  Future<void> save({
    required String patientId,
    required String displayName,
    required String notes,
    int? age,
    String sex = '',
    int? gestationalAgeWeeks,
  }) async {
    _patientId = patientId.trim().isEmpty ? 'medverse-demo-patient' : patientId.trim();
    _displayName = displayName.trim();
    _notes = notes.trim();
    _age = age;
    _sex = sex.trim();
    _gestationalAgeWeeks = gestationalAgeWeeks;
    try {
      await _storage.write(key: _patientIdKey, value: _patientId);
      await _storage.write(key: _displayNameKey, value: _displayName);
      await _storage.write(key: _notesKey, value: _notes);
      await _storage.write(key: _ageKey, value: _age?.toString() ?? '');
      await _storage.write(key: _sexKey, value: _sex);
      await _storage.write(key: _gestKey, value: _gestationalAgeWeeks?.toString() ?? '');
    } catch (_) {/* non-fatal */}
    notifyListeners();
  }
}
