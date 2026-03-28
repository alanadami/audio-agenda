import 'dart:html' as html;
import 'dart:js_util' as js_util;

import 'package:js/js.dart';

import 'speech_service.dart';

class SpeechServiceImpl implements SpeechService {
  dynamic _recognition;

  bool _ensureRecognition() {
    final dynamic speechRecognition = js_util.getProperty(html.window, 'SpeechRecognition') ??
        js_util.getProperty(html.window, 'webkitSpeechRecognition');
    if (speechRecognition == null) {
      return false;
    }
    _recognition = js_util.callConstructor(speechRecognition, []);
    js_util.setProperty(_recognition, 'lang', 'pt-BR');
    js_util.setProperty(_recognition, 'continuous', false);
    js_util.setProperty(_recognition, 'interimResults', true);
    return true;
  }

  @override
  Future<bool> initialize() async {
    if (_recognition != null) {
      return true;
    }
    return _ensureRecognition();
  }

  @override
  Future<void> listen({required void Function(String text) onResult}) async {
    if (_recognition == null) {
      final ok = _ensureRecognition();
      if (!ok) {
        return;
      }
    }

    js_util.setProperty(
      _recognition,
      'onresult',
      allowInterop((event) {
        final results = js_util.getProperty(event, 'results');
        final length = js_util.getProperty(results, 'length') as int;
        if (length == 0) {
          return;
        }
        final last = js_util.getProperty(results, length - 1);
        final firstAlt = js_util.getProperty(last, 0);
        final transcript = js_util.getProperty(firstAlt, 'transcript') as String;
        onResult(transcript);
      }),
    );

    js_util.setProperty(
      _recognition,
      'onerror',
      allowInterop((event) {
        // noop: falhas são tratadas no app via initialize()
      }),
    );

    js_util.callMethod(_recognition, 'start', []);
  }

  @override
  Future<void> stop() async {
    if (_recognition != null) {
      js_util.callMethod(_recognition, 'stop', []);
    }
  }
}
