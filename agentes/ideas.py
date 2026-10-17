"""Agente de ideas: pasa a texto (con Whisper, en esta PC) las ideas grabadas por audio."""
from pathlib import Path

from flask import current_app

from app.extensiones import db
from app.modelos import Idea
from servicios import whisper


def tarea() -> int:
    """Transcribe las ideas de audio pendientes. Devuelve cuántas quedaron listas."""
    listas = 0
    for i in Idea.query.filter_by(estado="transcribiendo").order_by(Idea.id).limit(5).all():
        ruta = Path(current_app.config["IDEAS_DIR"]) / (i.audio or "")
        try:
            segmentos = whisper.transcribir(str(ruta), current_app.config["WHISPER_MODELO"])
            texto = " ".join(s[2] for s in segmentos).strip()
            i.texto, i.estado = (texto, "lista") if texto else ("", "error")
            listas += bool(texto)
        except Exception:  # noqa: BLE001
            current_app.logger.exception("No se pudo transcribir la idea %s", i.id)
            db.session.rollback()
            i = db.session.get(Idea, i.id)
            i.estado = "error"
        db.session.commit()
    return listas
