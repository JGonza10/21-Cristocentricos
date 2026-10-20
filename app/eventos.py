"""Eventos (programas en vivo) y sus pasos: /api/eventos/... e /api/integrantes."""
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_from_directory
from pypdf.errors import PdfReadError

from servicios import difusion, guion

from .extensiones import db
from .modelos import REVISION, Evento, Integrante
from .seguridad import login_requerido

bp = Blueprint("eventos", __name__, url_prefix="/api")

PATRON_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
PATRON_MES = re.compile(r"^(\d{4})-(\d{2})$")
GUION_MAX = 100_000
ARCHIVO_MAX = 10 * 1024 * 1024
MSG_PASO_1 = "Primero completa el paso 1: tema y guion."
MSG_PASO_2 = "Primero genera las imágenes de difusión (paso 2)."


def hoy_cdmx() -> date:
    """Fecha de hoy en la Ciudad de México (UTC-6, sin horario de verano desde 2022)."""
    return datetime.now(timezone(timedelta(hours=-6))).date()


def _fecha(texto: str) -> date | None:
    try:
        d = date.fromisoformat(texto)
    except ValueError:
        return None
    return d if 2024 <= d.year <= 2100 else None


def _evento(texto: str, crear: bool = False) -> Evento | None:
    d = _fecha(texto)
    if d is None:
        return None
    ev = Evento.query.filter_by(fecha=d).first()
    if ev is None and crear:
        ev = Evento(fecha=d, hora="10:00", tema="", guion_md="", frases=[], revision={})
        db.session.add(ev)
    return ev


def _texto(valor, maximo: int) -> str | None:
    return valor.strip() if isinstance(valor, str) and len(valor.strip()) <= maximo else None


@bp.get("/eventos")
@login_requerido
def listar():
    m = PATRON_MES.match(request.args.get("mes", ""))
    if not m or not 1 <= int(m.group(2)) <= 12:
        return jsonify(error="Mes no válido."), 400
    anio, mes = int(m.group(1)), int(m.group(2))
    inicio = date(anio, mes, 1)
    fin = date(anio + (mes == 12), mes % 12 + 1, 1)
    eventos = Evento.query.filter(Evento.fecha >= inicio, Evento.fecha < fin).order_by(Evento.fecha).all()
    return jsonify(eventos=[e.a_dict(completo=False) for e in eventos])


@bp.get("/eventos/proximos")
@login_requerido
def proximos():
    eventos = Evento.query.filter(Evento.fecha >= hoy_cdmx()).order_by(Evento.fecha).limit(5).all()
    return jsonify(eventos=[e.a_dict(completo=False) for e in eventos], hoy=hoy_cdmx().isoformat())


@bp.get("/eventos/<fecha>")
@login_requerido
def ver(fecha):
    if _fecha(fecha) is None:
        return jsonify(error="Fecha no válida."), 400
    ev = _evento(fecha) or Evento(fecha=_fecha(fecha), hora="10:00", tema="", guion_md="", frases=[], revision={})
    return jsonify(evento=ev.a_dict())


@bp.put("/eventos/<fecha>")
@login_requerido
def guardar(fecha):
    datos = request.get_json(silent=True) or {}
    ev = _evento(fecha, crear=True)
    if ev is None:
        return jsonify(error="Fecha no válida."), 400
    if "tema" in datos:
        tema = _texto(datos["tema"], 120)
        if tema is None:
            return jsonify(error="El tema debe tener máximo 120 caracteres."), 400
        ev.tema = tema
    if "hora" in datos:
        if not isinstance(datos["hora"], str) or not PATRON_HORA.match(datos["hora"]):
            return jsonify(error="Escribe la hora como 10:00."), 400
        ev.hora = datos["hora"]
    if "guion_md" in datos:
        texto = _texto(datos["guion_md"], GUION_MAX)
        if texto is None:
            return jsonify(error="El guion es demasiado largo."), 400
        ev.guion_md = guion.quitar_secciones(texto) if texto else ""
    if "frases" in datos:
        frases = datos["frases"]
        if (not isinstance(frases, list) or len(frases) > 20
                or not all(isinstance(f, str) and 0 < len(f.strip()) <= 200 for f in frases)):
            return jsonify(error="Cada frase debe tener entre 1 y 200 caracteres (máximo 20 frases)."), 400
        ev.frases = [f.strip() for f in frases]
    db.session.commit()
    return jsonify(evento=ev.a_dict())


