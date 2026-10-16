"""Invitaciones de Google Calendar para cada evento."""
from datetime import date

from agentes import fechas

from . import google


def sincronizar(fecha: date, calendario_id: str, titulo: str, descripcion: str,
                correos: list[str], google_id: str | None) -> str:
    """Crea o actualiza el evento del evento con los invitados. Devuelve el id del evento.

    Google manda el correo de invitación (o de cambio) a cada invitado: sendUpdates="all".
    """
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    cred = google.credenciales()
    if cred is None:
        raise RuntimeError("Google Calendar no está autorizado")
    cal = build("calendar", "v3", credentials=cred, cache_discovery=False)
    cuerpo = {
        "summary": titulo,
        "description": descripcion,
        "start": {"dateTime": fechas.inicio(fecha).isoformat(), "timeZone": "America/Mexico_City"},
        "end": {"dateTime": fechas.fin(fecha).isoformat(), "timeZone": "America/Mexico_City"},
        "attendees": [{"email": c} for c in correos],
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}]},
    }
    if google_id:
        try:
            return cal.events().patch(calendarId=calendario_id, eventId=google_id, body=cuerpo,
                                      sendUpdates="all").execute()["id"]
        except HttpError as e:
            if getattr(e, "status_code", None) not in (404, 410):   # si lo borraron, se crea otro
                raise
    return cal.events().insert(calendarId=calendario_id, body=cuerpo, sendUpdates="all").execute()["id"]
