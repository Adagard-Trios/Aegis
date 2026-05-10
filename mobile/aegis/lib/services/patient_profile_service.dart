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

  final _storage = const FlutterSecureStorage();

  String _patientId = 'medverse-demo-patient';
  String _displayName = '';
  String _notes = '';

  String get patientId => _patientId;
  String get displayName => _displayName;
  String get notes => _notes;

  /// Map shape sent in agent request bodies as `patient_profile`.
  /// Empty fields are omitted so the AI graph's
  /// `shared.get('patient_profile')` truthy check still no-ops cleanly
  /// when nothing's been entered.
  Map<String, dynamic>? get agentPayload {
    final out = <String, dynamic>{};
    if (_displayName.isNotEmpty) out['display_name'] = _displayName;
    if (_notes.isNotEmpty) out['notes'] = _notes;
    return out.isEmpty ? null : out;
  }

  /// Read all three keys from secure storage. Safe to call repeatedly.
  Future<void> load() async {
    try {
      _patientId = (await _storage.read(key: _patientIdKey)) ?? 'medverse-demo-patient';
      _displayName = (await _storage.read(key: _displayNameKey)) ?? '';
      _notes = (await _storage.read(key: _notesKey)) ?? '';
      notifyListeners();
    } catch (_) {/* secure storage failure is non-fatal — keep defaults */}
  }

  /// Persist new values + notify listeners. Called by ProfileSettingsScreen
  /// after the user taps Save.
  Future<void> save({
    required String patientId,
    required String displayName,
    required String notes,
  }) async {
    _patientId = patientId.trim().isEmpty ? 'medverse-demo-patient' : patientId.trim();
    _displayName = displayName.trim();
    _notes = notes.trim();
    try {
      await _storage.write(key: _patientIdKey, value: _patientId);
      await _storage.write(key: _displayNameKey, value: _displayName);
      await _storage.write(key: _notesKey, value: _notes);
    } catch (_) {/* non-fatal */}
    notifyListeners();
  }
}
