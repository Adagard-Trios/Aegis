import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../ble/permission_gate.dart';
import '../theme/medverse_motion.dart';
import '../screens/cardiology_screen.dart';
import '../screens/chat_screen.dart';
import '../screens/dashboard_screen.dart';
import '../screens/dermatology_screen.dart';
import '../screens/digital_twin_screen.dart';
import '../screens/general_physician_screen.dart';
import '../screens/neurology_screen.dart';
import '../screens/obstetrics_screen.dart';
import '../screens/ocular_screen.dart';
import '../screens/respiratory_screen.dart';
import '../screens/sensors_screen.dart';
import '../screens/settings/about_screen.dart';
import '../screens/settings/accessibility_settings_screen.dart';
import '../screens/settings/backend_settings_screen.dart';
import '../screens/settings/profile_settings_screen.dart';
import '../screens/settings/settings_screen.dart';
import '../screens/specialists_screen.dart';
import 'app_shell.dart';

/// Top-level GoRouter configuration.
///
/// Architecture: a single `StatefulShellRoute.indexedStack` hosts the
/// five top-level branches (Dashboard / Specialists / 3D Twin / Chat /
/// Settings). Each branch keeps its own navigator stack so that, e.g.,
/// drilling Specialists → Cardiology + then switching to Chat + then
/// back to Specialists restores the Cardiology screen — instead of
/// resetting the whole branch.
///
/// Sensors lives under `/settings/sensors` (a child of the Settings
/// branch) — this is the move from "own bottom-nav tab" to "Settings
/// sub-page" the redesign called for.
GoRouter buildAppRouter() {
  return GoRouter(
    initialLocation: '/',
    routes: [
      // Single shell hosting all five tabs. The PermissionGate wraps
      // the shell so first-run BLE permission requests still happen
      // before any sub-route mounts the BLE service.
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) {
          return PermissionGate(child: AppShell(shell: shell));
        },
        branches: [
          // ── Branch 0: Dashboard ──────────────────────────────────
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/',
                pageBuilder: (context, state) =>
                    const NoTransitionPage(child: _Wrapped(title: 'OVERVIEW', child: DashboardScreen())),
              ),
            ],
          ),

          // ── Branch 1: Specialists (with 7 specialty children) ────
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/specialists',
                pageBuilder: (context, state) => const NoTransitionPage(
                  child: _Wrapped(title: 'SPECIALISTS', child: _SpecialistsLanding()),
                ),
                // Sub-routes use MedverseMotion.fadePage so the
                // Specialists card → specialty detail push gets the
                // M3 fade-through transition (300 ms standard,
                // collapses to instant when reduced-motion is on).
                routes: [
                  GoRoute(
                    path: 'cardiology',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(title: 'CARDIOLOGY', child: CardiologyScreen()),
                    ),
                  ),
                  GoRoute(
                    path: 'respiratory',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(title: 'RESPIRATORY', child: RespiratoryScreen()),
                    ),
                  ),
                  GoRoute(
                    path: 'neurology',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(title: 'NEUROLOGY', child: NeurologyScreen()),
                    ),
                  ),
                  GoRoute(
                    path: 'obstetrics',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(title: 'OBSTETRICS', child: ObstetricsScreen()),
                    ),
                  ),
                  GoRoute(
                    path: 'dermatology',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(title: 'DERMATOLOGY', child: DermatologyScreen()),
                    ),
                  ),
                  GoRoute(
                    path: 'ocular',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(title: 'OCULAR', child: OcularScreen()),
                    ),
                  ),
                  GoRoute(
                    path: 'general-physician',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(
                        title: 'GENERAL PHYSICIAN',
                        child: GeneralPhysicianScreen(),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),

          // ── Branch 2: 3D Twin ────────────────────────────────────
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/twin',
                pageBuilder: (_, _) => const NoTransitionPage(
                  // DigitalTwinScreen owns its own Scaffold + AppBar
                  // (the FAB + status pill overlay full-screen), so
                  // we don't wrap it.
                  child: DigitalTwinScreen(),
                ),
              ),
            ],
          ),

          // ── Branch 3: Chat ───────────────────────────────────────
          // ChatScreen owns its own Scaffold + AppBar (it has the
          // persona picker + clear-conversation action), so we don't
          // double-wrap it in `_Wrapped`.
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/chat',
                pageBuilder: (_, _) => const NoTransitionPage(
                  child: ChatScreen(),
                ),
              ),
            ],
          ),

          // ── Branch 4: Settings hub + 5 sub-routes ────────────────
          // Sensors lives here (was its own bottom-nav tab pre-redesign).
          // Profile / backend / accessibility / about all wired to real
          // actions — no placeholders.
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/settings',
                pageBuilder: (_, _) => const NoTransitionPage(
                  child: _Wrapped(title: 'SETTINGS', child: SettingsScreen()),
                ),
                routes: [
                  GoRoute(
                    path: 'sensors',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      // SensorsScreen owns its own Scaffold + AppBar.
                      child: const SensorsScreen(),
                    ),
                  ),
                  GoRoute(
                    path: 'profile',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(
                          title: 'PATIENT PROFILE',
                          child: ProfileSettingsScreen()),
                    ),
                  ),
                  GoRoute(
                    path: 'backend',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(
                          title: 'BACKEND CONNECTION',
                          child: BackendSettingsScreen()),
                    ),
                  ),
                  GoRoute(
                    path: 'accessibility',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(
                          title: 'ACCESSIBILITY',
                          child: AccessibilitySettingsScreen()),
                    ),
                  ),
                  GoRoute(
                    path: 'about',
                    pageBuilder: (_, _) => MedverseMotion.fadePage(
                      child: const _Wrapped(title: 'ABOUT', child: AboutScreen()),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    ],
  );
}

/// Specialists landing — wraps the legacy [SpecialistsScreen] (which
/// expected an `onSelect(title, view)` callback) with a router-aware
/// shim so taps push the right named route instead of swapping local
/// state.
class _SpecialistsLanding extends StatelessWidget {
  const _SpecialistsLanding();

  @override
  Widget build(BuildContext context) {
    return SpecialistsScreen(
      onSelect: (title, _) {
        // Map the legacy uppercase title → router path. Stays in lock-
        // step with the order in [SpecialistsScreen._buildExpertCard]
        // calls; failing the lookup falls back to the listing.
        final path = switch (title) {
          'CARDIOLOGY' => '/specialists/cardiology',
          'RESPIRATORY' => '/specialists/respiratory',
          'NEUROLOGY' => '/specialists/neurology',
          'OBSTETRICS' => '/specialists/obstetrics',
          'DERMATOLOGY' => '/specialists/dermatology',
          'OCULAR' => '/specialists/ocular',
          'GENERAL PHYSICIAN' => '/specialists/general-physician',
          _ => '/specialists',
        };
        context.go(path);
      },
    );
  }
}

/// Shared M3 AppBar wrapper for screens that don't carry their own.
/// Placed here so swapping the chrome later is one edit, not seven.
class _Wrapped extends StatelessWidget {
  final String title;
  final Widget child;
  const _Wrapped({required this.title, required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(title),
        centerTitle: false,
      ),
      body: child,
    );
  }
}
