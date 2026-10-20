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
    "grabacion": "Grabación con OBS (apagada en la versión corta)",
    "bitacora": "Bitácora de eventos",
}
OCULTOS = {"publicacion", "turnos", "reporte", "grabacion"}   # no corren en la versión corta
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


def _estilo() -> dict:
    """Cómo está la carpeta estilo_cliente/ (para Inicio): referencia, herramientas y si estilo.json se lee bien."""
    from pathlib import Path

    from servicios import estilo
    raiz = Path(current_app.config["ESTILO_DIR"])

    def contar(sub, tipos):
        d = raiz / sub
        return sum(1 for x in d.iterdir() if x.is_file() and x.suffix.lower() in tipos) if d.is_dir() else 0

    r = {"carpeta": str(raiz), "referencia": contar("referencia", estilo.VIDEO),
         "herramientas": contar("herramientas", estilo.VIDEO | estilo.IMAGEN | estilo.AUDIO | {".ttf", ".otf"}),
         "receta": (raiz / "estilo.json").exists(), "activo": None, "error": None}
    if r["receta"]:
        try:
            r["activo"] = bool(estilo.cargar(raiz).get("activo", True))
        except estilo.ErrorEstilo as e:
            r["error"] = str(e)
    return r


@bp.get("/estado")
@login_requerido
def estado():
    from servicios import google, meta, obs
    registros = {e.nombre: e for e in EstadoAgente.query.all()}
    worker = registros.get("worker")
    activo = bool(worker and worker.latido and ahora() - worker.latido < LATIDO_MAX)
    grabaciones = Grabacion.query.order_by(Grabacion.id.desc()).limit(5).all()
    corta = current_app.config.get("VERSION_CORTA", True)
    return jsonify(
        bandeja=conteos(),
        pendientes_por_tipo=_contar(Paquete.tipo, Paquete.estado == "pendiente"),
        grabaciones_conteo=_contar(Grabacion.estado),
        publicaciones_conteo=_contar(Publicacion.estado),
        publicaciones_por_red=_por_red(),
        ultimo_reporte=_ultimo_reporte(),
        worker_activo=activo,
        agentes=[{**(registros[n].a_dict() if n in registros else {"nombre": n}), "titulo": t}
                 for n, t in AGENTES.items() if n != "worker" and not (corta and n in OCULTOS)],
        grabaciones=[x.a_dict() for x in grabaciones],
        google=google.configurado(),
        meta=meta.configurado(),
        canal=current_app.config["CANAL_NOMBRE"],
        temas=_temas_proximos(),
        obs=obs.estado(),
        version_corta=current_app.config.get("VERSION_CORTA", True),
        estilo=_estilo(),
        ideas_nuevas=Idea.query.filter(Idea.estado.in_(("lista", "transcribiendo"))).count(),
    )
