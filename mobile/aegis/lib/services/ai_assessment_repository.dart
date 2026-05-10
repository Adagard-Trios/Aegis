import 'package:flutter/foundation.dart';

import 'api_service.dart';
import 'auth_service.dart';
import 'vest_stream_service.dart';

/// Cached store for per-specialty AI assessments.
///
/// Each `AiAssessmentCard` on a specialty screen would fire a fresh
/// `/api/agent/ask` on every mount, which burns Groq tokens on every
/// tab switch. This repository caches the most-recent reply per
/// specialty + auto-invalidates the cache when the underlying telemetry
/// snapshot has meaningfully drifted (debounce: ≥ 30 s OR HR / SpO₂
/// delta > 5 %).
///
/// Usage:
///   ```dart
///   final repo = context.read<AiAssessmentRepository>();
///   final state = repo.watchSpecialty(context, 'cardiology');
///   ```
class AiAssessmentRepository extends ChangeNotifier {
  final VestStreamService stream;
  final AuthService? auth;

  static const Duration _minRefetchInterval = Duration(seconds: 30);
  static const double _hrChangeThreshold = 5.0;
  static const double _spo2ChangeThreshold = 5.0;

  /// Per-specialty cached entries. Key = backend specialty id (matches
  /// the `specialty` field on /api/agent/ask).
  final Map<String, AiAssessmentEntry> _cache = {};

  AiAssessmentRepository({required this.stream, this.auth});

  AiAssessmentEntry? entry(String specialty) => _cache[specialty];

  /// Fire a fresh request for `specialty` if (a) we don't have a cache
  /// hit, or (b) the cache is older than the dampened-refresh window
  /// AND the telemetry has drifted, or (c) the caller passes
  /// `force: true` (manual refresh button).
  Future<void> requestAssessment(
    String specialty, {
    bool force = false,
  }) async {
    final existing = _cache[specialty];
    final snapshot = stream.latestSnapshot;

    if (!force && existing != null && existing.state == AssessmentState.loaded) {
      // Cache hit — only re-fetch when meaningfully stale.
      final age = DateTime.now().difference(existing.fetchedAt);
      if (age < _minRefetchInterval || !_hasDrifted(existing.snapshot, snapshot)) {
        return;
      }
    }

    _cache[specialty] = AiAssessmentEntry.loading(
      previous: existing?.text,
      snapshot: snapshot,
    );
    notifyListeners();

    try {
      final reply = await ApiService.agentAsk(
        specialty: specialty,
        message: 'Provide a concise current clinical assessment based on the '
            'latest telemetry. List key observations and any flags. Markdown OK.',
        snapshot: snapshot,
        auth: auth,
      );

      if (reply == null) {
        _cache[specialty] = AiAssessmentEntry.error(
          message: 'Could not reach the AI agent. Check Settings → Connection.',
          snapshot: snapshot,
        );
      } else {
        _cache[specialty] = AiAssessmentEntry.loaded(
          text: (reply['reply'] as String?) ?? '(no response)',
          severity: reply['severity']?.toString(),
          severityScore: _readNum(reply['severity_score']),
          fetchedAt: DateTime.now(),
          snapshot: snapshot,
        );
      }
    } catch (e) {
      _cache[specialty] = AiAssessmentEntry.error(
        message: 'Request failed: $e',
        snapshot: snapshot,
      );
      debugPrint('[AiAssessmentRepository] $specialty failed: $e');
    }
    notifyListeners();
  }

  /// Compare two telemetry snapshots — has the live state drifted
  /// enough that the AI's assessment is likely stale? Conservative:
  /// only flags meaningful HR / SpO₂ deltas. Other vitals are noisier
  /// at the per-tick scale and would force a refresh too often.
  bool _hasDrifted(Map<String, dynamic>? a, Map<String, dynamic>? b) {
    if (a == null || b == null) return true;
    final aV = (a['vitals'] as Map?) ?? const {};
    final bV = (b['vitals'] as Map?) ?? const {};
    final aHr = _readNum(aV['heart_rate']) ?? 0;
    final bHr = _readNum(bV['heart_rate']) ?? 0;
    if ((aHr - bHr).abs() > _hrChangeThreshold) return true;
    final aSp = _readNum(aV['spo2']) ?? 0;
    final bSp = _readNum(bV['spo2']) ?? 0;
    if ((aSp - bSp).abs() > _spo2ChangeThreshold) return true;
    return false;
  }

  static double? _readNum(dynamic v) {
    if (v is num) return v.toDouble();
    if (v is String) return double.tryParse(v);
    return null;
  }

  /// Reset the cache — used on Logout / Patient Profile change so
  /// stored AI text doesn't leak across patients.
  void clear() {
    _cache.clear();
    notifyListeners();
  }
}

/// One cache entry — covers all four states the UI cares about.
class AiAssessmentEntry {
  final AssessmentState state;
  final String? text;            // loaded text (or previous text while reloading)
  final String? severity;        // "normal" | "concerning" | "critical" | …
  final double? severityScore;
  final DateTime fetchedAt;
  final Map<String, dynamic>? snapshot;
  final String? errorMessage;

  AiAssessmentEntry._({
    required this.state,
    this.text,
    this.severity,
    this.severityScore,
    DateTime? fetchedAt,
    this.snapshot,
    this.errorMessage,
  }) : fetchedAt = fetchedAt ?? DateTime.fromMillisecondsSinceEpoch(0);

  factory AiAssessmentEntry.loading({
    String? previous,
    Map<String, dynamic>? snapshot,
  }) =>
      AiAssessmentEntry._(state: AssessmentState.loading, text: previous, snapshot: snapshot);

  factory AiAssessmentEntry.loaded({
    required String text,
    String? severity,
    double? severityScore,
    required DateTime fetchedAt,
    Map<String, dynamic>? snapshot,
  }) =>
      AiAssessmentEntry._(
        state: AssessmentState.loaded,
        text: text,
        severity: severity,
        severityScore: severityScore,
        fetchedAt: fetchedAt,
        snapshot: snapshot,
      );

  factory AiAssessmentEntry.error({
    required String message,
    Map<String, dynamic>? snapshot,
  }) =>
      AiAssessmentEntry._(
        state: AssessmentState.error,
        errorMessage: message,
        snapshot: snapshot,
      );

  bool get isLoading => state == AssessmentState.loading;
  bool get isLoaded => state == AssessmentState.loaded;
  bool get isError => state == AssessmentState.error;
}

enum AssessmentState { loading, loaded, error }
