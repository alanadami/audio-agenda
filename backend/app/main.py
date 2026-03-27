from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from app.auth import create_access_token, get_current_user
from app.calendar_service import create_calendar_event
from app.config import settings
from app.db import get_db
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://alanadami.github.io",
    ],
    allow_origin_regex=r"https?://localhost(:\d+)?",
    allow_credentials=False,
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

    if payload.code:
        token_data = exchange_code_for_tokens(payload.code, payload.redirect_uri)

        if "id_token" not in token_data:
            raise HTTPException(status_code=400, detail="id_token não retornado pelo Google")

        userinfo = get_userinfo_from_id_token(token_data["id_token"])
        if not userinfo.get("sub"):
            raise HTTPException(status_code=400, detail="Não foi possível identificar o usuário")

        try:
            user = upsert_user_and_token(db, userinfo, token_data, payload.timezone)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
    elif payload.id_token:
        userinfo = get_userinfo_from_id_token(payload.id_token)
        if not userinfo.get("sub"):
            raise HTTPException(status_code=400, detail="Não foi possível identificar o usuário")
        user = upsert_user(db, userinfo, payload.timezone)
    elif payload.access_token:
        userinfo = get_userinfo_from_access_token(payload.access_token)
        if not userinfo.get("sub"):
            raise HTTPException(status_code=400, detail="Não foi possível identificar o usuário")
        user = upsert_user(db, userinfo, payload.timezone)
    else:
        raise HTTPException(status_code=400, detail="Informe code ou id_token")
    token = create_access_token(user.id)

    return {"token": token, "user": user}


@app.post("/compromissos", response_model=CommitmentOut)
def criar_compromisso(
    payload: CommitmentCreate,
    usuario: AppUsuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
