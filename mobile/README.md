# Flutter App (Template)

Este diretório contém **somente** o código-base do Flutter (para copiar e usar em um projeto Flutter real).

## 1) Crie o projeto Flutter
```powershell
flutter create agenda_app
```

## 2) Copie os arquivos deste template
- Substitua `agenda_app/lib/main.dart` por `mobile/lib/main.dart`
- Mescle as dependências do `mobile/pubspec.yaml` no `agenda_app/pubspec.yaml`

## 3) Configure o Google Sign-In (Android)
- No Google Cloud Console, crie um OAuth Client **Android** e baixe o `google-services.json`.
- Coloque `google-services.json` em `agenda_app/android/app/`.

## 4) Permissões Android
Em `agenda_app/android/app/src/main/AndroidManifest.xml`:
```
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```

## 5) Preencha as constantes no main.dart
Em `mobile/lib/main.dart`, troque:
- `apiBaseUrl` para a URL do Railway
- `googleWebClientId` para o Client ID **Web**

## 6) Rode
```powershell
cd agenda_app
flutter pub get
flutter run
```

Se você quiser, posso também gerar o projeto completo já no repo (com android/ e todos os arquivos). Para isso eu preciso confirmar que o Flutter está instalado aqui.
