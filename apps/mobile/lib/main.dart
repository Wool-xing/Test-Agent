import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/chat_screen.dart';
import 'services/api_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    ChangeNotifierProvider(
      create: (_) => ApiService(),
      child: const TestAgentApp(),
    ),
  );
}

class TestAgentApp extends StatelessWidget {
  const TestAgentApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Test-Agent',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const ChatScreen(),
    );
  }
}
