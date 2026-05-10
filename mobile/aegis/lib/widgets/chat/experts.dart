import 'package:flutter/material.dart';

/// One specialty persona shown in the [PersonaChipBar] at the top of
/// the Chat screen.
///
/// `id` matches the `specialty` field the backend's `/api/agent/ask`
/// route expects (see app.py:_resolve_specialty for the mapping). Keep
/// this list in sync with the web frontend's
/// [ExpertChatPanel](frontend/app/components/ExpertChatPanel.tsx).
class ExpertPersona {
  final String id;
  final String label;
  final IconData icon;
  final Color accent;
  const ExpertPersona({
    required this.id,
    required this.label,
    required this.icon,
    required this.accent,
  });
}

const expertPersonas = <ExpertPersona>[
  ExpertPersona(
    id: 'general physician',
    label: 'General',
    icon: Icons.medical_information_rounded,
    accent: Color(0xFF3B82F6),
  ),
  ExpertPersona(
    id: 'cardiology',
    label: 'Cardio',
    icon: Icons.monitor_heart_rounded,
    accent: Color(0xFFF43F5E),
  ),
  ExpertPersona(
    id: 'pulmonary',
    label: 'Pulm',
    icon: Icons.air_rounded,
    accent: Color(0xFF10B981),
  ),
  ExpertPersona(
    id: 'neurology',
    label: 'Neuro',
    icon: Icons.psychology_rounded,
    accent: Color(0xFF8B5CF6),
  ),
  ExpertPersona(
    id: 'dermatology',
    label: 'Derm',
    icon: Icons.healing_rounded,
    accent: Color(0xFFF59E0B),
  ),
  ExpertPersona(
    id: 'obstetrics',
    label: 'OB-GYN',
    icon: Icons.pregnant_woman_rounded,
    accent: Color(0xFFD946EF),
  ),
  ExpertPersona(
    id: 'ocular',
    label: 'Ocular',
    icon: Icons.visibility_rounded,
    accent: Color(0xFF06B6D4),
  ),
];

ExpertPersona expertPersonaById(String id) {
  return expertPersonas.firstWhere(
    (p) => p.id == id,
    orElse: () => expertPersonas[0],
  );
}
