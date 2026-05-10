import 'package:flutter/material.dart';

import 'medverse_typography.dart';

/// Material 3 theme system for Aegis.
///
/// Replaces the old `MedVerseTheme.darkTheme` (legacy `ColorScheme.dark`
/// constructor, no Material 3 tokens). Now produces a fully M3-tonal
/// dark scheme seeded from cyan-500 (the brand colour) via
/// [ColorScheme.fromSeed]. Light variant is provided as a stub for the
/// future light-mode toggle in [AccessibilitySettingsScreen].
///
/// **Backward compatibility**: the static colour constants on the
/// legacy `MedVerseTheme` class (kept in [theme.dart] alongside this
/// module during the migration) still resolve to sensible values so
/// the dozens of existing widgets that read `MedVerseTheme.primary`,
/// `MedVerseTheme.surface`, etc. keep working. New code should prefer
/// `Theme.of(context).colorScheme.<token>` directly.
///
/// Per-vital accent colours (`hrColor`, `spo2Color`, `tempColor`,
/// `rrColor`, `ecgColor`, `ppgColor`, `rspColor`, `fhrColor`) are NOT
/// derived from the seed — they encode clinical meaning and stay
/// constant across themes.
class MedverseM3Theme {
  MedverseM3Theme._();

  /// Brand seed — cyan-500. M3's tonal-palette generator derives the
  /// full primary / secondary / tertiary palettes from this single
  /// colour, keeping every surface in tonal harmony.
  static const Color seed = Color(0xFF06B6D4);

  /// Build the dark `ThemeData`. `highContrast` flag bumps surface
  /// luminance so on-surface text passes WCAG AAA (≥7:1) instead of
  /// just AA — used by the accessibility-mode toggle.
  static ThemeData dark({bool highContrast = false}) {
    var scheme = ColorScheme.fromSeed(
      seedColor: seed,
      brightness: Brightness.dark,
    );
    if (highContrast) {
      // Push surface tones darker + foreground tones brighter so the
      // luminance gap widens. This is the cheap, theme-level
      // approximation of M3's full high-contrast scheme.
      scheme = scheme.copyWith(
        surface: const Color(0xFF030712),
        onSurface: const Color(0xFFFFFFFF),
        onSurfaceVariant: const Color(0xFFE5E7EB),
        outline: const Color(0xFF94A3B8),
      );
    }
    return _build(scheme);
  }

  /// Light `ThemeData` — stub for the future. Same seed, brightness
  /// flipped. Today the app boots in dark mode by default; this exists
  /// so AccessibilitySettingsScreen can offer a "Light" toggle without
  /// blocking on more theme work.
  static ThemeData light({bool highContrast = false}) {
    var scheme = ColorScheme.fromSeed(
      seedColor: seed,
      brightness: Brightness.light,
    );
    if (highContrast) {
      scheme = scheme.copyWith(
        surface: const Color(0xFFFFFFFF),
        onSurface: const Color(0xFF000000),
      );
    }
    return _build(scheme);
  }

  static ThemeData _build(ColorScheme scheme) {
    final textTheme = MedverseTypography.textTheme(scheme.onSurface);
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      brightness: scheme.brightness,
      scaffoldBackgroundColor: scheme.surface,
      textTheme: textTheme,
      // M3 NavigationBar surface — pinned to surfaceContainer so it
      // sits visually distinct from the scaffold without a hard line.
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: scheme.surfaceContainer,
        indicatorColor: scheme.secondaryContainer,
        labelTextStyle: WidgetStatePropertyAll(textTheme.labelMedium),
        labelBehavior: NavigationDestinationLabelBehavior.onlyShowSelected,
        height: 80,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: scheme.surface,
        foregroundColor: scheme.onSurface,
        elevation: 0,
        scrolledUnderElevation: 1,
        surfaceTintColor: scheme.surfaceTint,
        centerTitle: false,
        titleTextStyle: textTheme.titleLarge?.copyWith(
          fontWeight: FontWeight.w700,
          letterSpacing: 0.4,
        ),
      ),
      cardTheme: CardThemeData(
        // Soft tonal surface — matches M3's "filled card" variant which
        // is what dashboards look best on.
        color: scheme.surfaceContainerLow,
        surfaceTintColor: scheme.surfaceTint,
        shadowColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
        ),
        elevation: 0,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size(64, 48),  // M3 baseline + a11y target
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          textStyle: textTheme.labelLarge,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size(64, 48),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          textStyle: textTheme.labelLarge,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          minimumSize: const Size(48, 48),
          textStyle: textTheme.labelLarge,
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(
          minimumSize: const Size(48, 48),
        ),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: scheme.surfaceContainerHigh,
        selectedColor: scheme.secondaryContainer,
        labelStyle: textTheme.labelLarge,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        side: BorderSide.none,
      ),
      dividerTheme: DividerThemeData(
        color: scheme.outlineVariant,
        thickness: 1,
        space: 1,
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: scheme.inverseSurface,
        contentTextStyle: textTheme.bodyMedium?.copyWith(
          color: scheme.onInverseSurface,
        ),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: scheme.surfaceContainer,
        surfaceTintColor: scheme.surfaceTint,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
        showDragHandle: true,
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: scheme.surfaceContainerHigh,
        surfaceTintColor: scheme.surfaceTint,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(28)),
        titleTextStyle: textTheme.headlineSmall,
        contentTextStyle: textTheme.bodyMedium,
      ),
    );
  }
}
