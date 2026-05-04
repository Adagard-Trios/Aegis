import 'package:flutter/foundation.dart';

/// Queue of snapshots captured while offline, ready to flush back to
/// the backend when connectivity returns.
///
/// The backend already accepts each snapshot via the live SSE-feeding
/// path, so flushing is a forward-replay: re-emit each cached snapshot
/// onto the in-process VestDataModel as the connection returns. The
/// backend's sqlite_writer_loop will pick those up like any other tick.
///
/// `flushTo(callback)` is the bridge — pass a function that re-injects
/// one snapshot, and SyncQueueService walks the queue + clears it on
/// success. If the callback throws, we keep the remaining queue intact
/// so the next reconnect attempt can pick up where we left off.
class SyncQueueService extends ChangeNotifier {
  final int _maxLen;
  final List<Map<String, dynamic>> _queue = [];
  bool _flushInProgress = false;

  SyncQueueService({int maxLen = 5000}) : _maxLen = maxLen;

  int get length => _queue.length;
  int get maxLength => _maxLen;
  bool get isFlushing => _flushInProgress;

  /// Append a snapshot to the queue (e.g. while offline).
  void enqueue(Map<String, dynamic> snapshot) {
    _queue.add(Map<String, dynamic>.from(snapshot));
    if (_queue.length > _maxLen) {
      _queue.removeAt(0); // drop oldest when full
    }
    notifyListeners();
  }

  /// Flush queued snapshots through `injector`. The injector should
  /// hand each snapshot to the live consumer (VestDataModel.updateFromStream).
  /// Concurrent flush calls are no-ops.
  Future<int> flushTo(Future<void> Function(Map<String, dynamic>) injector) async {
    if (_flushInProgress || _queue.isEmpty) return 0;
    _flushInProgress = true;
    notifyListeners();
    int sent = 0;
    try {
      while (_queue.isNotEmpty) {
        final next = _queue.first;
        await injector(next);
        _queue.removeAt(0);
        sent++;
      }
      return sent;
    } catch (_) {
      // Leave the unsent rest in the queue for the next attempt.
      rethrow;
    } finally {
      _flushInProgress = false;
      notifyListeners();
    }
  }

  /// Drop everything (e.g. user-initiated reset).
  void clear() {
    if (_queue.isEmpty) return;
    _queue.clear();
    notifyListeners();
  }
}
