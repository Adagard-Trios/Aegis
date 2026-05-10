import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';

import '../ble/ble_constants.dart';
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

  /// Host for `/api/agent/*` calls. Defaults to the HF Spaces deployment
  /// because Render free tier OOMs on LangGraph. Override via Settings or
  /// `--dart-define=AI_URL=...`. See [ApiConfig.aiBaseUrl].
  static String get aiBaseUrl => ApiConfig.aiBaseUrl;

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

  // ── Agent + digital-twin calls ───────────────────────────────────
  // These attach the freshest local snapshot in the body so the backend
  // graph runs against current data. The X-Aegis-Source header tells
  // the backend that mobile is the BLE master and that its own BLE
  // thread should back off for ~60s.

  static Map<String, String> _agentHeaders(AuthService? auth) {
    return {
      ..._headers(auth),
      BleTuning.mobileSourceHeader: BleTuning.mobileSourceValue,
    };
  }

  /// POST /api/agent/ask — single-specialty Q&A.
  /// Backend pydantic schema names this field `message` — keep parity.
  ///
  /// [history] is the prior chat turns (last N, capped client-side) so
  /// follow-up questions like "can you elaborate?" have context.
  /// [patientProfile] carries display_name + clinical notes; the AI
  /// graph reads them via `shared_context.patient_profile`.
  static Future<Map<String, dynamic>?> agentAsk({
    required String specialty,
    required String message,
    Map<String, dynamic>? snapshot,
    String? patientId,
    Map<String, dynamic>? patientProfile,
    List<Map<String, String>>? history,
    AuthService? auth,
  }) async {
    try {
      final body = <String, dynamic>{
        'specialty': specialty,
        'message': message,
        'snapshot': ?snapshot,
        'patient_id': ?patientId,
        'patient_profile': ?patientProfile,
        'history': ?history,
      };
      final response = await http.post(
        Uri.parse('$aiBaseUrl/api/agent/ask'),
        headers: _agentHeaders(auth),
        body: jsonEncode(body),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('agentAsk error: $e');
      return null;
    }
  }

  /// POST /api/agent/run-now — fan-out across all specialty experts.
  static Future<Map<String, dynamic>?> agentRunNow({
    Map<String, dynamic>? snapshot,
    String? patientId,
    Map<String, dynamic>? patientProfile,
    AuthService? auth,
  }) async {
    try {
      final body = <String, dynamic>{
        'snapshot': ?snapshot,
        'patient_id': ?patientId,
        'patient_profile': ?patientProfile,
      };
      final response = await http.post(
        Uri.parse('$aiBaseUrl/api/agent/run-now'),
        headers: _agentHeaders(auth),
        body: jsonEncode(body),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('agentRunNow error: $e');
      return null;
    }
  }

  /// POST /api/agent/complex-diagnosis — collaborative diagnosis graph.
  static Future<Map<String, dynamic>?> complexDiagnosis({
    String patientId = 'medverse-demo-patient',
    Map<String, dynamic>? snapshot,
    Map<String, dynamic>? patientProfile,
    AuthService? auth,
  }) async {
    try {
      final body = <String, dynamic>{
        'patient_id': patientId,
        'snapshot': ?snapshot,
        'patient_profile': ?patientProfile,
      };
      final response = await http.post(
        Uri.parse('$aiBaseUrl/api/agent/complex-diagnosis'),
        headers: _agentHeaders(auth),
        body: jsonEncode(body),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('complexDiagnosis error: $e');
      return null;
    }
  }

  /// POST /api/digital-twin/scenario — what-if forward simulation.
  static Future<Map<String, dynamic>?> digitalTwinScenario({
    required String twin,
    required Map<String, dynamic> inputs,
    int horizonMin = 30,
    String patientId = 'medverse-demo-patient',
    Map<String, dynamic>? snapshot,
    AuthService? auth,
  }) async {
    try {
      final body = <String, dynamic>{
        'patient_id': patientId,
        'twin': twin,
        'inputs': inputs,
        'horizon_min': horizonMin,
        'snapshot': ?snapshot,
      };
      final response = await http.post(
        Uri.parse('$baseUrl/api/digital-twin/scenario'),
        headers: _agentHeaders(auth),
        body: jsonEncode(body),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      debugPrint('digitalTwinScenario error: $e');
      return null;
    }
  }
}
