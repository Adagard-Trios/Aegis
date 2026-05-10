import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

/// The bottom-of-screen input row for [ChatScreen].
///
/// Three controls: image attach, multi-line TextField (auto-grow up to
/// 4 lines), send button. Image attach sources from the camera; the
/// caller can swap to gallery via a long-press if desired.
///
/// Every control is wrapped in semantics + ≥48 px tap targets so
/// TalkBack / large-finger users hit cleanly.
class ChatComposer extends StatefulWidget {
  /// Hint shown inside the TextField — usually "Ask the {persona}…".
  final String hint;

  /// Called when the user taps Send. Returns the trimmed text + the
  /// optional image path; the screen owns the actual API call.
  final Future<void> Function(String text, String? imagePath) onSend;

  /// True when an in-flight reply is being awaited. Disables Send +
  /// shows a tiny progress indicator inside the button.
  final bool isLoading;

  const ChatComposer({
    super.key,
    required this.hint,
    required this.onSend,
    required this.isLoading,
  });

  @override
  State<ChatComposer> createState() => _ChatComposerState();
}

class _ChatComposerState extends State<ChatComposer> {
  final _controller = TextEditingController();
  final _picker = ImagePicker();
  XFile? _image;

  Future<void> _pickFromCamera() async {
    try {
      final f = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 80,
      );
      if (f != null && mounted) {
        setState(() => _image = f);
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Camera unavailable: $e')),
      );
    }
  }

  Future<void> _pickFromGallery() async {
    try {
      final f = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 80,
      );
      if (f != null && mounted) {
        setState(() => _image = f);
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Gallery unavailable: $e')),
      );
    }
  }

  Future<void> _sourceSheet() async {
    await showModalBottomSheet<void>(
      context: context,
      builder: (_) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('Take photo'),
              onTap: () {
                Navigator.pop(context);
                _pickFromCamera();
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('Choose from gallery'),
              onTap: () {
                Navigator.pop(context);
                _pickFromGallery();
              },
            ),
            if (_image != null)
              ListTile(
                leading: const Icon(Icons.close),
                title: const Text('Remove attachment'),
                onTap: () {
                  setState(() => _image = null);
                  Navigator.pop(context);
                },
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    final imagePath = _image?.path;
    if (text.isEmpty && imagePath == null) return;
    if (widget.isLoading) return;
    _controller.clear();
    setState(() => _image = null);
    await widget.onSend(text, imagePath);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SafeArea(
      top: false,
      child: Container(
        padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerLow,
          border: Border(top: BorderSide(color: theme.colorScheme.outlineVariant)),
        ),
        child: Column(
          children: [
            // Image preview strip — only when an image is staged.
            if (_image != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image.file(
                        File(_image!.path),
                        width: 56,
                        height: 56,
                        fit: BoxFit.cover,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Image attached',
                        style: theme.textTheme.bodySmall,
                      ),
                    ),
                    Semantics(
                      button: true,
                      label: 'Remove attached image',
                      child: IconButton(
                        icon: const Icon(Icons.close),
                        onPressed: () => setState(() => _image = null),
                      ),
                    ),
                  ],
                ),
              ),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Semantics(
                  button: true,
                  label: 'Attach image from camera or gallery',
                  child: IconButton(
                    icon: const Icon(Icons.add_photo_alternate_outlined),
                    onPressed: widget.isLoading ? null : _sourceSheet,
                    tooltip: 'Attach image',
                  ),
                ),
                Expanded(
                  child: TextField(
                    controller: _controller,
                    minLines: 1,
                    maxLines: 4,
                    enabled: !widget.isLoading,
                    keyboardType: TextInputType.multiline,
                    textInputAction: TextInputAction.newline,
                    decoration: InputDecoration(
                      hintText: widget.hint,
                      filled: true,
                      fillColor: theme.colorScheme.surfaceContainerHigh,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide.none,
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 12),
                    ),
                  ),
                ),
                const SizedBox(width: 4),
                Semantics(
                  button: true,
                  label: 'Send message',
                  child: IconButton.filled(
                    icon: widget.isLoading
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                                strokeWidth: 2, color: Colors.white),
                          )
                        : const Icon(Icons.send_rounded),
                    onPressed: widget.isLoading ? null : _send,
                    tooltip: 'Send',
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
