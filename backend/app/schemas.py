from datetime import date, time
from typing import Optional
from pydantic import BaseModel, EmailStr


class AuthCodeIn(BaseModel):
    code: Optional[str] = None
    id_token: Optional[str] = None
    access_token: Optional[str] = None
    redirect_uri: Optional[str] = None
    timezone: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    nome: Optional[str] = None
    timezone: str
    resumo_diario_ativo: bool
    resumo_diario_hora: time

    class Config:
        orm_mode = True


class AuthResponse(BaseModel):
    token: str
    user: UserOut


class CommitmentCreate(BaseModel):
    texto: str
    timezone: Optional[str] = None
    access_token: Optional[str] = None


class CommitmentOut(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    data: date
    hora: time
    local: Optional[str] = None
    google_event_id: Optional[str] = None
    google_event_link: Optional[str] = None

    class Config:
        orm_mode = True
