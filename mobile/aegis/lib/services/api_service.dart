import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';

import 'api_config.dart';
import 'auth_service.dart';

/// Thin REST client for the MedVerse backend.
///
/// All methods accept an optional [AuthService] so the bearer token
/// (when present) is attached transparently. Existing callers that
/// don't pass one keep working — endpoints unauthenticated while
/// `MEDVERSE_AUTH_ENABLED=false` on the server.
class ApiService {
  static String get baseUrl => ApiConfig.baseUrl;

  static Map<String, String> _headers(AuthService? auth, {bool json = true}) {
    final headers = <String, String>{};
    if (json) headers['Content-Type'] = 'application/json';
    if (auth != null) headers.addAll(auth.authHeaders());
    return headers;
  }

  static Future<bool> setSimulationMode(String mode, {AuthService? auth}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/simulation/mode'),
        headers: _headers(auth),
        body: jsonEncode({'mode': mode}),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error setting simulation mode: $e');
      return false;
    }
  }

  static Future<bool> injectMedication(String medicationName, double dose, {AuthService? auth}) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/simulation/medicate'),
        headers: _headers(auth),
        body: jsonEncode({'medication': medicationName, 'dose': dose}),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error injecting medication: $e');
      return false;
    }
  }

  static Future<Map<String, dynamic>?> uploadLabResults(String filePath, {AuthService? auth}) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/upload-lab-results'));
      if (auth != null) request.headers.addAll(auth.authHeaders());
      request.files.add(await http.MultipartFile.fromPath('file', filePath));
      var response = await request.send();
      if (response.statusCode == 200) {
        var respString = await response.stream.bytesToString();
        return jsonDecode(respString);
      }
      return null;
    } catch (e) {
      debugPrint('Error uploading lab results: $e');
      return null;
    }
  }

  static Future<List<dynamic>?> fetchHistory({
    String resolution = '1h',
    int limit = 500,
    AuthService? auth,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/api/history').replace(
        queryParameters: {'resolution': resolution, 'limit': '$limit'},
      );
      final response = await http.get(uri, headers: _headers(auth, json: false));
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as List<dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('Error fetching history: $e');
      return null;
    }
  }
}
