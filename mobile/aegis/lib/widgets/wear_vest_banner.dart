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
  static _BannerState? _evaluate(BleVestService vest) {
    if (vest.status != BleStatus.connected) return null;
    final v = vest.latestVitals;
    if (v == null) return null;

    final readings = <double>[v.ir1, v.ir2, v.ira];
    final contacting = readings.where((r) => r >= _contactThreshold).length;
    if (contacting > 0) return null;        // at least one probe is on skin → fine

    // All three < threshold. Distinguish "all silent (=0)" — which is
    // a hardware fault, not a wear issue — from "all at LED-only floor"
    // — which means the user just hasn't strapped the vest on.
    final allSilent = readings.every((r) => r == 0.0);
    if (allSilent) return _BannerState.silent;
    return _BannerState.noContact;
  }
}

enum _BannerState { noContact, silent }

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
