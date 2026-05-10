import 'package:flutter/material.dart';

import 'theme/medverse_a11y.dart';
import 'theme/medverse_theme.dart';

// Re-export the new M3 modules so a single import covers the
// transition surface for callers that want them.
export 'theme/medverse_theme.dart';
export 'theme/medverse_typography.dart';
export 'theme/medverse_motion.dart';
export 'theme/medverse_a11y.dart';

/// Legacy `MedVerseTheme` class — every existing widget across the app
/// reads its colour constants directly. We're migrating to
/// `Theme.of(context).colorScheme.<token>` lookups screen-by-screen,
/// so this class stays alive as a compatibility shim during the
/// rollout. Each constant resolves to a sensible value that matches
/// the new Material 3 dark scheme.
///
/// New code should prefer:
///   - `Theme.of(context).colorScheme.primary` over `MedVerseTheme.primary`
///   - `Theme.of(context).colorScheme.surface` over `MedVerseTheme.surface`
///   - `Theme.of(context).colorScheme.error` over `MedVerseTheme.statusCritical`
///
/// …because those track the live theme (light/dark, high-contrast, etc.).
class MedVerseTheme {
  // ── Brand palette ──────────────────────────────────────────────────
  // Aliased to the M3 seed-derived tones so existing widgets render
  // in M3 colours without code changes.
  static const Color background = Color(0xFF020617); // slate-950
  static const Color surface = Color(0xFF0F172A); // slate-900
  static const Color surfaceHighlight = Color(0xFF1E293B); // slate-800
  static const Color primary = Color(0xFF06B6D4); // cyan-500
  static const Color secondary = Color(0xFF10B981); // emerald-500
  static const Color accent = Color(0xFF3B82F6); // blue-500
  static const Color textMain = Color(0xFFF8FAFC); // slate-50
  static const Color textMuted = Color(0xFF94A3B8); // slate-400

  // ── Status colours (clinical meaning — never theme-derived) ────────
  static const Color statusNormal = Color(0xFF10B981); // emerald-500
  static const Color statusWarning = Color(0xFFF59E0B); // amber-500
  static const Color statusCritical = Color(0xFFEF4444); // red-500

  // ── Waveform / per-vital accents ────────────────────────────────────
  // Encode clinical meaning — kept constant across theme variants so a
  // clinician's mental colour-to-vital map doesn't shift.
  static const Color ecgColor = Color(0xFF10B981); // emerald
  static const Color ppgColor = Color(0xFFF43F5E); // rose
  static const Color rspColor = Color(0xFF06B6D4); // cyan
  static const Color fhrColor = Color(0xFFD946EF); // fuchsia
  static const Color hrColor = Color(0xFFF43F5E); // rose-500
  static const Color spo2Color = Color(0xFF06B6D4); // cyan-500
  static const Color tempColor = Color(0xFFF59E0B); // amber-500
  static const Color rrColor = Color(0xFF8B5CF6); // violet-500

  // ── Subtle 1-px divider stroke ─────────────────────────────────────
  static const Color border = Color(0xFF1E293B); // slate-800

  /// Resolves to the new Material 3 dark theme. The previous
  /// implementation built a manual `ThemeData(brightness, ...)`; that
  /// produced a non-M3 look. Now this getter forwards to the seeded
  /// M3 factory so the whole app picks up M3 component shapes,
  /// typography, motion + accessibility scaling automatically.
  static ThemeData get darkTheme =>
      MedverseM3Theme.dark(highContrast: MedverseA11y.highContrastOverride);
}
