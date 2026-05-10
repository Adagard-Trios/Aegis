import 'package:flutter/material.dart';

import '../ble/ble_abdomen_service.dart';
import '../ble/ble_vest_service.dart';
import '../theme.dart';

/// Per-sensor health diagnostic for the connected vest + abdomen.
///
/// Reads each device service's `latestVitals` / `latestFrame` and
/// renders one row per physical probe with:
///   • Live value (formatted with units)
///   • Status chip:  ✓ OK   |  ⚠ NO CONTACT  |  ✕ SILENT
///
/// "Silent" — sensor never reports a plausible value during the entire
/// session (firmware init failure or wiring fault). For most sensors
/// this is detected at-tick (always-zero-on-the-current-frame); for
/// noisy sensors (digital mic, IMU at rest) we instead track a
/// session-max and only mark silent once we've observed enough quiet
/// frames in a row that init-failure is the more likely explanation.
/// "No contact" — reading equals the no-skin baseline (PPG <
/// 2 000 counts, DS18B20 < 25 °C) but the sensor itself responds.
/// "OK" — reading is in a plausible band.
///
/// The widget rebuilds on each ChangeNotifier ping from the underlying
/// services, so values stay live as new BLE notifications arrive.
class SensorHealthPanel extends StatefulWidget {
  final BleVestService vest;
  final BleAbdomenService abdomen;

  const SensorHealthPanel({
    super.key,
    required this.vest,
    required this.abdomen,
  });

  @override
  State<SensorHealthPanel> createState() => _SensorHealthPanelState();
}

class _SensorHealthPanelState extends State<SensorHealthPanel> {
  // Session-max trackers — record the highest absolute value we've
  // ever seen for each "noisy" sensor. Used by the heuristics below
  // so an INMP441 mic in a silent room (RMS=0 on the current tick)
  // doesn't get falsely flagged as SILENT — once it has read >0 even
  // once, it's known-alive for the rest of this session.
  double _digitalMicMax = 0;
  double _analogMicMax = 0;
  double _upperAccelMax = 0;
  double _lowerAccelMax = 0;

  // Frame counter — gives the session-max heuristics enough warm-up
  // before the panel decides anything is silent. Defaults to "alive"
  // on first paint so we don't briefly render SILENT chips before the
  // first BLE frame arrives.
  int _frames = 0;
  static const int _warmupFrames = 5;  // ~0.2 s at 25 Hz

  void _track(double value, double Function() get, void Function(double) set) {
    final abs = value.abs();
    if (abs > get()) set(abs);
  }

  @override
  Widget build(BuildContext context) {
    // Update session-max trackers from the latest snapshot. Done in
    // build so Theme rebuilds + service notifies both refresh state.
    final v = widget.vest.latestVitals;
    if (v != null) {
      _frames++;
      _track(v.digitalRms, () => _digitalMicMax, (n) => _digitalMicMax = n);
      _track(v.analogRms, () => _analogMicMax, (n) => _analogMicMax = n);
      // For IMU "alive" detection we use total accel magnitude — gravity
      // always acts on at least one axis (~9.8 m/s² total) when the
      // MPU6050 is responding, regardless of orientation.
      final upMag = _accelMagnitude(v.upperAccelX, v.upperAccelY, v.upperAccelZ);
      final loMag = _accelMagnitude(v.lowerAccelX, v.lowerAccelY, v.lowerAccelZ);
      _track(upMag, () => _upperAccelMax, (n) => _upperAccelMax = n);
      _track(loMag, () => _lowerAccelMax, (n) => _lowerAccelMax = n);
    }
    return _build(context);
  }

  static double _accelMagnitude(double x, double y, double z) {
    return _sqrt(x * x + y * y + z * z);
  }

  static double _sqrt(double v) {
    if (v <= 0) return 0;
    var r = v;
    for (var i = 0; i < 16; i++) {
      r = 0.5 * (r + v / r);
    }
    return r;
  }

