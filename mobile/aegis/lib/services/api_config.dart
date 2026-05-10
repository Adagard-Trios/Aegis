import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';

/// Central backend URL resolver.
///
/// Resolution priority (highest first):
///   1. **User override** persisted via Settings → Backend connection
///      (writes to flutter_secure_storage and into [setOverride]).
///   2. **Build-time --dart-define overrides**:
///        flutter run --dart-define=BACKEND_URL=http://192.168.1.42:8000
///        flutter run --dart-define=USE_LOCAL_BACKEND=true
///   3. **Production default** — the live Render deployment at
///      `https://medverse-api.onrender.com`. Every release build ships
///      pointing here so the app works out-of-the-box without any
///      manual setup.
///   4. **Local-dev defaults** when [USE_LOCAL_BACKEND] is true:
///      `10.0.2.2:8000` on the Android emulator, `localhost:8000`
///      everywhere else.
class ApiConfig {
  static String? _override;
  static String? _frontendOverride;
  static String? _aiOverride;

  /// Live backend on Render. Used as the default for every build
  /// unless the user overrides via Settings or a `--dart-define`.
  static const String _renderBaseUrl = 'https://medverse-api.onrender.com';

  /// AI service on Hugging Face Spaces — handles `/api/agent/*` because
  /// LangGraph + LangChain doesn't fit in Render's 512 MB free tier.
  /// Source for this deployment lives at services/medverse-ai/. Replace
  /// with your own Space URL if you fork.
  static const String _hfSpacesAiUrl =
      'https://nivakaran-medverse.hf.space';

  /// Build-time switch — pass `--dart-define=USE_LOCAL_BACKEND=true`
  /// when developing against a local FastAPI process, or
  /// `--dart-define=BACKEND_URL=http://X.Y.Z.W:8000` for an explicit
  /// LAN address (phone-on-LAN testing).
  static const bool _useLocalBackend =
      bool.fromEnvironment('USE_LOCAL_BACKEND', defaultValue: false);
  static const String _backendUrlOverride =
      String.fromEnvironment('BACKEND_URL', defaultValue: '');
  static const String _aiUrlOverride =
      String.fromEnvironment('AI_URL', defaultValue: '');

  /// Seed override at startup from secure storage / Settings UI.
  static void setOverride(String? url) {
    _override = (url == null || url.trim().isEmpty) ? null : url.trim();
  }

  static void setFrontendOverride(String? url) {
    _frontendOverride = (url == null || url.trim().isEmpty) ? null : url.trim();
  }

  /// Override the AI service URL at runtime (Settings → Backend connection).
  static void setAiOverride(String? url) {
    _aiOverride = (url == null || url.trim().isEmpty) ? null : url.trim();
  }

  /// MedVerse backend URL — see resolution priority on [ApiConfig].
  static String get baseUrl {
    // 1. Runtime override (Settings → Backend connection)
    if (_override != null) return _override!;
    // 2. Build-time override
    if (_backendUrlOverride.isNotEmpty) return _backendUrlOverride;
    // 4. Local-dev defaults (only when explicitly opted in)
    if (_useLocalBackend) return _localBackendUrl;
    // 3. Production default — Render
    return _renderBaseUrl;
  }

  /// AI service URL for `/api/agent/*` calls. Defaults to the HF Space
  /// because Render free tier OOMs on LangGraph. Resolution priority:
  ///   1. Runtime override (Settings → Backend connection → AI URL)
  ///   2. Build-time --dart-define=AI_URL=...
  ///   3. When USE_LOCAL_BACKEND=true: same host as [baseUrl]
  ///      (assumes you've started both services locally)
  ///   4. Production default — the bundled HF Spaces deployment
  static String get aiBaseUrl {
    if (_aiOverride != null) return _aiOverride!;
    if (_aiUrlOverride.isNotEmpty) return _aiUrlOverride;
    if (_useLocalBackend) return baseUrl;
    return _hfSpacesAiUrl;
  }

  static String get _localBackendUrl {
    if (kIsWeb) return 'http://localhost:8000';
    try {
      if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    } catch (_) {/* desktop / non-platform */}
    return 'http://localhost:8000';
  }

  /// Next.js dashboard (used by the embedded WebView 3D viewer fallback,
  /// not the bundled GLB). Defaults to localhost — there's no public
  /// frontend deployment to point at yet.
  static String get frontendUrl {
    if (_frontendOverride != null) return _frontendOverride!;
    if (kIsWeb) return 'http://localhost:3000';
    try {
      if (Platform.isAndroid) return 'http://10.0.2.2:3000';
    } catch (_) {/* desktop / non-platform */}
    return 'http://localhost:3000';
  }
}
