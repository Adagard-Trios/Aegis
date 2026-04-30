import 'package:flutter/foundation.dart';
import 'dart:io' show Platform;

/// Central backend URL resolver — kept platform-aware (Android emulator
/// maps host `localhost` → `10.0.2.2`) and overridable via a persisted
/// preference when the mobile app is later pointed at a remote backend.
class ApiConfig {
  static String? _override;
  static String? _frontendOverride;

  /// Seed overrides at startup from secure storage / user preference.
  static void setOverride(String? url) {
    _override = (url == null || url.trim().isEmpty) ? null : url.trim();
  }

  static void setFrontendOverride(String? url) {
    _frontendOverride = (url == null || url.trim().isEmpty) ? null : url.trim();
  }

  /// MedVerse backend (FastAPI) — :8000 by default.
  static String get baseUrl {
    if (_override != null) return _override!;
    if (kIsWeb) return 'http://localhost:8000';
    try {
      if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    } catch (_) {}
    return 'http://localhost:8000';
  }

  /// Next.js dashboard (used by the embedded WebView 3D viewer) — :3000.
  static String get frontendUrl {
    if (_frontendOverride != null) return _frontendOverride!;
    if (kIsWeb) return 'http://localhost:3000';
    try {
      if (Platform.isAndroid) return 'http://10.0.2.2:3000';
    } catch (_) {}
    return 'http://localhost:3000';
  }
}
