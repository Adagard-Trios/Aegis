import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/local_cache_service.dart';
import '../services/edge_anomaly_service.dart';
import '../services/sync_queue_service.dart';
import '../models/vest_data_model.dart';

/// Offline-mode banner.
///
/// Drop on top of any screen that wants the IoMT-style "I am offline /
/// I am replaying / I have an alert" surface. Subscribes to:
///   - VestDataModel.connected → online vs offline
///   - SyncQueueService → "N cached" pill while waiting to flush
///   - EdgeAnomalyService → red bar when an alert is active
///
/// Tap on the alert bar acknowledges it (clears the active flag) so
/// the clinician can dismiss without waiting for the underlying signal
/// to clear.
class OfflineBanner extends StatelessWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context) {
    final vest = context.watch<VestDataModel?>();
    final cache = context.watch<LocalCacheService?>();
    final anomaly = context.watch<EdgeAnomalyService?>();
    final queue = context.watch<SyncQueueService?>();

    final isOffline = vest != null && !vest.connected;
    final hasAnomaly = anomaly?.active == true;
    final queueDepth = queue?.length ?? 0;
    final cacheDepth = cache?.length ?? 0;

    if (!isOffline && !hasAnomaly && queueDepth == 0) {
      return const SizedBox.shrink();
    }

    final List<Widget> rows = [];
    if (hasAnomaly) {
      rows.add(_AlertBar(anomaly: anomaly!));
    }
    if (isOffline) {
      rows.add(_StatusBar(
        icon: Icons.cloud_off,
        color: Colors.amber,
        text: 'Offline — caching locally ($cacheDepth held, $queueDepth queued)',
      ));
    } else if (queue?.isFlushing == true) {
      rows.add(_StatusBar(
        icon: Icons.cloud_sync,
        color: Colors.blue,
        text: 'Reconnected — syncing $queueDepth cached snapshot${queueDepth == 1 ? '' : 's'}…',
      ));
    }

    return Column(mainAxisSize: MainAxisSize.min, children: rows);
  }
}

class _StatusBar extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String text;
  const _StatusBar({required this.icon, required this.color, required this.text});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      color: color.withValues(alpha: 0.15),
      child: Row(
        children: [
          Icon(icon, size: 16, color: color),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(fontSize: 12, color: color, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      ),
    );
  }
}

class _AlertBar extends StatelessWidget {
  final EdgeAnomalyService anomaly;
  const _AlertBar({required this.anomaly});

  @override
  Widget build(BuildContext context) {
    final reason = anomaly.reason.replaceAll('_', ' ');
    return InkWell(
      onTap: anomaly.acknowledge,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        color: Colors.red.withValues(alpha: 0.18),
        child: Row(
          children: [
            const Icon(Icons.warning_amber_rounded, size: 18, color: Colors.red),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                'Edge alert: $reason — tap to acknowledge',
                style: const TextStyle(fontSize: 12, color: Colors.red, fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