@bp.post("/eventos/<fecha>/guion")
@login_requerido
def subir_guion(fecha):
    request.max_content_length = ARCHIVO_MAX
    ev = _evento(fecha, crear=True)
    if ev is None:
        return jsonify(error="Fecha no válida."), 400
    archivo = request.files.get("archivo")
    if archivo is None or not archivo.filename:
        return jsonify(error="Elige un archivo PDF o Markdown."), 400
    datos = archivo.read()
    nombre = archivo.filename.lower()
    try:
        if nombre.endswith(".pdf") and datos.startswith(b"%PDF-"):
            texto = guion.convertir(datos)
        elif nombre.endswith((".md", ".txt")):
            texto = guion.quitar_secciones(datos.decode("utf-8"))
        else:
            return jsonify(error="Solo se aceptan archivos PDF, .md o .txt."), 400
    except (PdfReadError, UnicodeDecodeError, ValueError):
        current_app.logger.warning("No se pudo leer el guion %s", archivo.filename, exc_info=True)
        return jsonify(error="No pudimos leer el archivo. Revisa que no esté dañado o protegido."), 400
    if not texto.strip():
        return jsonify(error="El archivo no tiene texto (¿es un PDF escaneado?). Pega el texto a mano."), 400
    ev.guion_md = texto[:GUION_MAX]
    ev.frases = guion.frases_difusion(ev.guion_md, ev.tema)
    db.session.commit()
    return jsonify(evento=ev.a_dict())


@bp.post("/eventos/<fecha>/frases")
@login_requerido
def sugerir_frases(fecha):
    ev = _evento(fecha)
    if ev is None or not ev.guion_md.strip():
        return jsonify(error="Primero carga el guion."), 409
    ev.frases = guion.frases_difusion(ev.guion_md, ev.tema)
    db.session.commit()
    return jsonify(evento=ev.a_dict())


def _carpeta_imagenes(ev: Evento) -> Path:
    return Path(current_app.config["PAQUETES_DIR"]) / ev.fecha.isoformat() / "difusion"


@bp.post("/eventos/<fecha>/imagenes")
@login_requerido
def generar_imagenes(fecha):
    ev = _evento(fecha)
    if ev is None or not ev.pasos()["datos"]:
        return jsonify(error=MSG_PASO_1), 409
    difusion.generar(ev.tema, ev.fecha, ev.hora, ev.frases, _carpeta_imagenes(ev))
    ev.imagenes_firma = ev.firma()
    db.session.commit()
    return jsonify(evento=ev.a_dict())


@bp.get("/eventos/<fecha>/imagenes/<int:numero>.png")
@login_requerido
def imagen(fecha, numero):
    ev = _evento(fecha)
    if ev is None or not ev.imagenes_firma or not 1 <= numero <= 5:
        return jsonify(error="No encontramos lo que buscas."), 404
    resp = send_from_directory(_carpeta_imagenes(ev), f"{numero}.png", max_age=0)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@bp.put("/eventos/<fecha>/revision")
@login_requerido
def revision(fecha):
    ev = _evento(fecha)
    if ev is None or not ev.pasos()["imagenes"]:
        return jsonify(error=MSG_PASO_2), 409
    datos = request.get_json(silent=True) or {}
    if not isinstance(datos, dict) or not all(k in REVISION and isinstance(v, bool) for k, v in datos.items()):
        return jsonify(error="La revisión no es válida."), 400
    ev.revision = {**ev.revision, **datos}
    db.session.commit()
    return jsonify(evento=ev.a_dict())


@bp.put("/eventos/<fecha>/integrantes")
@login_requerido
def asignar(fecha):
    ev = _evento(fecha, crear=True)
    if ev is None:
        return jsonify(error="Fecha no válida."), 400
    ids = (request.get_json(silent=True) or {}).get("ids")
    if not isinstance(ids, list) or len(ids) > 50 or not all(isinstance(i, int) for i in ids):
        return jsonify(error="La lista del equipo no es válida."), 400
    ev.integrantes = Integrante.query.filter(Integrante.id.in_(ids)).all() if ids else []
    db.session.commit()
    return jsonify(evento=ev.a_dict(completo=False))


@bp.get("/integrantes")
@login_requerido
def integrantes():
    return jsonify(integrantes=[i.a_dict() for i in Integrante.query.order_by(Integrante.nombre)])


@bp.post("/integrantes")
@login_requerido
def agregar_integrante():
    nombre = _texto((request.get_json(silent=True) or {}).get("nombre"), 60)
    if not nombre or len(nombre) < 2:
        return jsonify(error="Escribe un nombre de 2 a 60 caracteres."), 400
    nombre = re.sub(r"\s+", " ", nombre)
    if Integrante.query.filter(db.func.lower(Integrante.nombre) == nombre.lower()).first():
        return jsonify(error="Ese nombre ya está en el equipo."), 409
    i = Integrante(nombre=nombre)
    db.session.add(i)
    db.session.commit()
    return jsonify(integrante=i.a_dict()), 201


@bp.delete("/integrantes/<int:iid>")
@login_requerido
def quitar_integrante(iid):
    i = db.session.get(Integrante, iid)
    if i is None:
        return jsonify(error="No encontramos lo que buscas."), 404
    db.session.delete(i)
    db.session.commit()
    return jsonify(ok=True)
