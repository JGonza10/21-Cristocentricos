"""Estado general para la pantalla de Inicio y Configuración: /api/estado"""
from datetime import timedelta

from flask import Blueprint, current_app, jsonify

from .bandeja import conteos
from .modelos import EstadoAgente, Grabacion, ahora
from .seguridad import login_requerido

bp = Blueprint("panel", __name__, url_prefix="/api")

AGENTES = {
    "worker": "Worker",
    "carrusel": "Carrusel",
    "reels": "Reels",
    "publicacion": "Publicación",
    "turnos": "Turnos",
}
LATIDO_MAX = timedelta(minutes=3)


@bp.get("/estado")
@login_requerido
def estado():
    from servicios import google, meta
    registros = {e.nombre: e for e in EstadoAgente.query.all()}
    worker = registros.get("worker")
    activo = bool(worker and worker.latido and ahora() - worker.latido < LATIDO_MAX)
    grabaciones = Grabacion.query.order_by(Grabacion.id.desc()).limit(5).all()
    return jsonify(
        bandeja=conteos(),
        worker_activo=activo,
        agentes=[{**(registros[n].a_dict() if n in registros else {"nombre": n}), "titulo": t}
                 for n, t in AGENTES.items() if n != "worker"],
        grabaciones=[x.a_dict() for x in grabaciones],
        google=google.configurado(),
        meta=meta.configurado(),
        canal=current_app.config["CANAL_NOMBRE"],
    )
