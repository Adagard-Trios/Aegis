import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../services/api_config.dart';
import '../theme.dart';

class Vest3DViewer extends StatefulWidget {
  const Vest3DViewer({super.key});

  @override
  State<Vest3DViewer> createState() => _Vest3DViewerState();
}

class _Vest3DViewerState extends State<Vest3DViewer> {
  late final WebViewController _controller;

  @override
  void initState() {
    super.initState();
    final url = '${ApiConfig.frontendUrl}/vest-viewer';

    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(Colors.transparent)
      ..loadRequest(Uri.parse(url));
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Container(
        height: 300,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: MedVerseTheme.surface,
        ),
        child: Stack(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: WebViewWidget(controller: _controller),
            ),
            const Positioned(
              top: 16, left: 16,
              child: Text(
                'LIVE VEST MODEL',
                style: TextStyle(color: MedVerseTheme.primary, fontWeight: FontWeight.bold, letterSpacing: 1.5, fontSize: 10),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
