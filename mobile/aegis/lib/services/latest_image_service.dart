import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// In-memory cache of the most recently uploaded skin / retinal image
/// path per patient. Populated when the user uploads via
/// `POST /api/upload-image` (the response body includes the
/// `image_path` the backend stored). Surfaced through [agentPayload]
/// so every agent request body's `patient_profile.imaging` block
/// carries the latest paths — the AI service splices them into
/// `snapshot.imaging.{skin,retinal}.image_path` before invoking the
/// dermatology / ocular graphs, which feed the `skin_disease`,
/// `retinal_disease`, and `retinal_age` ML adapters.
///
/// Persisted to `flutter_secure_storage` so the most recent paths
/// survive app restarts (the backend keeps the file regardless; only
/// the path string needs to come back).
class LatestImageService extends ChangeNotifier {
  LatestImageService();

  static const _skinKey = 'aegis.latest_image.skin';
  static const _retinalKey = 'aegis.latest_image.retinal';

  final _storage = const FlutterSecureStorage();

  String _skinPath = '';
  String _retinalPath = '';

  String get skinPath => _skinPath;
  String get retinalPath => _retinalPath;

  /// Map shape merged into agent request bodies under
  /// `patient_profile.imaging`. The AI service walks this dict and
  /// splices each modality into `snapshot.imaging.<modality>.image_path`.
  Map<String, String>? get agentPayload {
    final out = <String, String>{};
    if (_skinPath.isNotEmpty) out['skin'] = _skinPath;
    if (_retinalPath.isNotEmpty) out['retinal'] = _retinalPath;
    return out.isEmpty ? null : out;
  }

  Future<void> load() async {
    try {
      _skinPath = (await _storage.read(key: _skinKey)) ?? '';
      _retinalPath = (await _storage.read(key: _retinalKey)) ?? '';
      notifyListeners();
    } catch (_) {/* secure storage failure is non-fatal */}
  }

  /// Call after a successful POST /api/upload-image. `modality`
  /// must match the backend's expected value (`skin` or `retinal`).
  Future<void> setLatest({required String modality, required String imagePath}) async {
    final mod = modality.trim().toLowerCase();
    if (imagePath.trim().isEmpty) return;
    if (mod == 'skin') {
      _skinPath = imagePath.trim();
      try { await _storage.write(key: _skinKey, value: _skinPath); } catch (_) {/**/}
    } else if (mod == 'retinal') {
      _retinalPath = imagePath.trim();
      try { await _storage.write(key: _retinalKey, value: _retinalPath); } catch (_) {/**/}
    } else {
      // Unknown modality — store under a custom key but don't expose
      // until the AI service knows about it.
      return;
    }
    notifyListeners();
  }

  /// Clear cached paths — useful when switching patient profiles.
  Future<void> clear() async {
    _skinPath = '';
    _retinalPath = '';
    try {
      await _storage.delete(key: _skinKey);
      await _storage.delete(key: _retinalKey);
    } catch (_) {/**/}
    notifyListeners();
  }
}
