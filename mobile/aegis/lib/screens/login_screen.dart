import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/auth_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _user = TextEditingController(text: 'medverse');
  final _pass = TextEditingController();
  bool _submitting = false;
  String? _error;

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    final auth = context.read<AuthService>();
    final ok = await auth.login(_user.text.trim(), _pass.text);
    if (!mounted) return;
    setState(() => _submitting = false);
    if (!ok) setState(() => _error = 'Invalid credentials or backend unreachable.');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 380),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Icon(Icons.shield_outlined, size: 40),
                  const SizedBox(height: 12),
                  Text(
                    'MedVerse sign-in',
                    style: Theme.of(context).textTheme.titleLarge,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Dev credentials default to medverse / medverse. Auth is opt-in at the backend.',
                    style: Theme.of(context).textTheme.bodySmall,
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 20),
                  TextField(
                    controller: _user,
                    decoration: const InputDecoration(labelText: 'Username'),
                    textInputAction: TextInputAction.next,
                    autofillHints: const [AutofillHints.username],
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _pass,
                    decoration: const InputDecoration(labelText: 'Password'),
                    obscureText: true,
                    autofillHints: const [AutofillHints.password],
                    onSubmitted: (_) => _submit(),
                  ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                  ],
                  const SizedBox(height: 20),
                  FilledButton(
                    onPressed: _submitting ? null : _submit,
                    child: _submitting
                        ? const SizedBox(
                            height: 16, width: 16,
                            child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('Sign in'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
