"""Avance guiado de cada evento: los 7 pasos de la versión corta, en orden.

Cada paso está hecho, omitido (no era necesario) o pendiente. Muchos se comprueban solos con los
datos del sistema; los demás se marcan a mano. El paso actual es el primero pendiente: solo ese se
puede marcar a mano, así no se brinca ninguno.

    GET /api/avance/activo           el evento de hoy o el próximo (los pasados van a la bitácora)
    GET /api/avance/<fecha>          avance de un evento
    PUT /api/avance/<fecha>/<paso>   {"accion": "hecho" | "omitir" | "deshacer", "nota": "..."}
"""
from datetime import date, timedelta

from flask import Blueprint, current_app, g, jsonify, request

from .extensiones import db
from .modelos import CHECKLIST, PASOS_EVENTO, AvancePaso, BitacoraEvento, Grabacion, Paquete, Tema, Turno
from .seguridad import login_requerido

bp = Blueprint("avance", __name__, url_prefix="/api/avance")

DIAS_ATRAS = 60  # la bitácora revisa hasta 60 días atrás por si el worker estuvo apagado

# Cómo se cumple cada paso (lo ve la persona en la tarjeta). Versión corta: 7 pasos.
COMO = {
    "tema": "Se marca solo cuando el evento tiene tema guardado en el calendario.",
    "guion": "Se marca solo cuando el guion está guardado: escríbelo, pégalo o cárgalo desde un archivo (.docx, .pdf, "
             ".txt). Si no hay guion, «Preparar guion con Claude» copia las instrucciones para buscar el tema en "
             "fuentes de la Iglesia; pega el resultado y guarda.",
    "difusion": "Se marca solo cuando las 5 imágenes para redes del tema están listas en Material ("
                "«Crear imágenes» las hace al momento; también salen solas al guardar el tema).",
    "revision": "Se marca solo cuando palomeas toda la revisión técnica del día.",
    "grabacion": "Se marca solo cuando llega a grabaciones/ el video limpio del celular (o se sube desde la app).",
    "reels": "Se marca solo cuando los 5 reels editados con el estilo del cliente están listos en Material.",
    "ideas": "Último paso: guarda en «Ideas» lo que surgió en el evento y márcalo como hecho (u omítelo).",
}


def momento(p: Paquete) -> str:
    """'antes' = difusión del evento; 'despues' = lo que sale del video (reels y carrusel de escenas)."""
    m = (p.datos or {}).get("momento")
    if m in ("antes", "despues"):
        return m
    return "despues" if p.tipo == "reel" else "antes"   # carruseles viejos eran la invitación


