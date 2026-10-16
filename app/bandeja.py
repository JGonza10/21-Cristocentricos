"""Bandeja de aprobación: /api/bandeja/...

Reglas:
- Todo lo que preparan los agentes entra como "pendiente".
- Solo una persona con sesión puede aprobar, rechazar o editar el texto.
- El agente de publicación (fase 5) solo toma lo que está "aprobado".
- Si se edita algo, primero debe estar pendiente: lo aprobado no cambia a escondidas.
"""
from datetime import date
from pathlib import Path

from flask import Blueprint, abort, current_app, g, jsonify, request, send_from_directory
from sqlalchemy import func

from .extensiones import db
from .modelos import ESTADOS_PAQUETE, TIPOS_PAQUETE, HistorialPaquete, Paquete, ahora
from .seguridad import login_requerido

bp = Blueprint("bandeja", __name__, url_prefix="/api/bandeja")

TITULO_MAX = 120
TEXTO_MAX = 2200   # límite de texto de Instagram, el más corto de las redes que usamos
MOTIVO_MAX = 300
EXTENSIONES_VISIBLES = {".png", ".jpg", ".jpeg", ".webp", ".mp4"}

MSG_OCUPADO = "Otra persona cambió este paquete hace un momento. Ya te mostramos la versión nueva."
MSG_NO_EDITABLE = "Solo se puede editar un paquete pendiente. Regrésalo a pendientes primero."


class ErrorBandeja(Exception):
    """Error con mensaje amable para el usuario."""

    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.codigo = codigo


# --- Funciones que usan los agentes y la API ----------------------------------------

def _limpiar_texto(valor, campo: str, maximo: int, obligatorio: bool = False) -> str:
    if not isinstance(valor, str):
        raise ErrorBandeja(f"El {campo} no es válido.")
    valor = valor.replace("\r\n", "\n").strip()
    if obligatorio and not valor:
        raise ErrorBandeja(f"El {campo} no puede ir vacío.")
    if len(valor) > maximo:
        raise ErrorBandeja(f"El {campo} es demasiado largo (máximo {maximo} caracteres).")
    return valor


def _nombre_archivo_valido(nombre) -> bool:
    return (isinstance(nombre, str) and 0 < len(nombre) <= 100 and nombre == Path(nombre).name
            and not nombre.startswith("."))


def crear_paquete(tipo: str, fecha_evento: date, titulo: str, texto: str = "",
                  carpeta: str = "", archivos: list[str] | None = None) -> Paquete:
    """Mete un paquete nuevo a la bandeja como pendiente. Lo usan los agentes (fases 3 y 4)."""
    if tipo not in TIPOS_PAQUETE:
        raise ErrorBandeja("Tipo de paquete no válido.")
    if not isinstance(fecha_evento, date):
        raise ErrorBandeja("Fecha de evento no válida.")
    archivos = list(archivos or [])
    if not all(_nombre_archivo_valido(a) for a in archivos):
        raise ErrorBandeja("Nombre de archivo no válido.")
    carpeta = (carpeta or "").replace("\\", "/").strip("/")
    if carpeta and (".." in carpeta.split("/") or len(carpeta) > 200):
        raise ErrorBandeja("Carpeta no válida.")

    p = Paquete(tipo=tipo, fecha_evento=fecha_evento,
                titulo=_limpiar_texto(titulo, "título", TITULO_MAX, obligatorio=True),
                texto=_limpiar_texto(texto, "texto", TEXTO_MAX), carpeta=carpeta, archivos=archivos)
    p.historial.append(HistorialPaquete(accion="creado"))
    db.session.add(p)
    db.session.commit()
    return p


def paquetes_aprobados() -> list[Paquete]:
    """Lo único que el agente de publicación tiene permitido tocar."""
    return Paquete.query.filter_by(estado="aprobado").order_by(Paquete.fecha_evento).all()


def conteos() -> dict:
    filas = db.session.query(Paquete.estado, func.count(Paquete.id)).group_by(Paquete.estado).all()
    resultado = {e: 0 for e in ESTADOS_PAQUETE}
    resultado.update(dict(filas))
    return resultado


def _cambiar(pid: int, version, estados_permitidos: tuple, cambios: dict,
             accion: str, detalle: str | None = None) -> Paquete:
    """Aplica un cambio solo si nadie más tocó el paquete (misma versión) y su estado lo permite.

    Se hace en un solo UPDATE ... WHERE id=? AND version=? AND estado IN (...), así dos
    personas no pueden aprobar y rechazar lo mismo al mismo tiempo.
    """
    if not isinstance(version, int) or isinstance(version, bool):
        raise ErrorBandeja("Falta la versión del paquete. Recarga la página.")
    cambios = {**cambios, "version": Paquete.version + 1, "actualizado": ahora()}
    filas = (Paquete.query
             .filter(Paquete.id == pid, Paquete.version == version, Paquete.estado.in_(estados_permitidos))
             .update(cambios, synchronize_session=False))
    if filas == 0:
        db.session.rollback()
        actual = db.session.get(Paquete, pid)
        if actual is None:
            raise ErrorBandeja("No encontramos ese paquete.", 404)
        if actual.version != version:
            raise ErrorBandeja(MSG_OCUPADO, 409)
        raise ErrorBandeja(MSG_NO_EDITABLE if accion == "editado"
                           else "Ese paquete ya no está en un estado que permita esta acción.", 409)
    db.session.add(HistorialPaquete(paquete_id=pid, usuario_id=g.usuario.id, accion=accion,
                                    detalle=detalle))
    db.session.commit()
    p = db.session.get(Paquete, pid)
    db.session.refresh(p)
    current_app.logger.info("Paquete %s %s por %s", pid, accion, g.usuario.usuario)
    return p


