import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';
// ignore: depend_on_referenced_packages
import 'package:webview_flutter_android/webview_flutter_android.dart';
import 'dart:io' show Platform;
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
    String url = 'http://localhost:3000/vest-viewer';
    try {
      if (Platform.isAndroid) url = 'http://10.0.2.2:3000/vest-viewer';
    } catch (_) {}

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
          color: AegisTheme.surface,
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
                style: TextStyle(color: AegisTheme.primary, fontWeight: FontWeight.bold, letterSpacing: 1.5, fontSize: 10),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
