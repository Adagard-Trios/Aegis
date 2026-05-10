import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../ble/ble_connection_supervisor.dart';
import '../ble/ble_payload_parser.dart';
import '../ble/ble_vest_service.dart';

/// "Please wear the vest" banner.
///
/// Watches the live [BleVestService.latestVitals]. When the vest is
/// connected but its three MAX30102 PPG channels (IR1 / IR2 / IRA)
/// are all reading at the no-contact baseline, surface a friendly
/// prompt asking the user to put the vest on. When at least one PPG
/// channel reports tissue contact (≥ 2 000 counts), the banner hides
/// itself.
///
/// Disconnect / no-data states stay silent here — the existing
/// [OfflineBanner] handles those at the app shell level.
class WearVestBanner extends StatelessWidget {
  const WearVestBanner({super.key});

  /// PPG counts below this read as "no skin contact" — same threshold
  /// used by [SensorHealthPanel]. The MAX30102 emits >2 000 counts as
  /// soon as light reflects off tissue, well above the LED-only
  /// reflection floor.
  static const double _contactThreshold = 2000.0;

  /// DS18B20 emits -127 °C as a sentinel when a probe momentarily fails
  /// to ACK. Anything outside the physiological band is "disconnected".
  static const double _tempMinC = 25.0;
  static const double _tempMaxC = 45.0;

  /// MPU6050 measures gravity always — total |a| should be near 1 g
  /// (≈ 9.8 m/s²) on a still vest. A working sensor never produces
  /// 0.0 across all three axes; that means the I2C bus is silent.
  static const double _accelGravityFloor = 0.1;

  /// INMP441 produces non-zero RMS even in a quiet room (electronic
  /// noise floor). Exactly zero across analog + digital mics for a
  /// few seconds means the I2S bus didn't initialise.
  static const double _audioFloor = 1.0;

  @override
  Widget build(BuildContext context) {
    final supervisor = context.watch<BleConnectionSupervisor>();
    return AnimatedBuilder(
      animation: supervisor.vest,
      builder: (context, _) {
        final state = _evaluate(supervisor.vest);
        if (state == null) return const SizedBox.shrink();
        return _Banner(state: state);
      },
    );
  }

  /// Returns a [_BannerState] when the banner should show, or `null`
  /// when conditions are good and the banner stays hidden.
  ///
  /// Priority order — higher-severity hardware faults shadow the
  /// "wear the vest" hint:
  ///   1. DS18B20 disconnected     (temperature out of physiological band)
  ///   2. MPU6050 silent           (zero accel magnitude → I2C dead)
  ///   3. INMP441 silent           (zero RMS on both mics → I2S dead)
  ///   4. PPG all silent           (existing — MAX30102 init failure)
  ///   5. PPG no contact           (existing — user hasn't strapped on)
  static _BannerState? _evaluate(BleVestService vest) {
    if (vest.status != BleStatus.connected) return null;
    final v = vest.latestVitals;
    if (v == null) return null;

    // 1. DS18B20 — at least one zone outside 25–45 °C means a probe
    //    is disconnected (returning -127 sentinel) or held wrong.
    final temps = <double>[v.tl, v.tr, v.tc];
    final tempBroken = temps.where((t) => t < _tempMinC || t > _tempMaxC).length;
    if (tempBroken == temps.length) return _BannerState.tempSilent;

    // 2. MPU6050 — gravity should always show. Use the upper IMU
    //    (the one mounted to the vest body — lower is on the abdomen
    //    monitor and may not be paired).
    final upperMag = _magnitude(v.upperAccelX, v.upperAccelY, v.upperAccelZ);
    if (upperMag < _accelGravityFloor) return _BannerState.imuSilent;

    // 3. INMP441 — zero RMS on both analog + digital mics for the
    //    current frame. (One mic alone could be silent legitimately;
    //    both at hard-zero means the I2S bus didn't init.)
    if (v.analogRms < _audioFloor && v.digitalRms < _audioFloor) {
      return _BannerState.audioSilent;
    }

    // 4 + 5. PPG — original logic, unchanged.
    final readings = <double>[v.ir1, v.ir2, v.ira];
    final contacting = readings.where((r) => r >= _contactThreshold).length;
    if (contacting > 0) return null;        // at least one probe is on skin → fine

    final allSilent = readings.every((r) => r == 0.0);
    if (allSilent) return _BannerState.silent;
    return _BannerState.noContact;
  }

  static double _magnitude(double x, double y, double z) {
    return (x * x + y * y + z * z).abs(); // sum of squares; floor compares
    // No sqrt needed — _accelGravityFloor² ≈ 0.01, and the comparison
    // direction is preserved. Cheaper than sqrt on every render.
  }
}

enum _BannerState { noContact, silent, tempSilent, imuSilent, audioSilent }

class _Banner extends StatelessWidget {
  final _BannerState state;
  const _Banner({required this.state});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final (icon, title, body, accent) = switch (state) {
      _BannerState.noContact => (
        Icons.touch_app_rounded,
        'Please wear the vest',
        'No skin contact detected on any pulse-oximeter site. Strap '
            'the vest on so MedVerse can read your live vitals.',
        cs.tertiary,
      ),
      _BannerState.silent => (
        Icons.report_problem_rounded,
        'Vest sensors not responding',
        'The pulse-oximeter probes are reading zero counts. Re-seat '
            'the vest, then check Sensors → Sensor health.',
        cs.error,
      ),
      _BannerState.tempSilent => (
        Icons.thermostat_outlined,
        'Temperature sensor disconnected',
        'All three skin-temp probes are reading outside the '
            'physiological band — likely a probe is unseated. Open '
            'Sensors → Sensor health for details.',
        cs.error,
      ),
      _BannerState.imuSilent => (
        Icons.explore_off_outlined,
        'Motion sensor not reporting',
        'The MPU6050 IMU is silent (no gravity reading). The I2C bus '
            'may have dropped — try reseating the vest or restarting it.',
        cs.error,
      ),
      _BannerState.audioSilent => (
        Icons.mic_off_outlined,
        'Audio sensor silent',
        'Neither chest microphone is producing readings. The I2S bus '
            'may not have initialised — restart the vest if this persists.',
        cs.error,
      ),
    };

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      child: Semantics(
        liveRegion: true,
        label: '$title. $body',
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: accent.withValues(alpha: 0.4)),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                accent.withValues(alpha: 0.18),
                cs.surfaceContainerLow,
              ],
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: accent.withValues(alpha: 0.22),
                  boxShadow: [
                    BoxShadow(
                      color: accent.withValues(alpha: 0.35),
                      blurRadius: 12,
                      spreadRadius: 1,
                    ),
                  ],
                ),
                child: Icon(icon, color: accent, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      body,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: cs.onSurfaceVariant,
                          ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// Suppresses an unused-import warning while preserving the explicit
// dependency on the BLE payload parser — kept so the file is
// self-documenting about what the contact threshold operates on.
// ignore: unused_element
VestVitals? _bindVestVitalsType() => null;