class ErrorAvance(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje, self.codigo = mensaje, codigo


@bp.errorhandler(ErrorAvance)
def _error(e: ErrorAvance):
    return jsonify(error=e.mensaje), e.codigo


def _fecha(texto: str) -> date:
    from agentes.fechas import es_dia_de_evento
    try:
        f = date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise ErrorAvance("Fecha no válida.") from None
    if not es_dia_de_evento(f):
        raise ErrorAvance("Solo hay evento los lunes y viernes.")
    return f


def _plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def _automatico(f: date) -> dict:
    """{paso: (estado, detalle)} de lo que el sistema puede comprobar solo."""
    r = {}
    tema = db.session.get(Tema, f)
    if tema:
        r["tema"] = ("hecho", f"Tema: {tema.titulo}.")
        if tema.guion.strip():
            r["guion"] = ("hecho", "Guion guardado.")
        else:
            r["guion"] = ("pendiente", "Sin guion. Usa «Preparar guion con Claude» para buscar el tema en "
                                       "fuentes de la Iglesia, o márcalo como omitido si no hace falta.")
    if tema and tema.checklist:
        marcas = tema.checklist
        faltan = [t for k, t in CHECKLIST if not marcas.get(k)]
        r["revision"] = ("hecho", "Revisión técnica completa.") if not faltan else \
            ("pendiente", f"Faltan {len(faltan)} de {len(CHECKLIST)} puntos de la revisión.")

    difusion = [p for p in Paquete.query.filter_by(fecha_evento=f, tipo="carrusel").all() if momento(p) == "antes"]
    if difusion:
        n = sum(len(p.archivos or []) for p in difusion[-1:])
        r["difusion"] = ("hecho", f"{_plural(n, 'imagen de difusión lista', 'imágenes de difusión listas')} en Material.")

    grab = Grabacion.query.filter_by(fecha_evento=f).order_by(Grabacion.id.desc()).first()
    if grab and grab.estado == "error":
        r["grabacion"] = ("pendiente", grab.error or "La grabación falló.")
    elif grab:
        r["grabacion"] = ("hecho", f"Llegó {grab.nombre}.")

    reels = [p for p in Paquete.query.filter_by(fecha_evento=f, tipo="reel").all() if momento(p) == "despues"]
    if reels:
        r["reels"] = ("hecho", f"{_plural(len(reels), 'reel editado listo', 'reels editados listos')} en Material.")
    elif grab and grab.estado in ("nueva", "procesando"):
        r["reels"] = ("pendiente", "Editando los reels con el estilo del cliente (tarda unos minutos por reel).")
    return r


def avance(f: date) -> dict:
    from agentes import fechas
    manual = {a.paso: a for a in AvancePaso.query.filter_by(fecha=f).all()}
    auto = _automatico(f)
    pasos, actual = [], None
    for paso in PASOS_EVENTO:
        if paso in manual:
            a = manual[paso]
            item = {"estado": a.estado, "manual": True, "detalle": a.nota,
                    "quien": a.usuario.nombre if a.usuario else None, "cuando": a.creado.isoformat() + "Z"}
        elif paso in auto:
            estado, detalle = auto[paso]
            item = {"estado": estado, "manual": False, "detalle": detalle}
        else:
            item = {"estado": "pendiente", "manual": False, "detalle": None}
        item.update(id=paso, como=COMO[paso])
        if item["estado"] == "pendiente" and actual is None:
            actual = paso
        pasos.append(item)
    hechos = sum(1 for p in pasos if p["estado"] != "pendiente")
    tema = db.session.get(Tema, f)
    return {"fecha": f.isoformat(), "nombre": fechas.nombre_fecha(f), "tema": tema.titulo if tema else None,
            "pasos": pasos, "actual": actual, "hechos": hechos, "total": len(pasos), "completo": actual is None}


def _tuvo_actividad(f: date) -> bool:
    return any(m.query.filter_by(**{campo: f}).first() is not None for m, campo in (
        (Tema, "fecha"), (Grabacion, "fecha_evento"), (Paquete, "fecha_evento"), (AvancePaso, "fecha"), (Turno, "fecha")))


def evento_activo() -> date:
    """El evento de hoy (si hoy hay) o el próximo. Los pasados ya no se muestran: quedan en la bitácora."""
    from agentes import fechas
    return fechas.proximos_eventos(fechas.hoy_cdmx(), 7)[0]


def archivar(f: date) -> BitacoraEvento:
    """Guarda (o actualiza) la foto final de un evento pasado para las estadísticas."""
    from .reportes import _registro
    a = avance(f)
    fila = next((r for r in _registro() if r["fecha"] == f.isoformat()), {})
    datos = {k: v for k, v in fila.items() if k not in ("fecha", "tema")}
    datos.setdefault("evento", a["nombre"])
    b = db.session.get(BitacoraEvento, f) or BitacoraEvento(fecha=f)
    b.tema, b.hechos, b.total = a["tema"], a["hechos"], a["total"]
    b.pasos, b.datos = {p["id"]: p["estado"] for p in a["pasos"]}, datos
    db.session.add(b)
    return b


def archivar_pasados() -> int:
    """Pasa a la bitácora los eventos que ya pasaron y se trabajaron. Devuelve cuántos archivó."""
    from agentes import fechas
    hoy = fechas.hoy_cdmx()
    n = 0
    for f in fechas.proximos_eventos(hoy - timedelta(DIAS_ATRAS), DIAS_ATRAS):
        if f >= hoy or db.session.get(BitacoraEvento, f) or not _tuvo_actividad(f):
            continue
        archivar(f)
        n += 1
    db.session.commit()
    return n


@bp.get("/activo")
@login_requerido
def ver_activo():
    return jsonify(avance(evento_activo()))


@bp.get("/<fecha>")
@login_requerido
def ver(fecha: str):
    return jsonify(avance(_fecha(fecha)))


@bp.put("/<fecha>/<paso>")
@login_requerido
def marcar(fecha: str, paso: str):
    f = _fecha(fecha)
    if paso not in PASOS_EVENTO:
        raise ErrorAvance("Paso no válido.")
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        raise ErrorAvance("Datos no válidos.")
    accion = d.get("accion")
    nota = d.get("nota")
    if nota is not None and (not isinstance(nota, str) or len(nota) > 200):
        raise ErrorAvance("La nota debe tener hasta 200 caracteres.")
    existente = db.session.get(AvancePaso, (f, paso))
    if accion == "deshacer":
        if existente:
            db.session.delete(existente)
            db.session.commit()
        return jsonify(avance(f))
    if accion not in ("hecho", "omitir"):
        raise ErrorAvance("Acción no válida.")
    actual = avance(f)["actual"]
    if paso != actual:
        raise ErrorAvance("Primero termina el paso en el que vas; así no se brinca ninguno.", 409)
    estado = "hecho" if accion == "hecho" else "omitido"
    a = existente or AvancePaso(fecha=f, paso=paso)
    a.estado, a.nota, a.usuario_id = estado, (nota or "").strip() or None, g.usuario.id
    db.session.add(a)
    db.session.commit()
    current_app.logger.info("Paso %s del %s marcado %s por %s", paso, f, estado, g.usuario.usuario)
    return jsonify(avance(f))
