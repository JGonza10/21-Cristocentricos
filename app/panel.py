"""Estado general para la pantalla de Inicio y Configuración: /api/estado"""
from datetime import timedelta

from flask import Blueprint, current_app, jsonify
from sqlalchemy import func

from .bandeja import conteos
from .extensiones import db
from .modelos import EstadoAgente, Grabacion, Idea, Tema, ahora
from .seguridad import login_requerido

bp = Blueprint("panel", __name__, url_prefix="/api")

AGENTES = {
    "worker": "Worker",
    "carrusel": "Imágenes de difusión",
    "reels": "Reels con el estilo del cliente",
    "avisos": "Avisos del tema por correo",
    "ideas": "Ideas por voz",
}
LATIDO_MAX = timedelta(minutes=3)


def _contar(columna, *filtros) -> dict:
    """{valor: cantidad} agrupando por una columna."""
    consulta = db.session.query(columna, func.count()).filter(*filtros).group_by(columna)
    return {valor: n for valor, n in consulta.all()}


def _temas_proximos(dias: int = 14) -> list[dict]:
    """Los eventos de las próximas 2 semanas con su tema (o sin él), para el aviso de Inicio."""
    from agentes import fechas

    from .temas import dias_de_evento
    lista = dias_de_evento(fechas.hoy_cdmx(), dias)
    temas = {t.fecha: t for t in Tema.query.filter(Tema.fecha.in_(lista)).all()}
    return [{"fecha": f.isoformat(), "tema": temas[f].titulo if f in temas else None,
             "guion": bool(temas[f].guion.strip()) if f in temas else False} for f in lista]


def _eventos_extra() -> list[str]:
    """Días con tema que no son lunes ni viernes (6 meses atrás y 1 año adelante), para el frontend."""
    from agentes import fechas
    hoy = fechas.hoy_cdmx()
    consulta = db.session.query(Tema.fecha).filter(Tema.fecha >= hoy - timedelta(183), Tema.fecha <= hoy + timedelta(366))
    return [f.isoformat() for (f,) in consulta.order_by(Tema.fecha) if not fechas.es_dia_fijo(f)]


def estado_laptop() -> dict:
    """Lo que solo sabe la laptop (estilo del cliente y Gmail). El worker lo guarda en la base cada
    5 minutos para que la nube lo muestre; en la laptop se calcula al momento."""
    from servicios import google
    return {"estilo": _estilo(), "google": google.configurado()}


def _de_la_laptop() -> dict:
    """En la nube: lo último que reportó la laptop (o vacío si aún no reporta)."""
    import json
    e = db.session.get(EstadoAgente, "laptop")
    try:
        return json.loads(e.mensaje) if e and e.mensaje else {}
    except ValueError:
        return {}


def _estilo() -> dict:
    """Cómo está la carpeta estilo_cliente/ (para Inicio): referencia, herramientas y si estilo.json se lee bien."""
    from pathlib import Path

    from servicios import estilo
    raiz = Path(current_app.config["ESTILO_DIR"])

    def contar(sub, tipos):
        d = raiz / sub
        return sum(1 for x in d.iterdir() if x.is_file() and x.suffix.lower() in tipos) if d.is_dir() else 0

    r = {"carpeta": raiz.name, "referencia": contar("referencia", estilo.VIDEO),
         "herramientas": contar("herramientas", estilo.VIDEO | estilo.IMAGEN | estilo.AUDIO | {".ttf", ".otf"}),
         "receta": (raiz / "estilo.json").exists(), "activo": None, "error": None}
    if r["receta"]:
        try:
            r["activo"] = bool(estilo.cargar(raiz).get("activo", True))
        except estilo.ErrorEstilo as e:
            r["error"] = str(e)[:120]
    return r


@bp.get("/salud")
def salud():
    """Para el healthcheck de Railway: responde si la app y la base contestan (sin datos)."""
    from sqlalchemy import text
    db.session.execute(text("SELECT 1"))
    return jsonify(ok=True)


@bp.get("/estado")
@login_requerido
def estado():
    laptop = _de_la_laptop() if current_app.config["EN_NUBE"] else estado_laptop()
    registros = {e.nombre: e for e in EstadoAgente.query.all()}
    worker = registros.get("worker")
    activo = bool(worker and worker.latido and ahora() - worker.latido < LATIDO_MAX)
    grabaciones = Grabacion.query.order_by(Grabacion.id.desc()).limit(5).all()
    return jsonify(
        material=conteos(),
        grabaciones_conteo=_contar(Grabacion.estado),
        worker_activo=activo,
        agentes=[{**(registros[n].a_dict() if n in registros else {"nombre": n}), "titulo": t}
                 for n, t in AGENTES.items() if n != "worker"],
        grabaciones=[x.a_dict() for x in grabaciones],
        google=bool(laptop.get("google")),
        canal=current_app.config["CANAL_NOMBRE"],
        modo=current_app.config["MODO"],
        temas=_temas_proximos(),
        eventos_extra=_eventos_extra(),
        estilo=laptop.get("estilo") or {},
        ideas_nuevas=Idea.query.filter(Idea.estado.in_(("lista", "transcribiendo"))).count(),
    )
