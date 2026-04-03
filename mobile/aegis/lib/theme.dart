import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class MedVerseTheme {
  // Brand colors matching the Next.js Tailwind configuration
  static const Color background = Color(0xFF020617); // slate-950
  static const Color surface = Color(0xFF0F172A); // slate-900
  static const Color surfaceHighlight = Color(0xFF1E293B); // slate-800
  static const Color primary = Color(0xFF06B6D4); // cyan-500
  static const Color secondary = Color(0xFF10B981); // emerald-500
  static const Color accent = Color(0xFF3B82F6); // blue-500
  static const Color textMain = Color(0xFFF8FAFC); // slate-50
  static const Color textMuted = Color(0xFF94A3B8); // slate-400

  // Status Colors
  static const Color statusNormal = Color(0xFF10B981); // emerald-500
  static const Color statusWarning = Color(0xFFF59E0B); // amber-500
  static const Color statusCritical = Color(0xFFEF4444); // red-500
  
  // Waveform Line Colors
  static const Color ecgColor = Color(0xFF10B981); // emerald
  static const Color ppgColor = Color(0xFFF43F5E); // rose
  static const Color rspColor = Color(0xFF06B6D4); // cyan
  static const Color fhrColor = Color(0xFFD946EF); // fuchsia

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: background,
      primaryColor: primary,
      colorScheme: const ColorScheme.dark(
        primary: primary,
        secondary: secondary,
        surface: surface,
        background: background,
        error: statusCritical,
        onSurface: textMain,
        onBackground: textMain,
      ),
      textTheme: GoogleFonts.interTextTheme(
        ThemeData.dark().textTheme,
      ).apply(
        bodyColor: textMain,
        displayColor: textMain,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        elevation: 0,
        centerTitle: false,
        iconTheme: IconThemeData(color: primary),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: surface,
        selectedItemColor: primary,
        unselectedItemColor: textMuted,
        type: BottomNavigationBarType.fixed,
        elevation: 4,
      ),
      cardTheme: CardThemeData(
        color: surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: surfaceHighlight, width: 1),
        ),
        elevation: 0,
      ),
      dividerColor: surfaceHighlight,
    );
  }
}
