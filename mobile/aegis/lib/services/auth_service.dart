import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'api_config.dart';

/// JWT auth + secure token storage.
///
/// Backend auth is opt-in (`MEDVERSE_AUTH_ENABLED=true`). Until the flag
/// flips, `POST /api/auth/login` still returns a token but the rest of
/// the API accepts unauthenticated traffic too — so the app works either
/// way. The token, when stored, is attached as a `Bearer` header on
/// every outbound request via [AuthService.authHeaders].
class AuthService extends ChangeNotifier {
  static const _tokenKey = 'medverse_token';
  static const _userKey = 'medverse_username';

  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String? _token;
  String? _username;

  /// Whether the backend requires JWT auth (server-side
  /// `MEDVERSE_AUTH_ENABLED=true`). Defaults to **false** so a fresh
  /// `flutter run` against a vanilla backend works without a login —
  /// `probeBackend()` upgrades this to `true` only when /health says
  /// auth is required, at which point GoRouter's redirect kicks in
  /// and bounces the user to /login.
  bool _authRequired = false;
  bool get authRequired => _authRequired;

  String? get token => _token;
  String? get username => _username;
  bool get isAuthenticated => _token != null && _token!.isNotEmpty;

  /// True when the auth gate should block the user from app routes —
  /// i.e. backend requires auth AND we don't have a token yet. The
  /// router's redirect callback reads this.
  bool get requiresLogin => _authRequired && !isAuthenticated;

  Future<void> load() async {
    try {
      _token = await _storage.read(key: _tokenKey);
      _username = await _storage.read(key: _userKey);
    } catch (e) {
      debugPrint('AuthService.load error: $e');
    }
    notifyListeners();
  }

  /// Hit /health to learn whether the backend requires auth. Fire-and-
  /// forget — the router listens to this notifier and re-runs its
  /// redirect when [_authRequired] flips. Safe to call repeatedly.
  Future<void> probeBackend() async {
    try {
      final res = await http
          .get(Uri.parse('${ApiConfig.baseUrl}/health'))
          .timeout(const Duration(seconds: 90));
      if (res.statusCode != 200) return;
      final body = jsonDecode(res.body) as Map<String, dynamic>;
      final flag = body['auth_enabled'];
      if (flag is bool && flag != _authRequired) {
        _authRequired = flag;
        notifyListeners();
      }
    } catch (e) {
      // Probe failure is non-fatal — keep the open-by-default state so
      // an unreachable backend doesn't lock the user out.
      debugPrint('AuthService.probeBackend error: $e');
    }
  }

  Future<bool> login(String username, String password) async {
    try {
      final res = await http.post(
        Uri.parse('${ApiConfig.baseUrl}/api/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      );
      if (res.statusCode != 200) return false;
      final body = jsonDecode(res.body) as Map<String, dynamic>;
      final tok = body['access_token'] as String?;
      if (tok == null || tok.isEmpty) return false;
      _token = tok;
      _username = username;
      await _storage.write(key: _tokenKey, value: tok);
      await _storage.write(key: _userKey, value: username);
      notifyListeners();
      return true;
    } catch (e) {
      debugPrint('AuthService.login error: $e');
      return false;
    }
  }

  Future<void> logout() async {
    _token = null;
    _username = null;
    try {
      await _storage.delete(key: _tokenKey);
      await _storage.delete(key: _userKey);
    } catch (e) {
      debugPrint('AuthService.logout error: $e');
    }
    notifyListeners();
  }

  /// Bearer header injection used by every API call.
  Map<String, String> authHeaders({Map<String, String>? extra}) {
    final headers = <String, String>{...?extra};
    if (_token != null && _token!.isNotEmpty) {
      headers['Authorization'] = 'Bearer $_token';
    }
    return headers;
  }

  /// Query-param form for SSE `/stream` (EventSource equivalents can't
  /// carry headers).
  String appendToken(Uri uri) {
    if (_token == null || _token!.isEmpty) return uri.toString();
    final qp = Map<String, String>.from(uri.queryParameters);
    qp['token'] = _token!;
    return uri.replace(queryParameters: qp).toString();
  }
}
