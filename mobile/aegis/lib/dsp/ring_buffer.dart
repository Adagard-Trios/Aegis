import 'dart:typed_data';

/// Bounded ring buffer for `double` samples backed by a [Float64List].
///
/// O(1) `push`, O(n) `toList` (amortised through the snapshot path —
/// the LocalDspService only reads the buffer once per second).
///
/// Designed for high-frequency sample streams (333 Hz ECG bursts, ~1 Hz
/// vest vitals, ~10 Hz fetal frames) where allocation churn would be
/// noticeable on low-end Android.
class RingBuffer {
  final int capacity;
  final Float64List _buf;
  int _head = 0;     // next write position
  int _length = 0;   // valid sample count (≤ capacity)

  RingBuffer(this.capacity) : _buf = Float64List(capacity);

  int get length => _length;
  bool get isFull => _length == capacity;
  bool get isEmpty => _length == 0;

  void push(double v) {
    _buf[_head] = v;
    _head = (_head + 1) % capacity;
    if (_length < capacity) _length++;
  }

  void pushAll(Iterable<double> samples) {
    for (final v in samples) {
      push(v);
    }
  }

  void clear() {
    _head = 0;
    _length = 0;
  }

  /// Snapshot the valid samples in chronological order.
  Float64List toList() {
    final out = Float64List(_length);
    if (_length < capacity) {
      // Buffer hasn't wrapped — head equals length, oldest at index 0.
      for (var i = 0; i < _length; i++) {
        out[i] = _buf[i];
      }
    } else {
      // Wrapped — oldest sample sits at _head.
      for (var i = 0; i < capacity; i++) {
        out[i] = _buf[(_head + i) % capacity];
      }
    }
    return out;
  }
}
