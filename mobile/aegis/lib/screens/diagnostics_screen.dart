import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:image_picker/image_picker.dart';
import '../theme.dart';

class DiagnosticsScreen extends StatefulWidget {
  const DiagnosticsScreen({super.key});

  @override
  State<DiagnosticsScreen> createState() => _DiagnosticsScreenState();
}

class _DiagnosticsScreenState extends State<DiagnosticsScreen> {
  final TextEditingController _controller = TextEditingController();
  final ImagePicker _picker = ImagePicker();
  XFile? _selectedImage;
  
  final List<Message> _messages = [
    Message(text: "Hello, I am your Aegis A.I. Medical Expert. I have active streaming access to your telemetry hardware. How can I assist you today?", isUser: false),
  ];
  bool _isLoading = false;

  Future<void> _pickImage() async {
    try {
      final XFile? pickedFile = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 80,
      );
      if (pickedFile != null) {
        setState(() {
          _selectedImage = pickedFile;
        });
      }
    } catch (e) {
      debugPrint("Error picking image: $e");
    }
  }

  void _sendMessage() async {
    final text = _controller.text.trim();
    final imagePath = _selectedImage?.path;
    
    if (text.isEmpty && imagePath == null) return;

    setState(() {
      _messages.add(Message(text: text, isUser: true, imagePath: imagePath));
      _isLoading = true;
      _selectedImage = null; // Clear image after sending
    });
    _controller.clear();

    // Mock API Delay
    await Future.delayed(const Duration(seconds: 2));

    if (mounted) {
      setState(() {
        _isLoading = false;
        _messages.add(Message(
          text: "**Analysis Complete**: Based on the context provided, I have registered the visual evidence. Please ensure you monitor for any change in symptom spread. My live telemetry continues to show stable vitals.",
          isUser: false,
        ));
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: _messages.length,
            itemBuilder: (context, index) {
              final msg = _messages[index];
              return Container(
                margin: const EdgeInsets.only(bottom: 16),
                alignment: msg.isUser ? Alignment.centerRight : Alignment.centerLeft,
                child: Column(
                  crossAxisAlignment: msg.isUser ? CrossAxisAlignment.end : CrossAxisAlignment.start,
                  children: [
                    if (msg.imagePath != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8.0),
                        child: Container(
                          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.7),
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: AegisTheme.primary.withOpacity(0.3)),
                          ),
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: Image.file(File(msg.imagePath!), fit: BoxFit.cover),
                          ),
                        ),
                      ),
                    if (msg.text.isNotEmpty)
                      Container(
                        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.8),
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: msg.isUser ? AegisTheme.primary.withOpacity(0.2) : AegisTheme.surfaceHighlight,
                          borderRadius: BorderRadius.circular(16).copyWith(
                            bottomRight: msg.isUser ? const Radius.circular(4) : const Radius.circular(16),
                            bottomLeft: !msg.isUser ? const Radius.circular(4) : const Radius.circular(16),
                          ),
                          border: msg.isUser ? Border.all(color: AegisTheme.primary.withOpacity(0.5)) : null,
                        ),
                        child: MarkdownBody(
                          data: msg.text,
                          styleSheet: MarkdownStyleSheet(
                            p: const TextStyle(color: AegisTheme.textMain, fontSize: 14),
                            strong: const TextStyle(color: AegisTheme.accent, fontWeight: FontWeight.bold),
                          ),
                        ),
                      ),
                  ],
                ),
              );
            },
          ),
        ),
        if (_isLoading)
          const Padding(
            padding: EdgeInsets.all(8.0),
            child: CircularProgressIndicator(color: AegisTheme.primary),
          ),
        
        // --- IMAGE PREVIEW WIDGET ---
        if (_selectedImage != null)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: AegisTheme.surfaceHighlight,
            child: Row(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.file(File(_selectedImage!.path), width: 60, height: 60, fit: BoxFit.cover),
                ),
                const SizedBox(width: 12),
                const Expanded(child: Text("Ready to send...", style: TextStyle(color: AegisTheme.textMuted, fontSize: 12))),
                IconButton(
                  icon: const Icon(Icons.close_rounded, color: Colors.red),
                  onPressed: () => setState(() => _selectedImage = null),
                ),
              ],
            ),
          ),

        Container(
          padding: const EdgeInsets.all(8.0).copyWith(bottom: 24),
          decoration: const BoxDecoration(
            color: AegisTheme.surface,
            border: Border(top: BorderSide(color: AegisTheme.surfaceHighlight)),
          ),
          child: Row(
            children: [
              IconButton(
                icon: const Icon(Icons.camera_alt_rounded, color: AegisTheme.primary),
                onPressed: _pickImage,
              ),
              Expanded(
                child: TextField(
                  controller: _controller,
                  style: const TextStyle(color: AegisTheme.textMain),
                  decoration: InputDecoration(
                    hintText: 'Ask the Expert A.I...',
                    hintStyle: const TextStyle(color: AegisTheme.textMuted),
                    filled: true,
                    fillColor: AegisTheme.background,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide.none,
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  ),
                  onSubmitted: (_) => _sendMessage(),
                ),
              ),
              const SizedBox(width: 8),
              CircleAvatar(
                backgroundColor: AegisTheme.primary,
                child: IconButton(
                  icon: const Icon(Icons.send_rounded, color: Colors.white),
                  onPressed: _sendMessage,
                ),
              )
            ],
          ),
        )
      ],
    );
  }
}

class Message {
  final String text;
  final bool isUser;
  final String? imagePath;
  Message({required this.text, required this.isUser, this.imagePath});
}
