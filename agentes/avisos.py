"""Agente de avisos: cuando se guarda o cambia el tema de un evento, avisa al equipo por correo.

"""
from flask import current_app

from app.extensiones import db
from app.modelos import Integrante, Tema
from servicios import correo, google

from . import fechas


def _texto(t: Tema) -> str:
    lineas = [f"Hola, ya tenemos tema para el evento del {fechas.nombre_fecha(t.fecha).lower()} (10:00 am, hora CDMX):",
              "", f"  {t.titulo}"]
    if t.descripcion:
        lineas += ["", t.descripcion]
    lineas += ["", "Ya puedes ir preparando tu parte. El guion y los detalles están en la app.", "",
               f"— {current_app.config['CANAL_NOMBRE']}"]
    return "\n".join(lineas)


def tarea() -> int:
    """Manda los avisos pendientes de temas de eventos futuros. Devuelve cuántos mandó."""
    hoy = fechas.hoy_cdmx()
    pendientes = Tema.query.filter(Tema.aviso_pendiente.is_(True)).all()
    if not pendientes:
        return 0
    correos = sorted({i.correo for i in Integrante.query.filter_by(activo=True).all() if i.correo})
    enviados = 0
    for t in pendientes:
        if t.fecha < hoy or not correos:
            t.aviso_pendiente, t.aviso_error = False, None if t.fecha < hoy else "No hay correos en el equipo."
            continue
        if not google.configurado():
            t.aviso_error = "Google sin conectar: el aviso se manda en cuanto se conecte."
            continue
        try:
            correo.enviar(correos, f"Tema del {fechas.nombre_fecha(t.fecha).lower()}: {t.titulo}", _texto(t))
            t.aviso_pendiente, t.aviso_error = False, None
            enviados += 1
        except Exception:  # noqa: BLE001
            current_app.logger.exception("No se pudo mandar el aviso del tema del %s", t.fecha)
            t.aviso_error = "No se pudo mandar el correo. Se reintentará en unos minutos."
    db.session.commit()
    return enviados
