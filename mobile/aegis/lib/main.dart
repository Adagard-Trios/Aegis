import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'theme.dart';
import 'main_layout.dart';
import 'models/vest_data_model.dart';
import 'services/vest_stream_service.dart';

void main() {
  final vestDataModel = VestDataModel();
  final vestStreamService = VestStreamService(model: vestDataModel);
  // Start the background stream connection immediately
  vestStreamService.startStream();

  runApp(
    MultiProvider(
      providers: [
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
      title: 'Aegis IoT Clinical Dashboard',
      debugShowCheckedModeBanner: false,
      theme: AegisTheme.darkTheme,
      home: const MainLayout(),
    );
  }
}
