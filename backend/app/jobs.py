from datetime import datetime, time as dtime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.calendar_service import list_events_for_date
from app.config import settings
from app.db import SessionLocal
from app.emailer import send_gmail_message
from app.google_oauth import build_credentials_from_token
from app.models import AppUsuario


scheduler = BackgroundScheduler(timezone="UTC")


def _should_send(user: AppUsuario, now_utc: datetime) -> bool:
    if not user.resumo_diario_ativo:
        return False

    tz = ZoneInfo(user.timezone or settings.default_timezone)
    now_local = now_utc.astimezone(tz)

    target_time = user.resumo_diario_hora or dtime(settings.summary_hour, settings.summary_minute)
    target = now_local.replace(
        hour=target_time.hour,
        minute=target_time.minute,
        second=0,
        microsecond=0,
    )

    if now_local < target:
        return False

    if user.ultimo_resumo_enviado_em:
        last_sent = user.ultimo_resumo_enviado_em
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=ZoneInfo("UTC"))
        last_local = last_sent.astimezone(tz)
        if last_local.date() == now_local.date():
            return False

    return True


def _build_summary_text(eventos):
    if not eventos:
        return "Nenhum compromisso encontrado para amanhã."

    linhas = ["Seus compromissos para amanhã:\n"]
    for evento in eventos:
        start = evento.get("start", {})
        inicio = start.get("dateTime") or start.get("date") or "(sem horário)"
        titulo = evento.get("summary", "(sem título)")
        linhas.append(f"- {inicio} | {titulo}")

    return "\n".join(linhas)


def enviar_resumos():
    db: Session = SessionLocal()
    try:
        now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
        usuarios = db.query(AppUsuario).all()

        for user in usuarios:
            if not _should_send(user, now_utc):
                continue

            if not user.token:
                continue

            creds = build_credentials_from_token(user.token)
            tz = ZoneInfo(user.timezone or settings.default_timezone)
            now_local = now_utc.astimezone(tz)

            amanha = now_local.date() + timedelta(days=1)
            inicio = datetime.combine(amanha, dtime(0, 0, 0), tzinfo=tz)
            fim = datetime.combine(amanha, dtime(23, 59, 59), tzinfo=tz)

            eventos = list_events_for_date(creds, inicio, fim)
            texto = _build_summary_text(eventos)

            assunto = f"Resumo diário - {amanha.strftime('%d/%m/%Y')}"
            send_gmail_message(creds, user.email, assunto, texto, user.email)

            user.ultimo_resumo_enviado_em = now_utc
            db.add(user)

        db.commit()
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(enviar_resumos, "interval", minutes=10, id="resumo_diario")
    scheduler.start()
