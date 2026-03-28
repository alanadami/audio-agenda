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
      final blob = html.Blob(_chunks, _mimeType);
      final bytes = await _blobToBytes(blob);
      final text = await _sendForTranscription(bytes);
      if (text.isNotEmpty) {
        onResult(text);
      } else {
        onError?.call('Não foi possível transcrever o áudio.');
      }
      _cleanup();
    });

    _recorder!.start();
  }

  @override
  Future<void> stop() async {
    if (_recorder != null && _recorder!.state != 'inactive') {
      _recorder!.stop();
    }
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

  Future<String> _sendForTranscription(Uint8List bytes) async {
    final uri = Uri.parse('${AppConfig.apiBaseUrl}/transcribe');
    final request = http.MultipartRequest('POST', uri);
    request.files.add(
      http.MultipartFile.fromBytes(
        'file',
        bytes,
        filename: 'audio.webm',
      ),
    );
    final response = await request.send();
    final body = await response.stream.bytesToString();
    if (response.statusCode != 200) {
      return '';
    }
    final data = jsonDecode(body) as Map<String, dynamic>;
    return (data['text'] as String?)?.trim() ?? '';
  }

  void _cleanup() {
    for (final track in _stream?.getTracks() ?? []) {
      track.stop();
    }
    _stream = null;
    _recorder = null;
  }
}
