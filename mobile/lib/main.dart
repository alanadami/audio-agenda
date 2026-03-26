import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'package:speech_to_text/speech_to_text.dart' as stt;

import 'app_config.dart';

void main() {
  runApp(const AgendaApp());
}

class AgendaApp extends StatelessWidget {
  const AgendaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Agenda App',
      theme: ThemeData(colorSchemeSeed: const Color(0xFF2B5B4D)),
      home: const HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  static const List<String> _scopes = [
    'email',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send',
  ];

  final TextEditingController _textoController = TextEditingController();
  final stt.SpeechToText _speech = stt.SpeechToText();

  String? _jwt;
  String _status = 'Desconectado';
  bool _loading = false;
  bool _listening = false;

  late final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: _scopes,
    serverClientId: AppConfig.googleWebClientId,
    forceCodeForRefreshToken: true,
  );

  Future<void> _login() async {
    setState(() {
      _loading = true;
      _status = 'Abrindo login Google...';
    });

    try {
      final account = await _googleSignIn.signIn();
      if (account == null) {
        setState(() => _status = 'Login cancelado.');
        return;
      }

      if (kIsWeb) {
        final granted = await _googleSignIn.requestScopes(_scopes);
        if (!granted) {
          setState(() => _status = 'Permissões negadas para calendário e e-mail.');
          return;
        }
      }

      final serverAuthCode = account.serverAuthCode;
      if (serverAuthCode == null || serverAuthCode.isEmpty) {
        setState(() => _status = 'serverAuthCode não retornado.');
        return;
      }

      final response = await http.post(
        Uri.parse('${AppConfig.apiBaseUrl}/auth/google'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'code': serverAuthCode,
          'redirect_uri': 'postmessage',
          'timezone': 'America/Sao_Paulo',
        }),
      );

      if (response.statusCode != 200) {
        setState(() => _status = 'Erro no backend: ${response.body}');
        return;
      }

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      setState(() {
        _jwt = data['token'] as String?;
        _status = 'Conectado: ${data['user']['email']}';
      });
    } catch (e) {
      setState(() => _status = 'Erro no login: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _criarCompromisso() async {
    final texto = _textoController.text.trim();
    if (texto.isEmpty) {
      setState(() => _status = 'Digite ou grave uma mensagem.');
      return;
    }
    if (_jwt == null) {
      setState(() => _status = 'Faça login primeiro.');
      return;
    }

    setState(() {
      _loading = true;
      _status = 'Enviando compromisso...';
    });

    try {
      final response = await http.post(
        Uri.parse('${AppConfig.apiBaseUrl}/compromissos'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $_jwt',
        },
        body: jsonEncode({'texto': texto}),
      );

      if (response.statusCode != 200) {
        setState(() => _status = 'Erro: ${response.body}');
        return;
      }

      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final link = data['google_event_link'] ?? '';
      setState(() => _status = 'Compromisso criado. $link');
    } catch (e) {
      setState(() => _status = 'Erro: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  Future<void> _toggleListening() async {
    if (!_listening) {
      final available = await _speech.initialize();
      if (!available) {
        setState(() => _status = 'Speech-to-text indisponível.');
        return;
      }

      setState(() {
        _listening = true;
        _status = 'Ouvindo...';
      });

      await _speech.listen(
        localeId: 'pt_BR',
        onResult: (result) {
          setState(() {
            _textoController.text = result.recognizedWords;
          });
        },
      );
    } else {
      await _speech.stop();
      setState(() {
        _listening = false;
        _status = 'Gravação finalizada.';
      });
    }
  }

  @override
  void dispose() {
    _textoController.dispose();
    _speech.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Agenda App')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ElevatedButton(
              onPressed: _loading ? null : _login,
              child: const Text('Login com Google'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _textoController,
              maxLines: 4,
              decoration: const InputDecoration(
                labelText: 'Mensagem do compromisso',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: _loading ? null : _criarCompromisso,
                    child: const Text('Salvar compromisso'),
                  ),
                ),
                const SizedBox(width: 12),
                IconButton(
                  onPressed: _loading ? null : _toggleListening,
                  icon: Icon(_listening ? Icons.stop : Icons.mic),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              _status,
              style: const TextStyle(fontSize: 14),
            ),
          ],
        ),
      ),
    );
  }
}
