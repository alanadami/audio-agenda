from datetime import datetime
import io
import logging
import os
import subprocess
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from openai import OpenAI
from imageio_ffmpeg import get_ffmpeg_exe
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from app.auth import create_access_token, get_current_user
from app.calendar_service import create_calendar_event
from app.config import settings
from app.db import get_db
from requests import RequestException

from app.google_oauth import (
    exchange_code_for_tokens,
    get_userinfo_from_id_token,
    get_userinfo_from_access_token,
    upsert_user_and_token,
    upsert_user,
    build_credentials_from_token,
    build_credentials_from_access_token,
)
from app.jobs import start_scheduler
from app.models import AppCompromisso, AppUsuario
from app.parser import parse_message
from app.schemas import AuthCodeIn, AuthResponse, CommitmentCreate, CommitmentOut

app = FastAPI(title="Agenda App API")
logger = logging.getLogger("uvicorn.error")
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def _is_audio_upload(upload: UploadFile) -> bool:
    if upload.content_type and upload.content_type.startswith("audio/"):
        return True
    # Alguns browsers enviam como application/octet-stream
    if upload.content_type in (None, "", "application/octet-stream"):
        suffix = Path(upload.filename or "").suffix.lower()
        return suffix in {".webm", ".ogg", ".wav", ".mp3", ".m4a"}
    return False


def _convert_to_mp3(src: Path, dst: Path) -> None:
    ffmpeg = get_ffmpeg_exe()
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[:500]}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://alanadami.github.io",
    ],
    allow_origin_regex=r"https?://localhost(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    if settings.enable_scheduler:
        start_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/auth/google", response_model=AuthResponse)
def auth_google(payload: AuthCodeIn, db: Session = Depends(get_db)):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=500, detail="Google OAuth não configurado")

    try:
        if payload.code:
            try:
                token_data = exchange_code_for_tokens(payload.code, payload.redirect_uri)
            except RequestException:
                raise HTTPException(status_code=400, detail="Falha ao trocar code por tokens")

            if "id_token" not in token_data:
                raise HTTPException(status_code=400, detail="id_token não retornado pelo Google")

            try:
                userinfo = get_userinfo_from_id_token(token_data["id_token"])
            except Exception:
                raise HTTPException(status_code=400, detail="Falha ao validar id_token")
            if not userinfo.get("sub"):
                raise HTTPException(status_code=400, detail="Não foi possível identificar o usuário")

            try:
                user = upsert_user_and_token(db, userinfo, token_data, payload.timezone)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        elif payload.id_token:
            try:
                userinfo = get_userinfo_from_id_token(payload.id_token)
            except Exception:
                raise HTTPException(status_code=400, detail="Falha ao validar id_token")
            if not userinfo.get("sub"):
                raise HTTPException(status_code=400, detail="Não foi possível identificar o usuário")
            user = upsert_user(db, userinfo, payload.timezone)
        elif payload.access_token:
            try:
                userinfo = get_userinfo_from_access_token(payload.access_token)
            except RequestException:
                raise HTTPException(status_code=400, detail="Falha ao validar access_token")
            if not userinfo.get("sub"):
                raise HTTPException(status_code=400, detail="Não foi possível identificar o usuário")
            user = upsert_user(db, userinfo, payload.timezone)
        else:
            raise HTTPException(status_code=400, detail="Informe code ou id_token")
        token = create_access_token(user.id)

        return {"token": token, "user": user}
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro ao acessar o banco")
    except Exception:
        raise HTTPException(status_code=400, detail="Erro inesperado no login")


@app.post("/transcribe")
def transcribe_audio(file: UploadFile = File(...)):
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI não configurada")

    if not _is_audio_upload(file):
        raise HTTPException(status_code=400, detail="Arquivo de áudio inválido")

    data = file.file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    audio = io.BytesIO(data)
    audio.name = file.filename or "audio.webm"

    client = OpenAI(api_key=settings.openai_api_key)
    try:
        result = client.audio.transcriptions.create(
            model=settings.openai_transcribe_model,
            file=audio,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Falha ao transcrever áudio")

    text = getattr(result, "text", None)
    if text is None:
        try:
            text = result.get("text")
        except Exception:
            text = ""

    return {"text": text or ""}


@app.post("/upload-audio")
def upload_audio(audio: UploadFile = File(...)):
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="OpenAI não configurada")

    if not _is_audio_upload(audio):
        raise HTTPException(status_code=400, detail="Arquivo de áudio inválido")

    suffix = Path(audio.filename or "").suffix or ".webm"
    filename = f"{uuid.uuid4().hex}{suffix}"
    filepath = UPLOAD_DIR / filename
    mp3_path = filepath.with_suffix(".mp3")

    try:
        with filepath.open("wb") as out:
            out.write(audio.file.read())

        _convert_to_mp3(filepath, mp3_path)

        client = OpenAI(api_key=settings.openai_api_key)
        with mp3_path.open("rb") as f:
            result = client.audio.transcriptions.create(
                model=settings.openai_transcribe_model,
                file=f,
            )
        text = getattr(result, "text", None)
        if text is None:
            try:
                text = result.get("text")
            except Exception:
                text = ""
        return {"text": text or ""}
    except Exception:
        raise HTTPException(status_code=400, detail="Falha ao transcrever áudio")
    finally:
        try:
            if filepath.exists():
                os.remove(filepath)
            if mp3_path.exists():
                os.remove(mp3_path)
        except Exception:
            pass


@app.post("/compromissos", response_model=CommitmentOut)
def criar_compromisso(
    payload: CommitmentCreate,
    usuario: AppUsuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        agora = datetime.now(ZoneInfo(usuario.timezone or settings.default_timezone))
        analise = parse_message(payload.texto, agora)

        if analise.get("erro"):
            raise HTTPException(status_code=400, detail=analise["erro"])

        try:
            data_evento = datetime.strptime(analise["data"], "%Y-%m-%d").date()
            hora_evento = datetime.strptime(analise["hora"], "%H:%M:%S").time()
        except Exception:
            raise HTTPException(status_code=400, detail="Data ou hora inválida retornada pela IA")

        compromisso = AppCompromisso(
            usuario_id=usuario.id,
            titulo=analise["titulo"],
            descricao=analise.get("descricao"),
            data=data_evento,
            hora=hora_evento,
            local=analise.get("local"),
            texto_original=payload.texto,
        )

        db.add(compromisso)
        db.flush()

        if usuario.token:
            creds = build_credentials_from_token(usuario.token)
        elif payload.access_token:
            creds = build_credentials_from_access_token(payload.access_token)
        else:
            raise HTTPException(status_code=400, detail="Usuário sem token do Google")

        evento = create_calendar_event(creds, analise, usuario.timezone or settings.default_timezone)

        compromisso.google_event_id = evento.get("id")
        db.commit()
        db.refresh(compromisso)
    except (HttpError, RefreshError):
        raise HTTPException(status_code=400, detail="Falha ao criar evento no Google Calendar")
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erro ao salvar compromisso no banco")
    except HTTPException:
        raise
    except Exception:
        logger.exception(
            "Erro inesperado ao criar compromisso. has_token=%s has_access_token=%s",
            bool(usuario.token),
            bool(payload.access_token),
        )
        raise HTTPException(status_code=400, detail="Erro inesperado ao criar compromisso")

    return {
        "id": compromisso.id,
        "titulo": compromisso.titulo,
        "descricao": compromisso.descricao,
        "data": compromisso.data,
        "hora": compromisso.hora,
        "local": compromisso.local,
        "google_event_id": compromisso.google_event_id,
        "google_event_link": evento.get("htmlLink"),
    }
