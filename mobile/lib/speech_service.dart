import 'speech_service_stub.dart'
    if (dart.library.html) 'speech_service_web.dart'
    if (dart.library.io) 'speech_service_mobile.dart';

abstract class SpeechService {
  Future<bool> initialize();
  Future<void> listen({required void Function(String text) onResult});
  Future<void> stop();
}

SpeechService createSpeechService() => SpeechServiceImpl();
