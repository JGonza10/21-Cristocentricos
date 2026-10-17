"""Avance guiado de cada evento: los 11 pasos del diagrama de Inicio, en orden.

Cada paso está hecho, omitido (no era necesario) o pendiente. Muchos se comprueban solos con los
datos del sistema; los demás se marcan a mano. El paso actual es el primero pendiente: solo ese se
puede marcar a mano, así no se brinca ninguno.

    GET /api/avance/activo           el evento que toca atender ahora
    GET /api/avance/<fecha>          avance de un evento
    PUT /api/avance/<fecha>/<paso>   {"accion": "hecho" | "omitir" | "deshacer", "nota": "..."}
"""
from datetime import date, timedelta

from flask import Blueprint, current_app, g, jsonify, request

from .extensiones import db
from .modelos import CHECKLIST, PASOS_EVENTO, AvancePaso, Grabacion, Paquete, Reporte, Tema, Turno
from .seguridad import login_requerido

bp = Blueprint("avance", __name__, url_prefix="/api/avance")

DIAS_ATRAS = 10  # un evento sin terminar sigue siendo "el activo" hasta 10 días después

# Cómo se cumple cada paso (lo ve la persona en la tarjeta).
COMO = {
    "tema": "Se marca solo cuando el evento tiene tema y guion guardados en el calendario.",
    "turnos": "Se marca solo cuando el evento tiene quién dirija.",
    "difusion": "Se marca solo cuando el material de difusión del evento ya se revisó en la bandeja.",
    "revision": "Se marca solo cuando palomeas toda la revisión técnica del día.",
    "vivo": "Se marca solo al terminar el horario del evento (11 am).",
    "grabacion": "Se marca solo cuando llega la grabación (OBS o subida desde la app) y se procesa.",
    "reels": "Se marca solo cuando los reels del evento llegan a la bandeja.",
    "carrusel": "Se marca solo cuando el carrusel con escenas del video llega a la bandeja.",
    "bandeja": "Se marca solo cuando ya no queda nada de este evento por revisar.",
    "publicacion": "Se marca solo cuando todo lo aprobado ya se subió o quedó en su carpeta.",
    "redes": "Se marca solo cuando no queda nada por subir a mano ni con error.",
    "registro": "Se marca solo: la app guarda el registro del video cuando termina la publicación.",
    "mides": "Se marca solo cuando el reporte semanal de esa semana ya está hecho (lunes 8 am).",
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
    from agentes import fechas
    r = {}
    tema = db.session.get(Tema, f)
    if tema and tema.guion.strip():
        r["tema"] = ("hecho", f"Tema: {tema.titulo}.")
    elif tema:
        r["tema"] = ("pendiente", f"Tema: {tema.titulo}. Falta el guion.")
    if tema and tema.checklist:
        marcas = tema.checklist
        faltan = [t for k, t in CHECKLIST if not marcas.get(k)]
        r["revision"] = ("hecho", "Revisión técnica completa.") if not faltan else             ("pendiente", f"Faltan {len(faltan)} de {len(CHECKLIST)} puntos de la revisión.")

    dirige = Turno.query.filter_by(fecha=f, rol="dirige").first()
    if dirige:
        r["turnos"] = ("hecho", f"Dirige {dirige.integrante.nombre}.")

    if fechas.ahora_cdmx() >= fechas.fin(f):
        r["vivo"] = ("hecho", "El horario del evento ya terminó.")

    grab = Grabacion.query.filter_by(fecha_evento=f).order_by(Grabacion.id.desc()).first()
    if grab and grab.estado == "lista":
        r["grabacion"] = ("hecho", f"Llegó {grab.nombre}.")
    elif grab:
        r["grabacion"] = ("pendiente", "Procesando la grabación." if grab.estado != "error" else (grab.error or "La grabación falló."))

    todos = Paquete.query.filter_by(fecha_evento=f).all()
    antes = [p for p in todos if momento(p) == "antes"]
    paquetes = [p for p in todos if momento(p) == "despues"]
    if antes:
        pend = [p for p in antes if p.estado == "pendiente"]
        r["difusion"] = ("pendiente", f"{_plural(len(pend), 'pieza de difusión espera', 'piezas de difusión esperan')} tu revisión.")             if pend else ("hecho", f"Difusión revisada: {_plural(sum(p.estado == 'aprobado' for p in antes), 'pieza aprobada', 'piezas aprobadas')}.")

    reels = [p for p in paquetes if p.tipo == "reel"]
    if reels:
        r["reels"] = ("hecho", f"{_plural(len(reels), 'reel llegó', 'reels llegaron')} a la bandeja.")
    if any(p.tipo == "carrusel" for p in paquetes):
        r["carrusel"] = ("hecho", "El carrusel con escenas del video llegó a la bandeja.")

    pendientes = [p for p in paquetes if p.estado == "pendiente"]
    aprobados = [p for p in paquetes if p.estado == "aprobado"]
    if paquetes and not pendientes:
        r["bandeja"] = ("hecho", f"{_plural(len(aprobados), 'aprobado', 'aprobados')}, "
                                 f"{_plural(len(paquetes) - len(aprobados), 'rechazado', 'rechazados')}.")
    elif pendientes:
        r["bandeja"] = ("pendiente", f"{_plural(len(pendientes), 'paquete espera', 'paquetes esperan')} tu revisión.")

    if paquetes and not pendientes and not aprobados:
        r["publicacion"] = ("omitido", "No hubo nada aprobado para publicar.")
        r["redes"] = ("omitido", "No hubo nada aprobado para publicar.")
    elif aprobados:
        pubs = [x for p in aprobados for x in p.publicaciones]
        sin_pub = [p for p in aprobados if not p.publicaciones]
        if not sin_pub and not any(x.estado == "subiendo" for x in pubs):
            r["publicacion"] = ("hecho", f"{_plural(len(pubs), 'publicación preparada', 'publicaciones preparadas')}.")
        else:
            r["publicacion"] = ("pendiente", "El agente de publicación está trabajando.")
        faltan = [x for x in pubs if x.estado in ("listo_manual", "error", "subiendo")]
        if pubs and not sin_pub and not faltan:
            r["redes"] = ("hecho", "Todo quedó publicado.")
        elif faltan:
            manual = sum(1 for x in faltan if x.estado == "listo_manual")
            error = sum(1 for x in faltan if x.estado == "error")
            partes = ([f"{manual} por subir a mano"] if manual else []) + ([f"{error} con error"] if error else [])
            r["redes"] = ("pendiente", ", ".join(partes) + "." if partes else "Subiendo…")
    if r.get("redes", ("",))[0] in ("hecho", "omitido"):
        r["registro"] = ("hecho", "Quedó en el registro de la app (descárgalo desde el reporte).")

    lunes = f - timedelta(f.weekday())
    if db.session.get(Reporte, lunes):
        r["mides"] = ("hecho", "El reporte semanal ya está listo.")
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


def evento_activo() -> date:
    """El evento más antiguo de los últimos días que no ha terminado su proceso; si no hay, el próximo."""
    from agentes import fechas
    hoy = fechas.hoy_cdmx()
    for f in fechas.proximos_eventos(hoy - timedelta(DIAS_ATRAS), DIAS_ATRAS):
        if not avance(f)["completo"]:
            return f
    return fechas.proximos_eventos(hoy + timedelta(1), 7)[0]


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
