from datetime import datetime, timedelta
from typing import Dict, Optional

import requests
from google.auth.transport.requests import Request
from google.oauth2 import id_token as google_id_token
from google.oauth2.credentials import Credentials
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AppUsuario, GoogleToken

TOKEN_URL = "https://oauth2.googleapis.com/token"


def exchange_code_for_tokens(code: str, redirect_uri: Optional[str] = None) -> Dict:
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri or settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    response = requests.post(TOKEN_URL, data=data, timeout=30)
    response.raise_for_status()
    return response.json()


def get_userinfo_from_id_token(id_token_str: str) -> Dict:
    request = Request()
    info = google_id_token.verify_oauth2_token(id_token_str, request, settings.google_client_id)
    return {
        "sub": info.get("sub"),
        "email": info.get("email"),
        "name": info.get("name"),
    }


def upsert_user_and_token(db: Session, userinfo: Dict, token_data: Dict, timezone: Optional[str] = None) -> AppUsuario:
    user = db.query(AppUsuario).filter(AppUsuario.google_sub == userinfo["sub"]).first()
    if not user:
        user = AppUsuario(
            google_sub=userinfo["sub"],
            email=userinfo.get("email", ""),
            nome=userinfo.get("name"),
            timezone=timezone or settings.default_timezone,
        )
        db.add(user)
        db.flush()
    else:
        if userinfo.get("email"):
            user.email = userinfo.get("email")
        if userinfo.get("name"):
            user.nome = userinfo.get("name")
        if timezone:
            user.timezone = timezone

    expiry = None
    if token_data.get("expires_in"):
        expiry = datetime.utcnow() + timedelta(seconds=int(token_data["expires_in"]))

    token = db.query(GoogleToken).filter(GoogleToken.usuario_id == user.id).first()
    if not token:
        if not token_data.get("refresh_token"):
            raise ValueError("refresh_token não retornado pelo Google (necessário para acesso offline)")
        token = GoogleToken(usuario_id=user.id)
        db.add(token)

    token.access_token = token_data.get("access_token", token.access_token)
    if token_data.get("refresh_token"):
        token.refresh_token = token_data["refresh_token"]
    token.expiry = expiry
    token.scope = token_data.get("scope")
    token.token_type = token_data.get("token_type")

    db.commit()
    db.refresh(user)
    return user


def build_credentials_from_token(token: GoogleToken) -> Credentials:
    creds = Credentials(
        token=token.access_token,
        refresh_token=token.refresh_token,
        token_uri=TOKEN_URL,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=settings.google_scopes_list,
    )
    if token.expiry:
        creds.expiry = token.expiry
    if not creds.valid:
        creds.refresh(Request())
    return creds
