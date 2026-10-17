"""Estado general para la pantalla de Inicio y Configuración: /api/estado"""
from datetime import timedelta

from flask import Blueprint, current_app, jsonify
from sqlalchemy import func

from .bandeja import conteos
from .extensiones import db
from .modelos import EstadoAgente, Grabacion, Idea, Paquete, Publicacion, Reporte, Tema, ahora
from .seguridad import login_requerido

bp = Blueprint("panel", __name__, url_prefix="/api")

AGENTES = {
    "worker": "Worker",
    "carrusel": "Difusión",
    "reels": "Reels",
    "publicacion": "Publicación",
    "turnos": "Turnos",
    "reporte": "Reporte semanal",
    "avisos": "Avisos del tema",
    "ideas": "Ideas por voz",
    "grabacion": "Grabación con OBS",
}
LATIDO_MAX = timedelta(minutes=3)


def _contar(columna, *filtros) -> dict:
    """{valor: cantidad} agrupando por una columna (para el diagrama de Inicio)."""
    consulta = db.session.query(columna, func.count()).filter(*filtros).group_by(columna)
    return {valor: n for valor, n in consulta.all()}


def _por_red() -> dict:
    """{red: {estado: cantidad}} para pintar cada red en el diagrama."""
    resultado: dict = {}
    for red, est, n in db.session.query(Publicacion.red, Publicacion.estado, func.count())             .group_by(Publicacion.red, Publicacion.estado).all():
        resultado.setdefault(red, {})[est] = n
    return resultado


def _ultimo_reporte() -> dict | None:
    r = Reporte.query.order_by(Reporte.semana.desc()).first()
    return {"semana": r.semana.isoformat(), "titulo": r.datos.get("titulo"),
            "mejorar": len(r.datos.get("mejorar", []))} if r else None


def _temas_proximos(dias: int = 14) -> list[dict]:
    """Los eventos de las próximas 2 semanas con su tema (o sin él), para el aviso de Inicio."""
    from agentes import fechas
    hoy = fechas.hoy_cdmx()
    lista = fechas.proximos_eventos(hoy, dias)
    temas = {t.fecha: t for t in Tema.query.filter(Tema.fecha.in_(lista)).all()}
    return [{"fecha": f.isoformat(), "tema": temas[f].titulo if f in temas else None,
             "guion": bool(temas[f].guion.strip()) if f in temas else False} for f in lista]


@bp.get("/estado")
@login_requerido
def estado():
    from servicios import google, meta, obs
    registros = {e.nombre: e for e in EstadoAgente.query.all()}
    worker = registros.get("worker")
    activo = bool(worker and worker.latido and ahora() - worker.latido < LATIDO_MAX)
    grabaciones = Grabacion.query.order_by(Grabacion.id.desc()).limit(5).all()
    return jsonify(
        bandeja=conteos(),
        pendientes_por_tipo=_contar(Paquete.tipo, Paquete.estado == "pendiente"),
        grabaciones_conteo=_contar(Grabacion.estado),
        publicaciones_conteo=_contar(Publicacion.estado),
        publicaciones_por_red=_por_red(),
        ultimo_reporte=_ultimo_reporte(),
        worker_activo=activo,
        agentes=[{**(registros[n].a_dict() if n in registros else {"nombre": n}), "titulo": t}
                 for n, t in AGENTES.items() if n != "worker"],
        grabaciones=[x.a_dict() for x in grabaciones],
        google=google.configurado(),
        meta=meta.configurado(),
        canal=current_app.config["CANAL_NOMBRE"],
        temas=_temas_proximos(),
        obs=obs.estado(),
        ideas_nuevas=Idea.query.filter(Idea.estado.in_(("lista", "transcribiendo"))).count(),
    )
