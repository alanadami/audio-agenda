from datetime import datetime, timedelta
from typing import Dict, List

from googleapiclient.discovery import build


def create_calendar_event(creds, dados: Dict, timezone: str) -> Dict:
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    data_hora_str = f"{dados['data']}T{dados['hora']}"
    inicio = datetime.fromisoformat(data_hora_str)
    fim = inicio + timedelta(hours=1)

    evento = {
        "summary": dados["titulo"],
        "description": dados.get("descricao"),
        "location": dados.get("local"),
        "start": {"dateTime": inicio.isoformat(), "timeZone": timezone},
        "end": {"dateTime": fim.isoformat(), "timeZone": timezone},
    }

    response = service.events().insert(calendarId="primary", body=evento).execute()
    return response


def list_events_for_date(creds, date_start: datetime, date_end: datetime) -> List[Dict]:
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    response = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=date_start.isoformat(),
            timeMax=date_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return response.get("items", [])
