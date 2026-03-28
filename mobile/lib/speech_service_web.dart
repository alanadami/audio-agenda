import 'dart:async';
import 'dart:convert';
import 'dart:html' as html;
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import 'app_config.dart';
import 'speech_service.dart';

class SpeechServiceImpl implements SpeechService {
  html.MediaRecorder? _recorder;
  html.MediaStream? _stream;
  final List<html.Blob> _chunks = [];
  String _mimeType = 'audio/webm';
  static const Duration _transcribeTimeout = Duration(seconds: 60);
  static const Duration _maxRecordDuration = Duration(seconds: 6);
  Timer? _autoStopTimer;

  @override
  Future<bool> initialize() async {
    final devices = html.window.navigator.mediaDevices;
    if (devices == null) {
      return false;
    }
    if (html.MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
      _mimeType = 'audio/webm;codecs=opus';
    } else if (html.MediaRecorder.isTypeSupported('audio/webm')) {
      _mimeType = 'audio/webm';
    } else if (html.MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
      _mimeType = 'audio/ogg;codecs=opus';
    }
    return true;
  }

  @override
  Future<void> listen({
    required void Function(String text) onResult,
    void Function(String message)? onError,
  }) async {
    final devices = html.window.navigator.mediaDevices;
    if (devices == null) {
      return;
    }
    _stream = await devices.getUserMedia({'audio': true});

    final options = <String, dynamic>{'mimeType': _mimeType};
    _recorder = html.MediaRecorder(_stream!, options);
    _chunks.clear();

    _recorder!.addEventListener('dataavailable', (event) {
      final e = event as html.BlobEvent;
      if (e.data != null) {
        _chunks.add(e.data!);
      }
    });

    _recorder!.addEventListener('stop', (event) async {
      _autoStopTimer?.cancel();
      final blob = html.Blob(_chunks, _mimeType);
      if (blob.size == 0) {
        onError?.call('Áudio vazio.');
        _cleanup();
        return;
      }
      final bytes = await _blobToBytes(blob);
      final result = await _sendForTranscription(bytes);
      if (result.text.isNotEmpty) {
        onResult(result.text);
      } else {
        onError?.call(result.error ?? 'Não foi possível transcrever o áudio.');
      }
      _cleanup();
    });

    _recorder!.start();
    _autoStopTimer?.cancel();
    _autoStopTimer = Timer(_maxRecordDuration, () {
      if (_recorder != null && _recorder!.state != 'inactive') {
        _recorder!.stop();
      }
    });
  }

  @override
  Future<void> stop() async {
    if (_recorder != null && _recorder!.state != 'inactive') {
      _recorder!.stop();
    }
    _autoStopTimer?.cancel();
  }

  Future<Uint8List> _blobToBytes(html.Blob blob) async {
    final reader = html.FileReader();
    final completer = Completer<Uint8List>();
    reader.onLoadEnd.listen((_) {
      final result = reader.result as ByteBuffer;
      completer.complete(Uint8List.view(result));
    });
    reader.readAsArrayBuffer(blob);
    return completer.future;
  }

  Future<_TranscribeResult> _sendForTranscription(Uint8List bytes) async {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}/upload-audio');
    final request = http.MultipartRequest('POST', uri);
    request.files.add(
      http.MultipartFile.fromBytes(
        'audio',
        bytes,
        filename: 'audio.webm',
      ),
    );
    try {
      final response = await request.send().timeout(_transcribeTimeout);
      final body = await response.stream.bytesToString();
      if (response.statusCode != 200) {
        String? detail;
        try {
          final data = jsonDecode(body) as Map<String, dynamic>;
          detail = data['detail']?.toString();
        } catch (_) {}
        return _TranscribeResult(
          '',
          detail ?? 'Falha ao transcrever áudio (HTTP ${response.statusCode}).',
        );
      }
      final data = jsonDecode(body) as Map<String, dynamic>;
      final text = (data['text'] as String?)?.trim() ?? '';
      return _TranscribeResult(text, text.isEmpty ? 'Transcrição vazia.' : null);
    } on TimeoutException {
      return _TranscribeResult('', 'Tempo limite na transcrição.');
    } catch (_) {
      return _TranscribeResult('', 'Falha ao enviar áudio para transcrição.');
    }
  }

  void _cleanup() {
    _autoStopTimer?.cancel();
    for (final track in _stream?.getTracks() ?? []) {
      track.stop();
    }
    _stream = null;
    _recorder = null;
  }
}

class _TranscribeResult {
  final String text;
  final String? error;

  _TranscribeResult(this.text, this.error);
}
