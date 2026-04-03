import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart';
import 'dart:io' show Platform;

class ApiService {
  static String get baseUrl {
    if (kIsWeb) return 'http://localhost:8000';
    try {
      if (Platform.isAndroid) return 'http://10.0.2.2:8000';
    } catch (_) {}
    return 'http://localhost:8000';
  }

  static Future<bool> setSimulationMode(String mode) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/simulation/mode'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'mode': mode}),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error setting simulation mode: $e');
      return false;
    }
  }

  static Future<bool> injectMedication(String medicationName, double dose) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/simulation/medicate'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'medication': medicationName, 'dose': dose}),
      );
      return response.statusCode == 200;
    } catch (e) {
      debugPrint('Error injecting medication: $e');
      return false;
    }
  }

  static Future<Map<String, dynamic>?> uploadLabResults(String filePath) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/upload-lab-results'));
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
}
