import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../services/patient_profile_service.dart';
import '../services/vest_stream_service.dart';
import '../widgets/chat/composer.dart';
import '../widgets/chat/experts.dart';
import '../widgets/chat/message_bubble.dart';

/// Multi-specialty chat screen. Replaces the legacy [DiagnosticsScreen]
/// which used a 2 s `Future.delayed` mock + hardcoded reply.
///
/// Layout (top to bottom):
///   - AppBar with title + clear-conversation action
///   - PersonaChipBar selecting which specialty agent to talk to
///   - Scrolling list of [ChatMessageBubble]s
///   - [ChatComposer] (image attach + multi-line TextField + send)
///
/// Send wires to `ApiService.agentAsk` — POST `/api/agent/ask` with the
/// selected specialty, message text, and the freshest local snapshot
/// from the [VestStreamService] so the agent reasons over current
/// telemetry. Reply renders as markdown via `flutter_markdown` inside
/// the bubble.
///
/// Selected persona persists across app restarts via `flutter_secure_storage`.
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  static const _personaKey = 'aegis.chat_persona_v1';
  final _storage = const FlutterSecureStorage();
  final _scrollController = ScrollController();

  ExpertPersona _persona = expertPersonas[0];
  final List<_ChatMessage> _messages = [];
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _restorePersona();
    // Prepend a contextual greeting matching the active persona.
    _messages.add(
      _ChatMessage(
        isUser: false,
        text: _greetingFor(_persona),
        personaLabel: _persona.label,
      ),
    );
  }

  Future<void> _restorePersona() async {
    try {
      final stored = await _storage.read(key: _personaKey);
      if (stored != null && mounted) {
        final restored = expertPersonaById(stored);
        setState(() {
          _persona = restored;
          // Replace the seeded greeting with one tailored to the
          // restored persona (so the user doesn't see "Hi from GP" when
          // they last had Cardiologist selected).
          if (_messages.length == 1 && !_messages.first.isUser) {
            _messages[0] = _ChatMessage(
              isUser: false,
              text: _greetingFor(_persona),
              personaLabel: _persona.label,
            );
          }
        });
      }
    } catch (_) {/* secure storage failure is non-fatal */}
  }

  Future<void> _persistPersona(ExpertPersona p) async {
    try {
      await _storage.write(key: _personaKey, value: p.id);
    } catch (_) {/* non-fatal */}
  }

  String _greetingFor(ExpertPersona p) {
    return "Hi — I'm your **${p.label}** assistant. Ask anything about "
        "your current vitals, recent symptoms, or what to do next. I have "
        "live access to your telemetry stream.";
  }

  void _onPersonaSelected(ExpertPersona p) {
    if (p.id == _persona.id) return;
    setState(() => _persona = p);
    _persistPersona(p);
    // Add a system-style note so the user sees the persona switched.
    _messages.add(
      _ChatMessage(
        isUser: false,
        text: '*Switched to **${p.label}***',
        personaLabel: p.label,
      ),
    );
    _scrollToBottom();
  }

  void _clearConversation() {
    setState(() {
      _messages
        ..clear()
        ..add(
          _ChatMessage(
            isUser: false,
            text: _greetingFor(_persona),
            personaLabel: _persona.label,
          ),
        );
    });
  }

  Future<void> _send(String text, String? imagePath) async {
    if (text.isEmpty && imagePath == null) return;
    setState(() {
      _messages.add(_ChatMessage(
        isUser: true,
        text: text,
        imagePath: imagePath,
        personaLabel: _persona.label,
      ));
      _isLoading = true;
    });
    _scrollToBottom();

    try {
      // Pull the freshest snapshot off the stream service so the agent
      // has live HR/SpO2/temp/etc. context.
      final stream = context.read<VestStreamService>();
      final snapshot = stream.latestSnapshot;
      // Auth shim — backend MEDVERSE_AUTH_ENABLED=false accepts empty
      // headers, but pass through regardless so a future flip of the
      // flag doesn't silently break this path.
      final auth = context.read<AuthService>();
      // Patient identity + clinical notes so the LLM can ground its
      // answer in who the patient actually is.
      final profile = context.read<PatientProfileService>();

      // Compose the message — if an image is attached, mention it in
      // the prompt so the agent knows imaging is available.
      final composed = imagePath != null
          ? '$text\n\n[Patient attached an image at $imagePath]'.trim()
          : text;

      // Last few turns for multi-turn context. Cap at 6 (3 user + 3
      // assistant) to keep the request body bounded — older turns are
      // semantically less important than the latest exchange.
      final history = _recentHistoryForApi(maxTurns: 6);

      final reply = await ApiService.agentAsk(
        specialty: _persona.id,
        message: composed.isEmpty ? 'Please review my current state.' : composed,
        snapshot: snapshot,
        patientId: profile.patientId,
        patientProfile: profile.agentPayload,
        history: history,
        auth: auth,
      );

      if (!mounted) return;

      setState(() {
        _isLoading = false;
        if (reply == null) {
          _messages.add(_ChatMessage(
            isUser: false,
            text: '⚠ Could not reach the AI agent. Check your backend '
                'connection in Settings → Connection.',
            personaLabel: _persona.label,
          ));
        } else {
          // ApiService.agentAsk returns {reply, severity, severity_score, specialty}
          final answer = (reply['reply'] as String?) ?? '(no response)';
          _messages.add(_ChatMessage(
            isUser: false,
            text: answer,
            personaLabel: _persona.label,
          ));
        }
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _messages.add(_ChatMessage(
          isUser: false,
          text: '⚠ Request failed: $e',
          personaLabel: _persona.label,
        ));
      });
      debugPrint('[ChatScreen] agentAsk failed: $e');
    }
  }

  /// Build the chat history payload sent to the agent. Skips the seeded
  /// greeting + persona-switch system bubbles (no question/answer
  /// information for the LLM) and walks backwards to keep the most
  /// recent [maxTurns] real exchanges.
  List<Map<String, String>> _recentHistoryForApi({int maxTurns = 6}) {
    // The current turn (just appended above as `isUser: true`) is the
    // one being asked NOW — exclude it from "history".
    final past = _messages.length > 1
        ? _messages.sublist(0, _messages.length - 1)
        : const <_ChatMessage>[];

    final out = <Map<String, String>>[];
    for (final m in past.reversed) {
      // Skip persona-switch / greeting markers — they start with '*' or
      // are the very first assistant bubble with no user before it.
      final trimmed = m.text.trim();
      if (!m.isUser && (trimmed.startsWith('*Switched to') || trimmed.startsWith('Hi —'))) {
        continue;
      }
      out.add({
        'role': m.isUser ? 'user' : 'assistant',
        'content': m.text,
      });
      if (out.length >= maxTurns) break;
    }
    return out.reversed.toList(growable: false);
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOutCubic,
      );
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      backgroundColor: theme.colorScheme.surface,
      appBar: AppBar(
        title: const Text('Chat'),
        actions: [
          Semantics(
            button: true,
            label: 'Clear conversation',
            child: IconButton(
              icon: const Icon(Icons.delete_sweep_outlined),
              tooltip: 'Clear conversation',
              onPressed: _messages.length > 1 ? _clearConversation : null,
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          // Persona picker — extracted to its own widget for clarity.
          _PersonaBar(
            selected: _persona,
            onSelected: _onPersonaSelected,
          ),
          const Divider(height: 1),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              itemCount: _messages.length + (_isLoading ? 1 : 0),
              itemBuilder: (context, i) {
                if (i == _messages.length && _isLoading) {
                  return ChatTypingIndicator(personaLabel: _persona.label);
                }
                final m = _messages[i];
                return ChatMessageBubble(
                  isUser: m.isUser,
                  text: m.text,
                  imagePath: m.imagePath,
                  personaLabel: m.personaLabel,
                );
              },
            ),
          ),
          ChatComposer(
            hint: 'Ask the ${_persona.label}…',
            isLoading: _isLoading,
            onSend: _send,
          ),
        ],
      ),
    );
  }
}