  Widget _build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: MedVerseTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: MedVerseTheme.border, width: 1),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.troubleshoot, color: MedVerseTheme.primary, size: 18),
              const SizedBox(width: 8),
              const Text(
                'Sensor Health',
                style: TextStyle(
                  color: MedVerseTheme.textMain,
                  fontWeight: FontWeight.w700,
                  fontSize: 14,
                  letterSpacing: 0.4,
                ),
              ),
              const Spacer(),
              const Text(
                'Live',
                style: TextStyle(
                    color: MedVerseTheme.textMuted, fontSize: 10, letterSpacing: 1.2),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Text(
            'Per-probe diagnostic — green = reading, amber = no contact, '
            'red = sensor silent (likely firmware init failure).',
            style: TextStyle(color: MedVerseTheme.textMuted, fontSize: 11),
          ),
          const SizedBox(height: 12),
          AnimatedBuilder(
            animation: widget.vest,
            builder: (_, _) => _vestSection(),
          ),
          const SizedBox(height: 8),
          AnimatedBuilder(
            animation: widget.abdomen,
            builder: (_, _) => _abdomenSection(),
          ),
        ],
      ),
    );
  }

  Widget _vestSection() {
    final v = widget.vest.latestVitals;
    final connected = widget.vest.status == BleStatus.connected;
    if (!connected) {
      return _SectionHeader(
        title: 'Aegis Vest',
        subtitle: 'Not connected — pair the vest above to see probe status.',
        icon: Icons.favorite_outline,
        accent: MedVerseTheme.hrColor,
      );
    }
    if (v == null) {
      return _SectionHeader(
        title: 'Aegis Vest',
        subtitle: 'Connected — waiting for first vitals frame…',
        icon: Icons.favorite_outline,
        accent: MedVerseTheme.hrColor,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionHeader(
          title: 'Aegis Vest',
          subtitle: widget.vest.firmwareVersion != null
              ? 'Connected · FW v${widget.vest.firmwareVersion}'
              : 'Connected',
          icon: Icons.favorite_outline,
          accent: MedVerseTheme.hrColor,
        ),
        const SizedBox(height: 8),
        // PPG sensors — three MAX30102 sites
        _SensorRow(
          label: 'MAX30102 #1 (IR1/Red1)',
          value: '${v.ir1.toStringAsFixed(0)} / ${v.red1.toStringAsFixed(0)}',
          state: _pickPpgState(v.ir1),
        ),
        _SensorRow(
          label: 'MAX30102 #2 (IR2/Red2)',
          value: '${v.ir2.toStringAsFixed(0)} / ${v.red2.toStringAsFixed(0)}',
          state: _pickPpgState(v.ir2),
        ),
        _SensorRow(
          label: 'MAX30102 armband (IRA/RedA)',
          value: '${v.ira.toStringAsFixed(0)} / ${v.reda.toStringAsFixed(0)}',
          state: _pickPpgState(v.ira),
        ),
        _SensorRow(
          label: 'PPG sensor temps (T1 / T2)',
          value: '${v.t1.toStringAsFixed(1)} / ${v.t2.toStringAsFixed(1)} °C',
          state: v.t1 > 0 || v.t2 > 0 ? _State.ok : _State.silent,
        ),
        // DS18B20 skin-temp probes
        _SensorRow(
          label: 'DS18B20 left axilla (TL)',
          value: '${v.tl.toStringAsFixed(1)} °C',
          state: _pickSkinState(v.tl),
        ),
        _SensorRow(
          label: 'DS18B20 right axilla (TR)',
          value: '${v.tr.toStringAsFixed(1)} °C',
          state: _pickSkinState(v.tr),
        ),
        _SensorRow(
          label: 'DS18B20 cervical (TC)',
          value: '${v.tc.toStringAsFixed(1)} °C',
          state: _pickSkinState(v.tc),
        ),
        // IMU — upper + lower. Display pitch/roll, but use accel
        // magnitude for the silent/OK heuristic — gravity always
        // shows ~9.8 m/s² total magnitude on a working MPU6050,
        // regardless of orientation. Pitch + roll alone read 0/0
        // when the vest is flat on a desk, which used to falsely
        // trip "SILENT" before this fix.
        _SensorRow(
          label: 'MPU6050 upper (pitch/roll · g)',
          value: '${v.upperPitch.toStringAsFixed(1)} / ${v.upperRoll.toStringAsFixed(1)}°  '
              '· ${_accelMagnitude(v.upperAccelX, v.upperAccelY, v.upperAccelZ).toStringAsFixed(2)} g',
          state: _pickImuStateFromAccel(_upperAccelMax),
        ),
        _SensorRow(
          label: 'MPU6050 lower (pitch/roll · g)',
          value: '${v.lowerPitch.toStringAsFixed(1)} / ${v.lowerRoll.toStringAsFixed(1)}°  '
              '· ${_accelMagnitude(v.lowerAccelX, v.lowerAccelY, v.lowerAccelZ).toStringAsFixed(2)} g',
          state: _pickImuStateFromAccel(_lowerAccelMax),
        ),
        // Pressure / environment
        _SensorRow(
          label: 'BMP180 chest (BPR/BTP)',
          value: '${v.bmp180Pressure.toStringAsFixed(0)} hPa, ${v.bmp180Temp.toStringAsFixed(1)} °C',
          state: v.bmp180Pressure > 100 ? _State.ok : _State.silent,
        ),
        _SensorRow(
          label: 'BMP280 env (EP/ET)',
          value: '${v.bmp280Pressure.toStringAsFixed(0)} hPa, ${v.bmp280Temp.toStringAsFixed(1)} °C',
          state: v.bmp280Pressure > 100 ? _State.ok : _State.silent,
        ),
        _SensorRow(
          label: 'DHT11 env (HUM/DT)',
          value: '${v.dht11Humidity.toStringAsFixed(0)}%, ${v.dht11Temp.toStringAsFixed(1)} °C',
          state: v.dht11Humidity > 0 ? _State.ok : _State.silent,
        ),
        // ECG + audio
        _SensorRow(
          label: 'AD8232 ECG (EHR firmware QRS)',
          value: '${v.ecgHr.toStringAsFixed(1)} bpm',
          state: v.ecgHr > 0 ? _State.ok : _State.silent,
        ),
        _SensorRow(
          label: 'MAX9814 analog mic (ARMS)',
          value: v.analogRms.toStringAsFixed(0),
          state: _pickAudioState(v.analogRms, _analogMicMax),
        ),
        _SensorRow(
          label: 'INMP441 digital mic (DRMS)',
          value: v.digitalRms.toStringAsFixed(0),
          state: _pickAudioState(v.digitalRms, _digitalMicMax),
        ),
      ],
    );
  }

  Widget _abdomenSection() {
    final f = widget.abdomen.latestFrame;
    final connected = widget.abdomen.status == BleStatus.connected;
    if (!connected) {
      return _SectionHeader(
        title: 'Abdomen Monitor',
        subtitle: 'Not connected — pair the abdomen monitor above.',
        icon: Icons.pregnant_woman,
        accent: MedVerseTheme.fhrColor,
      );
    }
    if (f == null) {
      return _SectionHeader(
        title: 'Abdomen Monitor',
        subtitle: 'Connected — waiting for first sensor frame…',
        icon: Icons.pregnant_woman,
        accent: MedVerseTheme.fhrColor,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _SectionHeader(
          title: 'Abdomen Monitor',
          subtitle: 'Connected · mode = ${f.mode == 0 ? "fetal" : "abdominal"}',
          icon: Icons.pregnant_woman,
          accent: MedVerseTheme.fhrColor,
        ),
        const SizedBox(height: 8),
        for (var i = 0; i < f.piezoRaw.length; i++)
          _SensorRow(
            label: 'Piezo channel ${i + 1} (pz$i)',
            value: '${f.piezoRaw[i]}',
            state: f.piezoRaw[i] > 100 ? _State.ok : _State.silent,
          ),
        for (var i = 0; i < f.micVolts.length; i++)
          _SensorRow(
            label: 'MEMS mic ${i + 1} (mv$i)',
            value: '${f.micVolts[i].toStringAsFixed(2)} V',
            state: f.micVolts[i].abs() > 0.05 ? _State.ok : _State.noContact,
          ),
        for (var i = 0; i < f.filmPressure.length; i++)
          _SensorRow(
            label: 'Flex film ${i + 1} (fp$i)',
            value: '${f.filmPressure[i].toStringAsFixed(1)} %',
            state: f.filmPressure[i] > 0.1 ? _State.ok : _State.noContact,
          ),
      ],
    );
  }

  // ── Heuristics ──────────────────────────────────────────────────────

  /// MAX30102 raw counts. 0 → sensor silent; <2000 → off skin (LED-only
  /// reflection); ≥2000 → seeing tissue.
  _State _pickPpgState(double v) {
    if (v <= 0) return _State.silent;
    if (v < 2000) return _State.noContact;
    return _State.ok;
  }

  /// DS18B20: -127 (clamped to 0 by firmware) → sensor silent;
  /// <25°C → probe in air (no skin contact); ≥25°C → on skin.
  _State _pickSkinState(double v) {
    if (v == 0) return _State.silent;
    if (v < 25) return _State.noContact;
    return _State.ok;
  }

  /// MPU6050 alive-detection from session-max accel magnitude.
  /// Gravity is always present (~1 g total magnitude) when the sensor
  /// is responding, so any reading near 1 g means the chip is working.
  /// We use session-max (the largest magnitude we've seen this run) so
  /// a momentary tick that comes through as 0 doesn't flip the chip
  /// to "silent" mid-session. Silent only after warmup if we've never
  /// seen any accel signal at all.
  _State _pickImuStateFromAccel(double sessionMaxG) {
    if (_frames < _warmupFrames) return _State.ok;
    if (sessionMaxG > 0.5) return _State.ok;
    return _State.silent;
  }

  /// Audio sensor alive-detection from session-max RMS. A silent room
  /// reads RMS=0 even when the mic is fully working, so checking the
  /// per-tick value would falsely flag the sensor as silent. We track
  /// the highest RMS we've seen this run; once it exceeds a small
  /// floor we treat the mic as known-alive for the rest of the
  /// session.
  _State _pickAudioState(double currentValue, double sessionMax) {
    if (_frames < _warmupFrames) return _State.ok;
    if (sessionMax > 1) return _State.ok;     // ever heard anything → alive
    return _State.silent;
  }
}

