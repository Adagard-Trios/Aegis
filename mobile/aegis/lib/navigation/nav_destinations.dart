import 'package:flutter/material.dart';

/// Bottom-navigation destination metadata. One entry per tab; the
/// order here is the order the tabs appear in the M3 NavigationBar.
///
/// Each entry carries the route path, label, both icon variants
/// (selected = filled, idle = outlined, per M3 spec), and a
/// `semanticLabel` consumed by TalkBack / VoiceOver so blind users get
/// a more descriptive announcement than the visual label alone.
class NavDestination {
  final String path;
  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final String semanticLabel;
  const NavDestination({
    required this.path,
    required this.label,
    required this.icon,
    required this.selectedIcon,
    required this.semanticLabel,
  });
}

/// Single source of truth for the bottom NavigationBar.
///
/// Sensors is intentionally absent — it lives at `/settings/sensors`
/// (one-time setup task, not daily nav). Drawer-only routes (Upload
/// labs etc.) are no longer separate; they're folded into the
/// Diagnostics chat composer or the Settings hub.
const navDestinations = <NavDestination>[
  NavDestination(
    path: '/',
    label: 'Dashboard',
    icon: Icons.dashboard_outlined,
    selectedIcon: Icons.dashboard_rounded,
    semanticLabel: 'Dashboard, vitals overview',
  ),
  NavDestination(
    path: '/specialists',
    label: 'Specialists',
    icon: Icons.medical_services_outlined,
    selectedIcon: Icons.medical_services_rounded,
    semanticLabel: 'Specialists, seven AI experts',
  ),
  NavDestination(
    path: '/twin',
    label: '3D Twin',
    icon: Icons.accessibility_new_outlined,
    selectedIcon: Icons.accessibility_new_rounded,
    semanticLabel: 'Three-D digital twin viewer',
  ),
  NavDestination(
    // `auto_awesome` (sparkle) reads as "AI / generative" rather than
    // a conventional speech-bubble — clearer signal that this surface
    // is an LLM-driven assistant, not a P2P chat.
    path: '/chat',
    label: 'Chat',
    icon: Icons.auto_awesome_outlined,
    selectedIcon: Icons.auto_awesome,
    semanticLabel: 'AI specialist chat',
  ),
  NavDestination(
    // `tune_rounded` (slider stack) carries a "control surface" /
    // futuristic-mission-control feel that fits the redesign better
    // than the conventional cog. Selected variant uses the filled
    // counterpart so the active state has visible weight.
    path: '/settings',
    label: 'Settings',
    icon: Icons.tune_outlined,
    selectedIcon: Icons.tune_rounded,
    semanticLabel: 'Settings, sensors, profile, preferences',
  ),
];
