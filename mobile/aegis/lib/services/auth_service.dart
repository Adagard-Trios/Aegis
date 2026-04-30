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

  String? get token => _token;
  String? get username => _username;
  bool get isAuthenticated => _token != null && _token!.isNotEmpty;

  Future<void> load() async {
    try {
      _token = await _storage.read(key: _tokenKey);
      _username = await _storage.read(key: _userKey);
    } catch (e) {
      debugPrint('AuthService.load error: $e');
    }
    notifyListeners();
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
