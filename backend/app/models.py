from datetime import time as dtime
from sqlalchemy import Column, Integer, String, Boolean, Date, Time, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class AppUsuario(Base):
    __tablename__ = "app_usuarios"

    id = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=False)
    nome = Column(String(255))
    timezone = Column(String(64), default="America/Sao_Paulo")
    resumo_diario_ativo = Column(Boolean, default=True)
    resumo_diario_hora = Column(Time, default=dtime(18, 0))
    ultimo_resumo_enviado_em = Column(DateTime, nullable=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    token = relationship("GoogleToken", back_populates="usuario", uselist=False, cascade="all, delete-orphan")
    compromissos = relationship("AppCompromisso", back_populates="usuario", cascade="all, delete-orphan")


class GoogleToken(Base):
    __tablename__ = "app_tokens_google"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("app_usuarios.id"), nullable=False, unique=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    expiry = Column(DateTime, nullable=True)
    scope = Column(Text, nullable=True)
    token_type = Column(String(20), nullable=True)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    usuario = relationship("AppUsuario", back_populates="token")


class AppCompromisso(Base):
    __tablename__ = "app_compromissos"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("app_usuarios.id"), nullable=False)
    titulo = Column(String(200), nullable=False)
    descricao = Column(String(1000))
    data = Column(Date, nullable=False)
    hora = Column(Time, nullable=False)
    local = Column(String(255))
    google_event_id = Column(String(200))
    texto_original = Column(Text)
    criado_em = Column(DateTime, server_default=func.now())
    atualizado_em = Column(DateTime, server_default=func.now(), onupdate=func.now())

    usuario = relationship("AppUsuario", back_populates="compromissos")
