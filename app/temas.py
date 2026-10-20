"""Tema de cada evento: tema, guion, intenciones y revisión técnica. /api/temas/...

    GET /api/temas?desde=AAAA-MM-DD&hasta=AAAA-MM-DD   temas del rango (para el calendario)
    GET /api/temas/<fecha>                             tema de un evento (o null)
    PUT /api/temas/<fecha>                             guarda {titulo, descripcion, cita, guion, intenciones, notas}
    PUT /api/temas/<fecha>/checklist                   {"id": "audio", "hecho": true}
    GET /api/temas/<fecha>/instrucciones               texto listo para pegarlo en Claude (guion)
    POST /api/temas/<fecha>/difusion                   arma ya la difusión (5 imágenes)
    GET/POST/DELETE /api/temas/<fecha>/imagen          imagen del tema (va en los reels, p. ej. el Santo Rostro)

Al guardar un tema nuevo o cambiar su título salen las 5 imágenes de difusión y se avisa al equipo
(correo y Google Calendar) desde el worker.
"""
from datetime import date, timedelta

import io
from pathlib import Path

from flask import Blueprint, current_app, g, jsonify, request, send_file

from .extensiones import db
from .modelos import CHECKLIST, EventoCalendario, Tema, ahora
from .seguridad import login_requerido

bp = Blueprint("temas", __name__, url_prefix="/api/temas")

LIMITES = {"titulo": 120, "descripcion": 400, "cita": 200, "guion": 20000, "intenciones": 4000, "notas": 4000}
MAX_DIAS = 93