// ── Internals ────────────────────────────────────────────────────────

enum _State { ok, noContact, silent }

class _SensorRow extends StatelessWidget {
  final String label;
  final String value;
  final _State state;
  const _SensorRow({
    required this.label,
    required this.value,
    required this.state,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(
            flex: 5,
            child: Text(
              label,
              style: const TextStyle(
                color: MedVerseTheme.textMain,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Expanded(
            flex: 4,
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(
                color: MedVerseTheme.textMuted,
                fontSize: 11,
                fontFamily: 'monospace',
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: 8),
          _StateChip(state: state),
        ],
      ),
    );
  }
}

class _StateChip extends StatelessWidget {
  final _State state;
  const _StateChip({required this.state});

  @override
  Widget build(BuildContext context) {
    final (label, color, icon) = switch (state) {
      _State.ok => ('OK', MedVerseTheme.statusNormal, Icons.check_circle),
      _State.noContact => (
        'NO CONTACT',
        MedVerseTheme.statusWarning,
        Icons.warning_amber_rounded
      ),
      _State.silent => (
        'SILENT',
        MedVerseTheme.statusCritical,
        Icons.cancel
      ),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 11, color: color),
          const SizedBox(width: 3),
          Text(
            label,
            style: TextStyle(
              color: color,
              fontSize: 9,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.6,
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final Color accent;
  const _SectionHeader({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.accent,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 16, color: accent),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title,
                    style: const TextStyle(
                      color: MedVerseTheme.textMain,
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                    )),
                Text(
                  subtitle,
                  style: const TextStyle(
                      color: MedVerseTheme.textMuted, fontSize: 11),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