# --- Rutas --------------------------------------------------------------------------

@bp.errorhandler(ErrorBandeja)
def _error_bandeja(e: ErrorBandeja):
    cuerpo = {"error": e.mensaje}
    if e.codigo == 409:
        pid = request.view_args.get("pid") if request.view_args else None
        actual = db.session.get(Paquete, pid) if pid else None
        if actual:
            cuerpo["paquete"] = actual.a_dict()
    return jsonify(cuerpo), e.codigo


def _datos() -> dict:
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        raise ErrorBandeja("La solicitud no es válida.")
    return datos


@bp.get("")
@login_requerido
def listar():
    estado = request.args.get("estado", "pendiente")
    if estado not in ESTADOS_PAQUETE:
        raise ErrorBandeja("Estado no válido.")
    orden = Paquete.fecha_evento.asc() if estado == "pendiente" else Paquete.actualizado.desc()
    paquetes = Paquete.query.filter_by(estado=estado).order_by(orden, Paquete.id).limit(100).all()
    return jsonify(paquetes=[p.a_dict() for p in paquetes], conteos=conteos())


@bp.get("/conteos")
@login_requerido
def ver_conteos():
    return jsonify(conteos=conteos())


@bp.get("/<int:pid>")
@login_requerido
def detalle(pid: int):
    p = db.session.get(Paquete, pid) or abort(404)
    return jsonify(paquete=p.a_dict(), historial=[h.a_dict() for h in p.historial])


@bp.patch("/<int:pid>")
@login_requerido
def editar(pid: int):
    datos = _datos()
    cambios = {}
    if "titulo" in datos:
        cambios["titulo"] = _limpiar_texto(datos["titulo"], "título", TITULO_MAX, obligatorio=True)
    if "texto" in datos:
        cambios["texto"] = _limpiar_texto(datos["texto"], "texto", TEXTO_MAX)
    if not cambios:
        raise ErrorBandeja("No hay nada que guardar.")
    p = _cambiar(pid, datos.get("version"), ("pendiente",), cambios, "editado")
    return jsonify(paquete=p.a_dict())


@bp.post("/<int:pid>/aprobar")
@login_requerido
def aprobar(pid: int):
    datos = _datos()
    p = _cambiar(pid, datos.get("version"), ("pendiente",),
                 {"estado": "aprobado", "motivo_rechazo": None,
                  "revisado_por_id": g.usuario.id, "revisado_en": ahora()}, "aprobado")
    return jsonify(paquete=p.a_dict(), conteos=conteos())


@bp.post("/<int:pid>/rechazar")
@login_requerido
def rechazar(pid: int):
    datos = _datos()
    motivo = _limpiar_texto(datos.get("motivo", ""), "motivo", MOTIVO_MAX)
    p = _cambiar(pid, datos.get("version"), ("pendiente",),
                 {"estado": "rechazado", "motivo_rechazo": motivo or None,
                  "revisado_por_id": g.usuario.id, "revisado_en": ahora()}, "rechazado", motivo or None)
    return jsonify(paquete=p.a_dict(), conteos=conteos())


@bp.post("/<int:pid>/reabrir")
@login_requerido
def reabrir(pid: int):
    """Regresa un paquete aprobado o rechazado a pendientes (para corregirlo o pensarlo otra vez)."""
    datos = _datos()
    p = _cambiar(pid, datos.get("version"), ("aprobado", "rechazado"),
                 {"estado": "pendiente", "motivo_rechazo": None,
                  "revisado_por_id": None, "revisado_en": None}, "reabierto")
    return jsonify(paquete=p.a_dict(), conteos=conteos())


@bp.get("/<int:pid>/archivo/<nombre>")
@login_requerido
def archivo(pid: int, nombre: str):
    """Vista previa de una imagen o video del paquete. Solo los archivos que el paquete declara."""
    p = db.session.get(Paquete, pid) or abort(404)
    if nombre not in (p.archivos or []) or Path(nombre).suffix.lower() not in EXTENSIONES_VISIBLES:
        abort(404)
    raiz = Path(current_app.config["PAQUETES_DIR"]).resolve()
    carpeta = (raiz / p.carpeta).resolve()
    if carpeta != raiz and raiz not in carpeta.parents:
        abort(404)
    # send_from_directory también rechaza rutas que intenten salirse de la carpeta.
    resp = send_from_directory(carpeta, nombre, max_age=0)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp
