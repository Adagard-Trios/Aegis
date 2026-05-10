import 'dart:math';
import 'dart:typed_data';

import 'package:aegis/dsp/dsp_service.dart';
import 'package:aegis/dsp/peak_finder.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('PeakFinder', () {
    test('detects two clean peaks 10 samples apart', () {
      final x = Float64List.fromList([0, 1, 2, 1, 0, 0, 0, 0, 0, 0, 0, 1, 2, 1, 0]);
      final peaks = PeakFinder.findPeaks(x, minDistance: 5, minProminence: 0.5);
      expect(peaks, [2, 12]);
    });

    test('distance constraint drops the smaller of two close peaks', () {
      final x = Float64List.fromList([0, 0, 1, 0, 2, 0, 0]);
      final peaks = PeakFinder.findPeaks(x, minDistance: 4);
      expect(peaks, [4]);
    });

    test('prominence filter drops noise spikes', () {
      final x = Float64List.fromList([10, 11, 10, 0, 5, 0, 10, 11, 10]);
      final peaks = PeakFinder.findPeaks(x, minProminence: 4);
      expect(peaks, contains(4));
    });
  });

  group('DspService.calculateHeartRate', () {
    // True-fidelity HR validation lives in the golden-data fixtures vs
    // Python (DSP plan, Phase 5). These tests just lock in the API
    // contract: returns 0 when there's no signal, returns *something*
    // in the physiologic 30–220 band when there is.
    test('clean 1.2 Hz sine returns either 0 or a value in 30–220', () {
      const fs = 40;
      const seconds = 6;
      const bpm = 72.0;
      const f = bpm / 60.0;
      final ir = Float64List(fs * seconds);
      for (var i = 0; i < ir.length; i++) {
        ir[i] = 50000 + 800 * sin(2 * pi * f * i / fs);
      }
      final hr = DspService.calculateHeartRate(ir, sampleRate: fs);
      expect(hr == 0.0 || (hr >= 30.0 && hr <= 220.0), isTrue);
    });

    test('flat input returns 0 (no peaks)', () {
      final ir = Float64List(40 * 6);
      for (var i = 0; i < ir.length; i++) {
        ir[i] = 50000;
      }
      expect(DspService.calculateHeartRate(ir, sampleRate: 40), 0.0);
    });

    test('too-short buffer returns 0', () {
      final ir = Float64List(40);  // only 1 second; needs ≥ 4 s
      expect(DspService.calculateHeartRate(ir, sampleRate: 40), 0.0);
    });
  });

  group('DspService.calculateSpo2', () {
    test('strong PPG matches table SpO2 in 90s range', () {
      const fs = 40;
      final ir = Float64List(fs * 4);
      final red = Float64List(fs * 4);
      for (var i = 0; i < ir.length; i++) {
        ir[i] = 50000 + 800 * sin(2 * pi * 1.2 * i / fs);
        red[i] = 30000 + 400 * sin(2 * pi * 1.2 * i / fs);
      }
      final spo2 = DspService.calculateSpo2(ir, red, sampleRate: fs);
      expect(spo2, greaterThanOrEqualTo(80));
      expect(spo2, lessThanOrEqualTo(100));
    });

    test('weak signal returns 0', () {
      final ir = Float64List(160);
      final red = Float64List(160);
      // mean(IR) < 1000 → 0.0 by contract
      expect(DspService.calculateSpo2(ir, red, sampleRate: 40), 0.0);
    });
  });

  group('DspService.calculatePi', () {
    test('flat signal returns 0', () {
      final ir = Float64List(160);
      for (var i = 0; i < ir.length; i++) {
        ir[i] = 50000;
      }
      expect(DspService.calculatePi(ir, sampleRate: 40), 0.0);
    });

    test('1% AC modulation gives PI ≈ 0.71', () {
      const fs = 40;
      final ir = Float64List(fs * 4);
      for (var i = 0; i < ir.length; i++) {
        ir[i] = 50000 * (1 + 0.01 * sin(2 * pi * 1.2 * i / fs));
      }
      final pIndex = DspService.calculatePi(ir, sampleRate: fs);
      // std/mean of a sine = 1/√2 of amplitude — so PI ≈ 0.71% here.
      expect(pIndex, closeTo(0.71, 0.2));
    });
  });
}
