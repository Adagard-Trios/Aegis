import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Material 3 typography scale for the Aegis app.
///
/// Two type families:
///   - **Inter** for prose / labels / titles — body content, navigation,
///     headers. M3-aligned weights (regular, medium, semibold, bold).
///   - **JetBrains Mono** for numeric biometrics (HR, BP, SpO₂, etc.).
///     Tabular monospaced glyphs prevent live-value reflow when the
///     number's digit count changes, which matters for clinical data
///     that updates every tick.
///
/// Pulled from the M3 type scale spec. Sizes match Google's reference
/// implementation so any Material 3 component (NavigationBar, Card,
/// FilledButton, etc.) renders with platform-correct proportions out
/// of the box.
class MedverseTypography {
  MedverseTypography._();

  /// Numeric / tabular text style — hand this to [BiometricCard] /
  /// [MultiLeadEcgWaveform] / any widget that renders a raw vital so
  /// the digits stop visually jittering when the value updates.
  static TextStyle mono(double fontSize, {FontWeight weight = FontWeight.w600}) {
    return GoogleFonts.jetBrainsMono(
      fontSize: fontSize,
      fontWeight: weight,
      fontFeatures: const [FontFeature.tabularFigures()],
    );
  }

  /// Build the M3 [TextTheme] used by [ThemeData.textTheme]. Weight +
  /// height ratios match the official M3 spec; sizes are stock M3
  /// defaults so platform-correct components keep their proportions.
  ///
  /// `baseColor` is the resolved `colorScheme.onSurface` from the
  /// current theme — passed in so we don't hard-code a light/dark
  /// foreground.
  static TextTheme textTheme(Color baseColor) {
    final inter = GoogleFonts.interTextTheme();
    return TextTheme(
      displayLarge: inter.displayLarge?.copyWith(
        fontSize: 57, height: 1.12, letterSpacing: -0.25, fontWeight: FontWeight.w400, color: baseColor,
      ),
      displayMedium: inter.displayMedium?.copyWith(
        fontSize: 45, height: 1.16, fontWeight: FontWeight.w400, color: baseColor,
      ),
      displaySmall: inter.displaySmall?.copyWith(
        fontSize: 36, height: 1.22, fontWeight: FontWeight.w400, color: baseColor,
      ),
      headlineLarge: inter.headlineLarge?.copyWith(
        fontSize: 32, height: 1.25, fontWeight: FontWeight.w500, color: baseColor,
      ),
      headlineMedium: inter.headlineMedium?.copyWith(
        fontSize: 28, height: 1.29, fontWeight: FontWeight.w500, color: baseColor,
      ),
      headlineSmall: inter.headlineSmall?.copyWith(
        fontSize: 24, height: 1.33, fontWeight: FontWeight.w500, color: baseColor,
      ),
      titleLarge: inter.titleLarge?.copyWith(
        fontSize: 22, height: 1.27, fontWeight: FontWeight.w600, color: baseColor,
      ),
      titleMedium: inter.titleMedium?.copyWith(
        fontSize: 16, height: 1.5, letterSpacing: 0.15, fontWeight: FontWeight.w600, color: baseColor,
      ),
      titleSmall: inter.titleSmall?.copyWith(
        fontSize: 14, height: 1.43, letterSpacing: 0.1, fontWeight: FontWeight.w600, color: baseColor,
      ),
      bodyLarge: inter.bodyLarge?.copyWith(
        fontSize: 16, height: 1.5, letterSpacing: 0.5, fontWeight: FontWeight.w400, color: baseColor,
      ),
      bodyMedium: inter.bodyMedium?.copyWith(
        fontSize: 14, height: 1.43, letterSpacing: 0.25, fontWeight: FontWeight.w400, color: baseColor,
      ),
      bodySmall: inter.bodySmall?.copyWith(
        fontSize: 12, height: 1.33, letterSpacing: 0.4, fontWeight: FontWeight.w400, color: baseColor,
      ),
      labelLarge: inter.labelLarge?.copyWith(
        fontSize: 14, height: 1.43, letterSpacing: 0.1, fontWeight: FontWeight.w600, color: baseColor,
      ),
      labelMedium: inter.labelMedium?.copyWith(
        fontSize: 12, height: 1.33, letterSpacing: 0.5, fontWeight: FontWeight.w600, color: baseColor,
      ),
      labelSmall: inter.labelSmall?.copyWith(
        fontSize: 11, height: 1.45, letterSpacing: 0.5, fontWeight: FontWeight.w600, color: baseColor,
      ),
    );
  }
}
