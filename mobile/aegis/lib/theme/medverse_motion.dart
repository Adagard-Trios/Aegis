import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Material 3 motion tokens — durations + easings + reduced-motion gate.
///
/// Reference: https://m3.material.io/styles/motion/easing-and-duration/tokens-specs
///
/// Use these instead of hard-coded `Duration` / `Curves` values in any
/// new animation. Calling [MedverseMotion.standard(context)] returns
/// [Duration.zero] when the user (or system) has reduced-motion enabled,
/// so transitions become instant rather than slow.
class MedverseMotion {
  MedverseMotion._();

  // ── Durations (M3 spec) ────────────────────────────────────────────
  static const Duration shortDuration = Duration(milliseconds: 100);
  static const Duration mediumDuration = Duration(milliseconds: 250);
  static const Duration standardDuration = Duration(milliseconds: 300);
  static const Duration emphasizedDuration = Duration(milliseconds: 500);

  // ── Easings (M3 spec) ──────────────────────────────────────────────
  /// Most-used decelerating curve — outgoing items fade-out faster than
  /// incoming items fade-in for a clear hand-off.
  static const Curve emphasizedDecelerate = Cubic(0.05, 0.7, 0.1, 1.0);
  static const Curve emphasizedAccelerate = Cubic(0.3, 0.0, 0.8, 0.15);
  static const Curve emphasized = Cubic(0.2, 0.0, 0.0, 1.0);
  static const Curve standard = Cubic(0.2, 0.0, 0.0, 1.0);
  static const Curve standardDecelerate = Cubic(0.0, 0.0, 0.0, 1.0);
  static const Curve standardAccelerate = Cubic(0.3, 0.0, 1.0, 1.0);

  // ── Context-aware duration accessors ───────────────────────────────
  // Each one collapses to Duration.zero when reduced-motion is on so
  // the same call site works for all users.

  static Duration short(BuildContext context) => _gate(context, shortDuration);
  static Duration medium(BuildContext context) => _gate(context, mediumDuration);
  static Duration sStandard(BuildContext context) => _gate(context, standardDuration);
  static Duration emphasizedDur(BuildContext context) => _gate(context, emphasizedDuration);

  /// Returns true when the current user / device prefers reduced motion.
  /// Combines the system flag (MediaQuery.disableAnimations) with our
  /// in-app override stored in flutter_secure_storage. Looking up the
  /// in-app override needs an async read, so we cache it via the
  /// [reducedMotionOverride] static — the AccessibilitySettingsScreen
  /// flips this on save.
  static bool prefersReduced(BuildContext context) {
    if (reducedMotionOverride) return true;
    return MediaQuery.disableAnimationsOf(context);
  }

  /// Set by AccessibilitySettingsScreen on app start (read from secure
  /// storage). Defaults to false. Public so the screen can flip it.
  static bool reducedMotionOverride = false;

  static Duration _gate(BuildContext context, Duration d) {
    return prefersReduced(context) ? Duration.zero : d;
  }

  /// GoRouter helper — wraps the given child in a `CustomTransitionPage`
  /// that fades-through with M3 timing. Use this for sub-route pushes
  /// (e.g. Specialists card → Cardiology). Top-level bottom-nav tab
  /// swaps should use `NoTransitionPage` instead, per M3 NavigationBar
  /// guidance (siblings don't animate against each other).
  ///
  /// Honours reduced-motion: when enabled, durations collapse to zero,
  /// effectively giving you NoTransitionPage behaviour.
  static Page<T> fadePage<T>({required Widget child, LocalKey? key}) {
    return _MotionPage<T>(child: child, key: key);
  }

  /// Build a fade-through page transition (Material 3 sibling-of-sibling
  /// navigation pattern). The outgoing route fades + scales out; the
  /// incoming route fades + scales in. Standard 300 ms.
  static Widget fadeThroughBuilder(
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondary,
    Widget child,
  ) {
    final t = CurvedAnimation(parent: animation, curve: standard);
    final tOut = CurvedAnimation(parent: secondary, curve: standard);
    return FadeTransition(
      opacity: Tween<double>(begin: 0.0, end: 1.0).animate(t),
      child: FadeTransition(
        opacity: Tween<double>(begin: 1.0, end: 0.0).animate(tOut),
        child: ScaleTransition(
          scale: Tween<double>(begin: 0.92, end: 1.0).animate(t),
          child: child,
        ),
      ),
    );
  }

  /// Shared-axis horizontal transition — used between bottom-nav siblings.
  /// Matches Material 3 motion guideline for parallel-but-related routes.
  static Widget sharedAxisHorizontalBuilder(
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondary,
    Widget child,
  ) {
    final inFromRight = Tween<Offset>(
      begin: const Offset(0.3, 0),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: animation, curve: standard));
    final outLeft = Tween<Offset>(
      begin: Offset.zero,
      end: const Offset(-0.3, 0),
    ).animate(CurvedAnimation(parent: secondary, curve: standard));
    return SlideTransition(
      position: outLeft,
      child: SlideTransition(
        position: inFromRight,
        child: FadeTransition(opacity: animation, child: child),
      ),
    );
  }
}

/// CustomTransitionPage subclass that uses [MedverseMotion.fadeThroughBuilder]
/// and respects the reduced-motion override. Acts like NoTransitionPage
/// when reduced-motion is on.
///
/// Internal — callers should use [MedverseMotion.fadePage] which
/// returns this with the right defaults.
class _MotionPage<T> extends CustomTransitionPage<T> {
  const _MotionPage({required super.child, super.key})
      : super(
          transitionDuration: MedverseMotion.standardDuration,
          reverseTransitionDuration: MedverseMotion.shortDuration,
          transitionsBuilder: _build,
        );

  static Widget _build(
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondary,
    Widget child,
  ) {
    if (MedverseMotion.prefersReduced(context)) return child;
    return MedverseMotion.fadeThroughBuilder(context, animation, secondary, child);
  }
}
