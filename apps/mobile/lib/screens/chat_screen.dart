import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';

/// Chat-like interface for natural language test input (中英双语).
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final TextEditingController _controller = TextEditingController();
  final List<ChatMessage> _messages = [];
  bool _isLoading = false;

  Future<void> _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    setState(() {
      _messages.add(ChatMessage(text: text, isUser: true));
      _isLoading = true;
    });
    _controller.clear();

    final api = context.read<ApiService>();
    final result = await api.runTest(text);

    setState(() {
      _isLoading = false;
      _messages.add(ChatMessage(
        text: result['summary'] ?? result['status'] ?? 'Unknown',
        isUser: false,
        details: result['details']?.toString(),
      ));
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Test-Agent'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => _showApiKeyDialog(context),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              itemCount: _messages.length,
              itemBuilder: (ctx, i) => _messages[i].buildWidget(),
            ),
          ),
          if (_isLoading) const LinearProgressIndicator(),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8.0),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: const InputDecoration(
                        hintText: '输入测试指令... / Enter test command...',
                        border: OutlineInputBorder(),
                      ),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send),
                    onPressed: _sendMessage,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  void _showApiKeyDialog(BuildContext context) {
    final keyCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('API Key'),
        content: TextField(
          controller: keyCtrl,
          obscureText: true,
          decoration: const InputDecoration(hintText: 'Enter your API key'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          TextButton(
            onPressed: () {
              context.read<ApiService>().setApiKey(keyCtrl.text);
              Navigator.pop(ctx);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }
}

class ChatMessage {
  final String text;
  final bool isUser;
  final String? details;

  ChatMessage({required this.text, required this.isUser, this.details});

  Widget buildWidget() {
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.all(8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isUser ? Colors.blue[100] : Colors.grey[200],
          borderRadius: BorderRadius.circular(12),
        ),
        constraints: const BoxConstraints(maxWidth: 300),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(text, style: const TextStyle(fontSize: 16)),
            if (details != null) Text(details!, style: const TextStyle(fontSize: 12, color: Colors.grey)),
          ],
        ),
      ),
    );
  }
}