class ErrorTema(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje, self.codigo = mensaje, codigo


@bp.errorhandler(ErrorTema)
def _error(e: ErrorTema):
    return jsonify(error=e.mensaje), e.codigo


def _fecha(texto: str) -> date:
    from agentes.fechas import es_dia_de_evento
    try:
        f = date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise ErrorTema("Fecha no válida.") from None
    if not es_dia_de_evento(f):
        raise ErrorTema("Solo hay evento los lunes y viernes.")
    return f


def _texto(d: dict, campo: str, obligatorio: bool = False) -> str:
    valor = d.get(campo, "")
    if valor is None:
        valor = ""
    if not isinstance(valor, str):
        raise ErrorTema(f"El campo {campo} no es válido.")
    valor = valor.replace("\r\n", "\n").strip()
    if campo in ("titulo", "descripcion", "cita"):
        valor = " ".join(valor.split())
    if obligatorio and len(valor) < 3:
        raise ErrorTema("Escribe el tema del evento (al menos 3 letras).")
    if len(valor) > LIMITES[campo]:
        raise ErrorTema(f"El campo {campo} es demasiado largo (máximo {LIMITES[campo]} caracteres).")
    return valor


def tema_de(f: date) -> Tema | None:
    return db.session.get(Tema, f)


def titulo_de(f: date) -> str | None:
    t = tema_de(f)
    return t.titulo if t else None


@bp.get("")
@login_requerido
def listar():
    try:
        desde = date.fromisoformat(request.args.get("desde", ""))
        hasta = date.fromisoformat(request.args.get("hasta", ""))
    except ValueError:
        from agentes.fechas import hoy_cdmx
        desde = hoy_cdmx()
        hasta = desde + timedelta(30)
    if hasta < desde or (hasta - desde).days > MAX_DIAS:
        raise ErrorTema(f"Consulta como máximo {MAX_DIAS} días.")
    temas = Tema.query.filter(Tema.fecha >= desde, Tema.fecha <= hasta).all()
    return jsonify(temas={t.fecha.isoformat(): t.a_dict() for t in temas})


@bp.get("/<fecha>")
@login_requerido
def ver(fecha: str):
    f = _fecha(fecha)
    t = tema_de(f)
    return jsonify(tema=t.a_dict() if t else None, imagen=_ruta_imagen(f).exists())


# --- Imagen del tema: la que el estilo del cliente pone en los reels («temas/{fecha}») ------

IMAGEN_MAX = 15 * 1024 * 1024
TIPOS_IMAGEN = {"image/jpeg", "image/png", "image/webp"}


def _ruta_imagen(f: date) -> Path:
    return Path(current_app.config["ESTILO_DIR"]) / "herramientas" / "temas" / f"{f.isoformat()}.jpg"


@bp.get("/<fecha>/imagen")
@login_requerido
def ver_imagen(fecha: str):
    ruta = _ruta_imagen(_fecha(fecha))
    if not ruta.exists():
        return jsonify(error="Este evento no tiene imagen del tema."), 404
    return send_file(ruta, mimetype="image/jpeg", max_age=0)


@bp.post("/<fecha>/imagen")
@login_requerido
def subir_imagen(fecha: str):
    """Guarda la imagen como JPG (máx. 1600 px) en estilo_cliente/herramientas/temas/<fecha>.jpg."""
    from PIL import Image, ImageOps, UnidentifiedImageError
    f = _fecha(fecha)
    request.max_content_length = IMAGEN_MAX
    if (request.mimetype or "") not in TIPOS_IMAGEN:
        raise ErrorTema("Sube una imagen JPG, PNG o WEBP.")
    datos = request.get_data(cache=False)
    try:
        with Image.open(io.BytesIO(datos)) as im:
            im = ImageOps.exif_transpose(im)
            if im.width * im.height > 60_000_000:
                raise ErrorTema("La imagen es demasiado grande.")
            fondo = Image.new("RGB", im.size, (255, 255, 255))
            fondo.paste(im.convert("RGBA"), mask=im.convert("RGBA").split()[3])
            fondo.thumbnail((1600, 1600))
            ruta = _ruta_imagen(f)
            ruta.parent.mkdir(parents=True, exist_ok=True)
            fondo.save(ruta, "JPEG", quality=92)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ErrorTema("No se pudo leer la imagen. Prueba con otra (JPG o PNG).") from None
    current_app.logger.info("Imagen del tema del %s guardada por %s", f, g.usuario.usuario)
    return jsonify(imagen=True)


@bp.delete("/<fecha>/imagen")
@login_requerido
def borrar_imagen(fecha: str):
    _ruta_imagen(_fecha(fecha)).unlink(missing_ok=True)
    return jsonify(imagen=False)


@bp.put("/<fecha>")
@login_requerido
def guardar(fecha: str):
    f = _fecha(fecha)
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        raise ErrorTema("La solicitud no es válida.")
    titulo = _texto(d, "titulo", obligatorio=True)
    t = tema_de(f)
    nuevo_titulo = t is None or t.titulo != titulo
    if t is None:
        t = Tema(fecha=f, titulo=titulo)
        db.session.add(t)
        t.aviso_pendiente = True
    elif t.titulo != titulo:
        t.aviso_pendiente = True
    t.titulo = titulo
    for campo in ("descripcion", "cita", "guion", "intenciones", "notas"):
        if campo in d:
            setattr(t, campo, _texto(d, campo))
    t.actualizado, t.actualizado_por_id = ahora(), g.usuario.id
    if t.aviso_pendiente:
        ev = db.session.get(EventoCalendario, f)
        if ev and ev.estado == "enviada":
            ev.estado = "pendiente"   # el título del evento en Calendar cambia: se vuelve a sincronizar
    db.session.commit()
    difusion = 0
    if nuevo_titulo and current_app.config.get("DIFUSION_AL_GUARDAR", True):
        difusion = _difusion_al_guardar(f)
    return jsonify(tema=t.a_dict(), difusion=difusion)


def _difusion_al_guardar(f: date) -> int:
    """Versión corta: en cuanto el evento tiene tema (o cambia) salen sus 5 imágenes de difusión.

    Si algo falla, el tema ya quedó guardado y el agente lo vuelve a intentar cada 15 minutos.
    """
    from agentes.carrusel import _existentes, preparar_difusion
    try:
        previa = _existentes(f, "carrusel", "antes")
        return len(preparar_difusion(f, forzar=bool(previa)))
    except Exception:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.exception("No se pudo armar la difusión del %s al guardar el tema", f)
        return 0


@bp.put("/<fecha>/checklist")
@login_requerido
def marcar_checklist(fecha: str):
    f = _fecha(fecha)
    d = request.get_json(silent=True) or {}
    item, hecho = d.get("id"), d.get("hecho")
    if item not in dict(CHECKLIST) or not isinstance(hecho, bool):
        raise ErrorTema("La solicitud no es válida.")
    t = tema_de(f)
    if t is None:
        raise ErrorTema("Primero guarda el tema del evento.", 409)
    marcas = dict(t.checklist or {})
    marcas[item] = hecho
    t.checklist = marcas
    db.session.commit()
    return jsonify(tema=t.a_dict())


def instrucciones(f: date, t: Tema | None) -> str:
    """Texto para pegarlo en Claude y que prepare el guion del evento."""
    from agentes import fechas
    canal = current_app.config["CANAL_NOMBRE"]
    partes = [
        f"Ayúdame a preparar el guion del evento en vivo de {canal}, un espacio católico de oración y reflexión.",
        f"Fecha: {fechas.nombre_fecha(f)}, de 10:00 a 11:00 am (hora CDMX). Dura 1 hora y se transmite en "
        "YouTube, Facebook, Instagram, TikTok y un canal de TV.",
        f"Tema: {t.titulo if t else '(escribe aquí el tema)'}",
    ]
    if t and t.descripcion:
        partes.append(f"De qué trata: {t.descripcion}")
    if t and t.cita:
        partes.append(f"Cita bíblica: {t.cita}")
    if t and t.intenciones:
        partes.append("Intenciones recibidas (léelas sin apellidos ni datos personales si no hay permiso):\n"
                      + t.intenciones)
    if t and t.notas:
        partes.append(f"Notas del equipo: {t.notas}")
    if t and t.guion:
        partes.append("Ya tengo este borrador; mejóralo en lugar de empezar de cero:\n" + t.guion)
    else:
        partes.append(
            "Todavía no tenemos guion. Primero busca qué enseña la Iglesia Católica sobre este tema en fuentes "
            "confiables: la Sagrada Escritura, el Catecismo de la Iglesia Católica, documentos del Papa y del "
            "Magisterio, los Padres de la Iglesia, la vida de los santos y oraciones aprobadas por la Iglesia. "
            "Dame un resumen corto de lo que encontraste con la fuente exacta de cada punto (libro, capítulo y "
            "versículo; número del Catecismo; nombre del documento) y con eso arma el guion. No inventes citas: "
            "si no estás seguro de una fuente, dilo.")
    partes.append(
        "Quiero el guion en bloques con minutos aproximados: bienvenida, oración inicial, desarrollo del tema "
        "(con la lectura o cita), momento de intenciones, reflexión práctica para la vida diaria, oración final "
        "y despedida invitando al siguiente evento y a seguir las redes. Tono cálido, sencillo y cercano. "
        "Al final dame 5 frases cortas de alto impacto, una para cada reel, y 5 para las imágenes de difusión.")
    return "\n\n".join(partes)


@bp.get("/<fecha>/instrucciones")
@login_requerido
def ver_instrucciones(fecha: str):
    f = _fecha(fecha)
    return jsonify(texto=instrucciones(f, tema_de(f)))


@bp.post("/<fecha>/difusion")
@login_requerido
def generar_difusion(fecha: str):
    from agentes.carrusel import preparar_difusion
    f = _fecha(fecha)
    if tema_de(f) is None:
        raise ErrorTema("Primero guarda el tema: la difusión se arma con él.", 409)
    nuevos = preparar_difusion(f, forzar=bool((request.get_json(silent=True) or {}).get("otra")))
    return jsonify(creados=len(nuevos))
