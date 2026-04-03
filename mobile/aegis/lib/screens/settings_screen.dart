import 'package:flutter/material.dart';
import '../theme.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16.0),
      children: [
        const ListTile(
          leading: Icon(Icons.person_rounded, color: MedVerseTheme.primary),
          title: Text('Patient Profile'),
          subtitle: Text('Manage biographical data'),
          trailing: Icon(Icons.chevron_right_rounded),
        ),
        const Divider(),
        const ListTile(
          leading: Icon(Icons.router_rounded, color: MedVerseTheme.primary),
          title: Text('Vest Connection'),
          subtitle: Text('Configure IoT endpoint'),
          trailing: Icon(Icons.chevron_right_rounded),
        ),
        const Divider(),
        ListTile(
          leading: const Icon(Icons.notifications_active_rounded, color: MedVerseTheme.primary),
          title: const Text('Alert Thresholds'),
          subtitle: const Text('Customize warning bounds'),
          trailing: Switch(value: true, onChanged: (v) {}, activeColor: MedVerseTheme.primary),
        ),
      ],
    );
  }
}
