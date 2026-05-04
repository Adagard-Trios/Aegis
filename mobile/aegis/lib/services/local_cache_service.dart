import 'package:flutter/foundation.dart';

/// In-memory ring buffer of recent telemetry snapshots.
///
/// Keeps the last [_maxLen] snapshots so the UI can replay the most-
/// recent window if the live stream drops. The cache is intentionally
/// bounded — we don't want unlimited growth on a long-running session.
///
/// Persistence across app restarts (Hive / shared_preferences) is a
/// future enhancement; today's contract is "buffer the last ~minute
/// of stream so we can show a clean disconnect-and-reconnect UX."
///
/// Subscribers (the offline banner, an export-on-demand widget, etc.)
/// listen via the ChangeNotifier interface.
class LocalCacheService extends ChangeNotifier {
  final int _maxLen;
  final List<Map<String, dynamic>> _buffer = [];

  /// Number of snapshots persisted into the cache since boot. Surfaced
  /// in the offline banner so users can see "20 cached" turn into "0
  /// cached" when sync flushes.
  int _persistedCount = 0;

  LocalCacheService({int maxLen = 1000}) : _maxLen = maxLen;

  /// Latest snapshots, oldest first. Returns a copy so callers can't
  /// mutate the internal buffer.
  List<Map<String, dynamic>> get snapshots => List.unmodifiable(_buffer);

  int get length => _buffer.length;
  int get persistedCount => _persistedCount;
  int get maxLength => _maxLen;

  /// Append one snapshot. Drops the oldest entry when full.
  void push(Map<String, dynamic> snapshot) {
    _buffer.add(Map<String, dynamic>.from(snapshot));
    if (_buffer.length > _maxLen) {
      _buffer.removeAt(0);
    }
    _persistedCount++;
    notifyListeners();
  }

  /// Drop everything. Called after a successful sync flush so the UI
  /// can reset its "cached" counter back to 0.
  void clear() {
    if (_buffer.isEmpty) return;
    _buffer.clear();
    notifyListeners();
  }

  /// Most recent snapshot, or null when empty.
  Map<String, dynamic>? get latest => _buffer.isEmpty ? null : _buffer.last;
}
