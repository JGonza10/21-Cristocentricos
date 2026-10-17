"""Correos del sistema por Gmail, con la misma autorización de Google (alcance gmail.send)."""
import base64
from email.message import EmailMessage

from . import google


def enviar(para: list[str], asunto: str, texto: str) -> None:
    """Manda un correo desde la cuenta de Google autorizada. Los destinatarios van en copia oculta."""
    from googleapiclient.discovery import build

    cred = google.credenciales()
    if cred is None or not cred.has_scopes(["https://www.googleapis.com/auth/gmail.send"]):
        raise RuntimeError("Gmail no está autorizado: corre «flask --app app google-autorizar».")
    msg = EmailMessage()
    msg["To"] = "undisclosed-recipients:;"
    msg["Bcc"] = ", ".join(para)
    msg["Subject"] = asunto
    msg.set_content(texto)
    crudo = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    build("gmail", "v1", credentials=cred, cache_discovery=False).users().messages().send(
        userId="me", body={"raw": crudo}).execute()
