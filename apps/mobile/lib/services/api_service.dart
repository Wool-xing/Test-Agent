import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

/// API service for communicating with Test-Agent backend.
/// Stores API keys securely using FlutterSecureStorage.
class ApiService extends ChangeNotifier {
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  String _baseUrl = 'https://api.test-agent.dev';
  bool _isConfigured = false;

  String get baseUrl => _baseUrl;
  bool get isConfigured => _isConfigured;

  Future<void> setApiKey(String key) async {
    await _storage.write(key: 'api_key', value: key);
    _isConfigured = true;
    notifyListeners();
  }

  Future<String?> getApiKey() async {
    return await _storage.read(key: 'api_key');
  }

  /// Send a natural language test request and get results.
  Future<Map<String, dynamic>> runTest(String prompt) async {
    final apiKey = await getApiKey();
    if (apiKey == null) {
      return {'status': 'error', 'summary': 'API key not configured'};
    }

    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/v1/run'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $apiKey',
        },
        body: jsonEncode({'prompt': prompt}),
      ).timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
      return {'status': 'error', 'summary': 'Server error: ${response.statusCode}'};
    } catch (e) {
      return {'status': 'error', 'summary': 'Connection failed: $e'};
    }
  }

  /// Get current Test-Agent status.
  Future<Map<String, dynamic>> getStatus() async {
    final apiKey = await getApiKey();
    if (apiKey == null) return {'status': 'error'};

    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/v1/status'),
        headers: {'Authorization': 'Bearer $apiKey'},
      ).timeout(const Duration(seconds: 10));

      return jsonDecode(response.body);
    } catch (e) {
      return {'status': 'error', 'summary': '$e'};
    }
  }
}
