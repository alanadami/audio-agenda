import 'speech_service.dart';

class SpeechServiceImpl implements SpeechService {
  @override
  Future<bool> initialize() async {
    return false;
  }

  @override
  Future<void> listen({required void Function(String text) onResult}) async {}

  @override
  Future<void> stop() async {}
}
