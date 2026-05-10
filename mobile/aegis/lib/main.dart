import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'theme.dart';
import 'models/vest_data_model.dart';
import 'navigation/app_routes.dart';
import 'services/api_config.dart';
import 'services/vest_stream_service.dart';
import 'services/auth_service.dart';
import 'services/local_cache_service.dart';
import 'services/edge_anomaly_service.dart';
import 'services/sync_queue_service.dart';
import 'services/snapshot_uploader.dart';
import 'services/ai_assessment_repository.dart';
import 'services/patient_profile_service.dart';
import 'ble/ble_connection_supervisor.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // ── Load persisted user preferences before anything reads them ────
  // - Backend URL override (Settings → Connection)
  // - Reduced-motion + high-contrast + large-tap-target (Settings →
  //   Accessibility) — mirrored to the theme module statics so the
  //   M3 theme factory + transition builders pick them up immediately.
  await _restorePreferences();

  final auth = AuthService();
  await auth.load();

  // Patient profile (display name, MRN, clinical notes) — kept in
  // memory so agent calls can attach it to /api/agent/* request bodies
  // without an async secure-storage read on the hot path.
  final patientProfile = PatientProfileService();
  await patientProfile.load();

  final vestDataModel = VestDataModel();
  // Phase 4 IoMT services — wired into the stream service so each
  // incoming snapshot is cached, scored for edge anomalies, and queued
  // for sync if we're offline. Drop-in: existing UI sees no behaviour
  // change unless it explicitly subscribes to one of these notifiers.
  final localCache = LocalCacheService();
  final edgeAnomaly = EdgeAnomalyService();
  final syncQueue = SyncQueueService();

  // BLE supervisor — owns the vest + abdomen device services. The
  // Sensors screen drives manual scan / connect through it; the
  // BleTelemetrySource subscribes to its event streams for snapshots.
  final bleSupervisor = BleConnectionSupervisor();

  final vestStreamService = VestStreamService(
    model: vestDataModel,
    auth: auth,
    cache: localCache,
    anomaly: edgeAnomaly,
    syncQueue: syncQueue,
    supervisor: bleSupervisor,
  );
  // Start the background stream connection immediately. On mobile this
  // boots the BleConnectionSupervisor (scans + connects to vest +
  // abdomen). On web it falls back to the FastAPI /stream SSE endpoint.
  vestStreamService.startStream();

  // Push the mobile-built snapshot to the backend every 15 s so the
  // agent loop / FHIR exports / alerts evaluator have continuous data.
  // No-ops on web — the backend is the BLE master in the web build.
  final snapshotUploader = SnapshotUploader(
    stream: vestStreamService,
    auth: auth,
  );
  snapshotUploader.start();

  // Per-specialty AI assessment cache. AiAssessmentCard widgets (one
  // per specialist screen) read from this; the repository debounces
  // re-fetches based on telemetry drift so we don't burn Groq tokens
  // on every tab switch.
  final aiRepo = AiAssessmentRepository(
    stream: vestStreamService,
    auth: auth,
    profile: patientProfile,
  );

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: auth),
        ChangeNotifierProvider.value(value: patientProfile),
        ChangeNotifierProvider.value(value: vestDataModel),
        Provider.value(value: vestStreamService),
        Provider.value(value: snapshotUploader),
        ChangeNotifierProvider.value(value: localCache),
        ChangeNotifierProvider.value(value: edgeAnomaly),
        ChangeNotifierProvider.value(value: syncQueue),
        // BLE supervisor — exposed so SensorsScreen can call
        // supervisor.vest.startScan() / connectTo() / disconnect().
        ChangeNotifierProvider.value(value: bleSupervisor),
        // AI assessment repository — backs AiAssessmentCard.
        ChangeNotifierProvider.value(value: aiRepo),
      ],
      child: const AegisApp(),
    ),
  );
}

class AegisApp extends StatefulWidget {
  const AegisApp({super.key});

  @override
  State<AegisApp> createState() => _AegisAppState();
}

class _AegisAppState extends State<AegisApp> {
  /// Built once and held for the lifetime of the app. GoRouter keeps
  /// internal state (current route, navigator stacks per branch) so we
  /// must not rebuild it on hot-reload — `late final` + a single
  /// initialiser does the right thing.
  ///
  /// Wired with the AuthService from the provider tree so the router's
  /// redirect callback can bounce unauthenticated users to /login and
  /// rebuild whenever the token changes (login → push to /, logout →
  /// pop back to /login).
  late final GoRouter _router = buildAppRouter(context.read<AuthService>());

  @override
  void dispose() {
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'MedVerse IoT Clinical Dashboard',
      debugShowCheckedModeBanner: false,
      theme: MedVerseTheme.darkTheme,
      // Router-driven navigation:
      //   - `appRouter` defines the StatefulShellRoute with five
      //     branches (Dashboard / Specialists / 3D Twin / Chat /
      //     Settings) all hosted by AppShell + its M3 NavigationBar,
      //     plus a /login leaf outside the shell.
      //   - PermissionGate wraps the shell builder inside the router
      //     config so first-run BLE permissions are still requested
      //     once, before any sub-route mounts the BLE service.
      //   - Auth gate: the router's redirect callback bounces
      //     unauthenticated users to /login. When MEDVERSE_AUTH_ENABLED
      //     is off on Render, /api/auth/login still issues a token, so
      //     login still works — and an existing token from secure
      //     storage skips the gate entirely.
      routerConfig: _router,
    );
  }
}

/// Restores user-set preferences from secure storage on cold start.
///
/// Each preference is mirrored to a static field on the theme / API
/// modules so widgets reading them on first frame see the saved state
/// immediately (no Provider plumbing needed for these primitives).
///
/// Failures here are non-fatal — secure storage may be unavailable on
/// fresh installs / emulator quirks, in which case the defaults stand.
Future<void> _restorePreferences() async {
  const storage = FlutterSecureStorage();
  try {
    final url = await storage.read(key: 'aegis.backend_url_override');
    if (url != null && url.trim().isNotEmpty) {
      ApiConfig.setOverride(url.trim());
    }
    final aiUrl = await storage.read(key: 'aegis.ai_url_override');
    if (aiUrl != null && aiUrl.trim().isNotEmpty) {
      ApiConfig.setAiOverride(aiUrl.trim());
    }
  } catch (_) {/* non-fatal */}
  try {
    MedverseMotion.reducedMotionOverride =
        (await storage.read(key: 'aegis.a11y.reduced_motion')) == 'true';
    MedverseA11y.highContrastOverride =
        (await storage.read(key: 'aegis.a11y.high_contrast')) == 'true';
    final largeTaps =
        (await storage.read(key: 'aegis.a11y.large_taps')) == 'true';
    MedverseA11y.minTapTarget = largeTaps ? 56.0 : 48.0;
  } catch (_) {/* non-fatal */}
}
