import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:test_agent_mobile/services/api_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // FlutterSecureStorage uses a platform channel — mock it (returns no key).
  const storageChannel = MethodChannel('plugins.it_nomads.com/flutter_secure_storage');
  setUp(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(storageChannel, (call) async => null);
  });
  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(storageChannel, null);
  });

  group('ApiService', () {
    test('initial state is not configured', () {
      final api = ApiService();
      expect(api.isConfigured, false);
    });

    test('baseUrl has default', () {
      final api = ApiService();
      expect(api.baseUrl, isNotEmpty);
    });

    test('runTest without API key returns error', () async {
      final api = ApiService();
      final result = await api.runTest('check www.example.com');
      expect(result['status'], 'error');
      expect(result['summary'], contains('not configured'));
    });

    test('getStatus without API key returns error', () async {
      final api = ApiService();
      final result = await api.getStatus();
      expect(result['status'], 'error');
    });
  });
}
