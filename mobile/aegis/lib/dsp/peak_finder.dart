import 'dart:typed_data';

/// Minimal port of `scipy.signal.find_peaks` covering the two arguments
/// the MedVerse DSP actually uses: `distance` (minimum samples between
/// adjacent peaks) and `prominence` (minimum peak prominence).
///
/// Detects local maxima of `x[i]` such that `x[i-1] < x[i] >= x[i+1]`,
/// then filters them by the prominence + distance constraints.
class PeakFinder {
  /// Find peak indices in [signal] subject to `distance >= minDistance`
  /// and `prominence >= minProminence`.
  ///
  /// `minDistance` is in samples (1-based: a value of 5 means peaks
  /// can be no closer than 5 samples apart).
  ///
  /// Returns indices in increasing order. When constraints conflict,
  /// scipy keeps the higher peak — same behaviour here.
  static List<int> findPeaks(
    Float64List signal, {
    int minDistance = 1,
    double minProminence = 0.0,
  }) {
    final n = signal.length;
    if (n < 3) return const [];
    // Step 1: collect raw local maxima.
    final raw = <int>[];
    for (var i = 1; i < n - 1; i++) {
      if (signal[i] > signal[i - 1] && signal[i] >= signal[i + 1]) {
        // Handle plateaus: walk to the right edge of the plateau and
        // record the centre, matching scipy semantics.
        var j = i;
        while (j + 1 < n - 1 && signal[j + 1] == signal[i]) {
          j++;
        }
        if (signal[j] > signal[j + 1]) {
          raw.add((i + j) ~/ 2);
        }
        i = j;
      }
    }
    if (raw.isEmpty) return const [];

    // Step 2: prominence filter (single-pass, looks left + right for
    // base, like scipy's _peak_prominences).
    final keepProminence = <int>[];
    for (final p in raw) {
      final prom = _prominence(signal, p);
      if (prom >= minProminence) keepProminence.add(p);
    }
    if (keepProminence.isEmpty) return const [];

    // Step 3: distance filter — greedy, taller-first (matches scipy).
    if (minDistance <= 1) return keepProminence;
    final order = List<int>.from(keepProminence)
      ..sort((a, b) => signal[b].compareTo(signal[a]));
    final keep = List<bool>.filled(keepProminence.length, true);
    final indexOf = {for (var i = 0; i < keepProminence.length; i++) keepProminence[i]: i};
    for (final p in order) {
      final ix = indexOf[p]!;
      if (!keep[ix]) continue;
      // Drop any other peaks within minDistance.
      for (var j = 0; j < keepProminence.length; j++) {
        if (j == ix) continue;
        if (!keep[j]) continue;
        if ((keepProminence[j] - p).abs() < minDistance) {
          keep[j] = false;
        }
      }
    }
    final out = <int>[];
    for (var i = 0; i < keepProminence.length; i++) {
      if (keep[i]) out.add(keepProminence[i]);
    }
    return out;
  }

  /// Topographic prominence at index `p` — the height of the peak above
  /// the lowest point you'd have to descend to reach a higher peak.
  /// Matches scipy.signal._peak_prominences semantics.
  static double _prominence(Float64List x, int p) {
    final h = x[p];
    // Walk left until we find a point ≥ peak height (or run off the edge).
    var left = p;
    var leftMin = h;
    while (left > 0) {
      left--;
      if (x[left] >= h) break;
      if (x[left] < leftMin) leftMin = x[left];
    }
    // Walk right.
    var right = p;
    var rightMin = h;
    while (right < x.length - 1) {
      right++;
      if (x[right] >= h) break;
      if (x[right] < rightMin) rightMin = x[right];
    }
    final base = leftMin > rightMin ? leftMin : rightMin;
    return h - base;
  }
}
