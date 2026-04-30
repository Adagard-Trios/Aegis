import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'theme.dart';
import 'main_layout.dart';
import 'screens/login_screen.dart';
import 'models/vest_data_model.dart';
import 'services/vest_stream_service.dart';
import 'services/auth_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final auth = AuthService();
  await auth.load();

  final vestDataModel = VestDataModel();
  final vestStreamService = VestStreamService(model: vestDataModel, auth: auth);
  // Start the background stream connection immediately
  vestStreamService.startStream();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider.value(value: auth),
        ChangeNotifierProvider.value(value: vestDataModel),
        Provider.value(value: vestStreamService),
      ],
      child: const AegisApp(),
    ),
  );
}

class AegisApp extends StatelessWidget {
  const AegisApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MedVerse IoT Clinical Dashboard',
      debugShowCheckedModeBanner: false,
      theme: MedVerseTheme.darkTheme,
      home: const _AuthGate(),
    );
  }
}

/// Presents [LoginScreen] when no token is stored; otherwise the dashboard.
///
/// Auth is opt-in at the backend (`MEDVERSE_AUTH_ENABLED`). The login
/// call still works when auth is off — it just returns a token that the
/// backend accepts but doesn't require. Set
/// [AuthGateMode.requireLogin] to `false` if you want to bypass the
/// gate entirely for unauthenticated demos.
class _AuthGate extends StatelessWidget {
  const _AuthGate();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    if (auth.isAuthenticated) return const MainLayout();
    return const LoginScreen();
  }
}