class _PersonaBar extends StatelessWidget {
  final ExpertPersona selected;
  final ValueChanged<ExpertPersona> onSelected;
  const _PersonaBar({required this.selected, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    // Imported lazily to avoid circular dep; in practice the
    // PersonaChipBar widget already handles every styling case.
    return _PersonaChipBarInline(selected: selected, onSelected: onSelected);
  }
}

class _PersonaChipBarInline extends StatelessWidget {
  final ExpertPersona selected;
  final ValueChanged<ExpertPersona> onSelected;
  const _PersonaChipBarInline({required this.selected, required this.onSelected});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SizedBox(
      height: 56,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        itemCount: expertPersonas.length,
        separatorBuilder: (_, _) => const SizedBox(width: 8),
        itemBuilder: (context, i) {
          final p = expertPersonas[i];
          final isSelected = p.id == selected.id;
          return Semantics(
            button: true,
            selected: isSelected,
            label: 'Talk to ${p.label}',
            child: FilterChip(
              selected: isSelected,
              onSelected: (_) => onSelected(p),
              avatar: Icon(
                p.icon,
                size: 18,
                color: isSelected
                    ? theme.colorScheme.onSecondaryContainer
                    : p.accent,
              ),
              label: Text(p.label),
              labelStyle: theme.textTheme.labelLarge?.copyWith(
                color: isSelected
                    ? theme.colorScheme.onSecondaryContainer
                    : theme.colorScheme.onSurface,
              ),
              side: BorderSide(
                color: isSelected
                    ? Colors.transparent
                    : theme.colorScheme.outlineVariant,
              ),
            ),
          );
        },
      ),
    );
  }
}

class _ChatMessage {
  final bool isUser;
  final String text;
  final String? imagePath;
  final String? personaLabel;
  _ChatMessage({
    required this.isUser,
    required this.text,
    this.imagePath,
    this.personaLabel,
  });
}
