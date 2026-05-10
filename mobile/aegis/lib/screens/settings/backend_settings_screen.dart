import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:provider/provider.dart';

import '../../services/api_config.dart';
import '../../services/api_service.dart';
import '../../services/auth_service.dart';

/// Backend connection screen. Lets the user override the FastAPI URL
/// (defaults to `10.0.2.2:8000` on Android emulator, `localhost:8000`
/// elsewhere) and run a live ping to confirm the chosen target answers.
///
/// Persists the override to `flutter_secure_storage`; loaded by main()
/// at app start so the choice survives restarts.
class BackendSettingsScreen extends StatefulWidget {
  const BackendSettingsScreen({super.key});

  @override
  State<BackendSettingsScreen> createState() => _BackendSettingsScreenState();
}

class _BackendSettingsScreenState extends State<BackendSettingsScreen> {
  static const _key = 'aegis.backend_url_override';
  final _storage = const FlutterSecureStorage();
  final _ctrl = TextEditingController();

  bool _loading = true;
  bool _testing = false;

  @override
  void initState() {
    super.initState();
    _restore();
  }

  Future<void> _restore() async {
    try {
      _ctrl.text = await _storage.read(key: _key) ?? '';
    } catch (_) {/* non-fatal */}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _save() async {
    final url = _ctrl.text.trim();
    try {
      if (url.isEmpty) {
        await _storage.delete(key: _key);
        ApiConfig.setOverride(null);
      } else {
        await _storage.write(key: _key, value: url);
        ApiConfig.setOverride(url);
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(url.isEmpty ? 'Override cleared' : 'Override saved: $url'),
      ));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Save failed: $e')),
      );
    }
  }

  Future<void> _test() async {
    setState(() => _testing = true);
    final auth = context.read<AuthService>();
    try {
      // /api/history is a tiny GET — perfect ping. Returns null on
      // failure (network error or 4xx/5xx); empty list when there's
      // no data yet but the connection works.
      final resp = await ApiService.fetchHistory(limit: 1, auth: auth);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(resp == null
            ? 'Backend unreachable at ${ApiConfig.baseUrl}'
            : 'Backend OK at ${ApiConfig.baseUrl} (${resp.length} rows)'),
      ));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Test failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _testing = false);
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 16),
      children: [
        Text(
          'Active backend',
          style: theme.textTheme.labelMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 4),
        Text(ApiConfig.baseUrl, style: theme.textTheme.titleMedium),
        const SizedBox(height: 24),
        TextField(
          controller: _ctrl,
          decoration: const InputDecoration(
            labelText: 'Override URL',
            hintText: 'http://192.168.1.42:8000',
            border: OutlineInputBorder(),
            helperText:
                'Leave blank to fall back to the per-platform default',
          ),
          keyboardType: TextInputType.url,
        ),
        const SizedBox(height: 24),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                icon: const Icon(Icons.save_outlined),
                label: const Text('Save'),
                onPressed: _save,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: OutlinedButton.icon(
                icon: _testing
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.cloud_done_outlined),
                label: Text(_testing ? 'Testing…' : 'Test connection'),
                onPressed: _testing ? null : _test,
              ),
            ),
          ],
        ),
      ],
    );
  }
}
