"""Material: /api/bandeja/...

Aquí llegan las 5 imágenes de difusión (al guardar el tema) y los 5 reels editados (cuando llega
el video del celular). Se puede ajustar el texto para publicar, pedir otro recorte de un reel,
descargar los archivos o vaciar todo para empezar de cero. Nada se publica solo.
"""
import shutil
from datetime import date
from pathlib import Path

from flask import Blueprint, abort, current_app, g, jsonify, request, send_from_directory
from sqlalchemy import func

from .extensiones import db
from .modelos import TIPOS_PAQUETE, HistorialPaquete, Paquete, ahora
from .seguridad import login_requerido, solo_en_laptop

bp = Blueprint("bandeja", __name__, url_prefix="/api/bandeja")

TITULO_MAX = 120
TEXTO_MAX = 2200   # límite de texto de Instagram, el más corto de las redes que usamos
EXTENSIONES_VISIBLES = {".png", ".jpg", ".jpeg", ".webp", ".mp4"}

MSG_OCUPADO = "Otra persona cambió esta pieza hace un momento. Ya te mostramos la versión nueva."


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
                  carpeta: str = "", archivos: list[str] | None = None,
                  datos: dict | None = None) -> Paquete:
    """Agrega una pieza nueva a Material. La usan los agentes de difusión y de reels."""
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
                texto=_limpiar_texto(texto, "texto", TEXTO_MAX), carpeta=carpeta, archivos=archivos,
                datos=datos or None)
    p.historial.append(HistorialPaquete(accion="creado"))
    db.session.add(p)
    db.session.commit()
    return p


def actualizar_por_agente(pid: int, cambios: dict, accion: str, detalle: str | None = None) -> None:
    """Cambio hecho por un agente (no por una persona): sube la versión y deja historial."""
    cambios = {**cambios, "version": Paquete.version + 1, "actualizado": ahora()}
    Paquete.query.filter(Paquete.id == pid).update(cambios, synchronize_session=False)
    db.session.add(HistorialPaquete(paquete_id=pid, accion=accion, detalle=(detalle or "")[:300] or None))
    db.session.commit()
    db.session.expire_all()


def conteos() -> dict:
    """{"total": n, "carrusel": n, "reel": n}"""
    filas = dict(db.session.query(Paquete.tipo, func.count(Paquete.id)).group_by(Paquete.tipo).all())
    return {"total": sum(filas.values()), **{t: filas.get(t, 0) for t in TIPOS_PAQUETE}}


def _cambiar(pid: int, version, cambios: dict, accion: str, detalle: str | None = None) -> Paquete:
    """Aplica un cambio solo si nadie más tocó la pieza (misma versión).

    Se hace en un solo UPDATE ... WHERE id=? AND version=?, así dos personas que editan
    el mismo texto a la vez no se pisan.
    """
    if not isinstance(version, int) or isinstance(version, bool):
        raise ErrorBandeja("Falta la versión de la pieza. Recarga la página.")
    cambios = {**cambios, "version": Paquete.version + 1, "actualizado": ahora()}
    filas = (Paquete.query.filter(Paquete.id == pid, Paquete.version == version)
             .update(cambios, synchronize_session=False))
    if filas == 0:
        db.session.rollback()
        if db.session.get(Paquete, pid) is None:
            raise ErrorBandeja("No encontramos esa pieza.", 404)
        raise ErrorBandeja(MSG_OCUPADO, 409)
    db.session.add(HistorialPaquete(paquete_id=pid, usuario_id=g.usuario.id, accion=accion,
                                    detalle=detalle))
    db.session.commit()
    p = db.session.get(Paquete, pid)
    db.session.refresh(p)
    current_app.logger.info("Pieza %s %s por %s", pid, accion, g.usuario.usuario)
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
    paquetes = Paquete.query.order_by(Paquete.fecha_evento.asc(), Paquete.id).limit(200).all()
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
    p = _cambiar(pid, datos.get("version"), cambios, "editado")
    return jsonify(paquete=p.a_dict())


@bp.post("/<int:pid>/recortar")
@login_requerido
def recortar(pid: int):
    """Ajuste manual de inicio/fin de un reel. El worker vuelve a editar el video."""
    datos = _datos()
    actual = db.session.get(Paquete, pid) or abort(404)
    if actual.tipo != "reel" or not (actual.datos or {}).get("grabacion_id"):
        raise ErrorBandeja("Solo los reels se pueden recortar.")
    inicio, fin = datos.get("inicio"), datos.get("fin")
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (inicio, fin)):
        raise ErrorBandeja("Escribe el inicio y el fin en segundos.")
    from agentes.reels import RECORTE_MAX, RECORTE_MIN  # import local: evita ciclo app <-> agentes
    total = float((actual.datos or {}).get("duracion_fuente") or 0)
    if inicio < 0 or fin > total or not RECORTE_MIN <= fin - inicio <= RECORTE_MAX:
        raise ErrorBandeja(f"El reel debe durar entre {RECORTE_MIN:.0f} y {RECORTE_MAX:.0f} segundos "
                           f"y quedar dentro de la grabación (0 a {total:.0f} s).")
    nuevos = {**(actual.datos or {}), "recortar": {"inicio": round(inicio, 2), "fin": round(fin, 2)}}
    nuevos.pop("error_recorte", None)
    p = _cambiar(pid, datos.get("version"), {"datos": nuevos}, "editado",
                 f"Recorte pedido: {inicio:.1f} s a {fin:.1f} s")
    return jsonify(paquete=p.a_dict())


@bp.get("/<int:pid>/archivo/<nombre>")
@login_requerido
@solo_en_laptop
def archivo(pid: int, nombre: str):
    """Vista previa o descarga de una imagen o video. Solo los archivos que la pieza declara."""
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


# --- Vaciar Material (empezar de cero) ------------------------------------------------

def vaciar_material() -> dict:
    """Borra todas las piezas (imágenes de difusión y reels) con su historial y sus archivos en
    paquetes/, y de «Grabaciones recientes» las grabaciones cuyo video ya no está en grabaciones/.
    Los videos que siguen en la carpeta se conservan (si no, se volverían a procesar).
    """
    from .modelos import Grabacion
    n = Paquete.query.count()
    HistorialPaquete.query.delete()
    Paquete.query.delete()
    carpeta_grab = Path(current_app.config["GRABACIONES_DIR"])
    sin_video = [x for x in Grabacion.query.all() if not (carpeta_grab / x.nombre).is_file()]
    for x in sin_video:
        db.session.delete(x)
    db.session.commit()
    carpeta = Path(current_app.config["PAQUETES_DIR"])
    if carpeta.is_dir():
        for x in carpeta.iterdir():
            if x.is_dir():
                shutil.rmtree(x, ignore_errors=True)
            else:
                x.unlink(missing_ok=True)
    current_app.logger.info("Material vaciado: %s piezas y %s grabaciones sin video", n, len(sin_video))
    return {"paquetes": n, "grabaciones": len(sin_video)}


@bp.post("/vaciar")
@login_requerido
@solo_en_laptop
def vaciar():
    if str((request.get_json(silent=True) or {}).get("confirmar", "")).strip().upper() != "BORRAR":
        raise ErrorBandeja("Para vaciar Material escribe BORRAR.")
    r = vaciar_material()
    current_app.logger.info("Material vaciado por %s", g.usuario.usuario)
    return jsonify(**r, conteos=conteos())
