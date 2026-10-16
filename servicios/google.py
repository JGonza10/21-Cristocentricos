"""Credenciales de Google (una sola autorización para YouTube y Calendar).

Archivos en secretos/ (nunca en git):
  client_secret.json  -> se descarga de Google Cloud Console (OAuth, "App de escritorio")
  token_google.json   -> lo crea `flask --app app google-autorizar` la primera vez
"""
from pathlib import Path

from flask import current_app

ALCANCES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/calendar.events",
]


def _rutas() -> tuple[Path, Path]:
    d = Path(current_app.config["SECRETOS_DIR"])
    return d / "client_secret.json", d / "token_google.json"


def configurado() -> bool:
    return _rutas()[1].exists()


def credenciales():
    """Credenciales listas para usar, o None si todavía no se autoriza."""
    _, token = _rutas()
    if not token.exists():
        return None
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    cred = Credentials.from_authorized_user_file(str(token), ALCANCES)
    if not cred.valid and cred.expired and cred.refresh_token:
        cred.refresh(Request())
        token.write_text(cred.to_json(), encoding="utf-8")
    return cred if cred.valid else None


def autorizar() -> Path:
    """Abre el navegador para que Gonza dé permiso. Guarda el token en secretos/."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    secreto, token = _rutas()
    if not secreto.exists():
        raise FileNotFoundError(secreto)
    flujo = InstalledAppFlow.from_client_secrets_file(str(secreto), ALCANCES)
    cred = flujo.run_local_server(port=0, prompt="consent", access_type="offline")
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(cred.to_json(), encoding="utf-8")
    return token
