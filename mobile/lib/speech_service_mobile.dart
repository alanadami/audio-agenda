import 'package:speech_to_text/speech_to_text.dart' as stt;

import 'speech_service.dart';

class SpeechServiceImpl implements SpeechService {
  final stt.SpeechToText _speech = stt.SpeechToText();

  @override
  Future<bool> initialize() {
    return _speech.initialize();
  }

  @override
  Future<void> listen({
    required void Function(String text) onResult,
    void Function(String message)? onError,
  }) async {
    await _speech.listen(
      localeId: 'pt_BR',
      onResult: (result) => onResult(result.recognizedWords),
    );
  }

  @override
  Future<void> stop() async {
    await _speech.stop();
  }
}
