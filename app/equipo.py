"""Equipo y turnos: /api/equipo/... y /api/turnos/...

Los integrantes no tienen cuenta: solo nombre y correo para mandarles la invitación.
Antes de guardar a alguien hay que confirmar que se le informó el aviso de privacidad
(LFPDPPP). Al darlo de baja se borra su correo (derecho de cancelación).
"""
import re
from datetime import date, timedelta

from flask import Blueprint, abort, current_app, g, jsonify, request

from .extensiones import db
from .modelos import EventoCalendario, Integrante, Turno, ahora
from .seguridad import login_requerido

bp = Blueprint("equipo", __name__, url_prefix="/api")

PATRON_CORREO = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,100}\.[^@\s.]{2,}$")
MAX_APOYOS = 3
MAX_DIAS_CONSULTA = 62


class ErrorEquipo(Exception):
    def __init__(self, mensaje: str, codigo: int = 400):
        super().__init__(mensaje)
        self.mensaje, self.codigo = mensaje, codigo


@bp.errorhandler(ErrorEquipo)
def _error(e: ErrorEquipo):
    return jsonify(error=e.mensaje), e.codigo


def _datos() -> dict:
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        raise ErrorEquipo("La solicitud no es válida.")
    return d


def _nombre(valor) -> str:
    if not isinstance(valor, str) or not 2 <= len(valor.strip()) <= 80:
        raise ErrorEquipo("Escribe un nombre de 2 a 80 caracteres.")
    return " ".join(valor.split())


def _correo(valor) -> str:
    if not isinstance(valor, str):
        raise ErrorEquipo("Escribe un correo válido.")
    valor = valor.strip().lower()
    if len(valor) > 120 or not PATRON_CORREO.match(valor):
        raise ErrorEquipo("Escribe un correo válido, por ejemplo nombre@gmail.com.")
    return valor


def _booleano(valor, campo: str) -> bool:
    if not isinstance(valor, bool):
        raise ErrorEquipo(f"El campo {campo} no es válido.")
    return valor


def _fecha(texto) -> date:
    try:
        return date.fromisoformat(texto)
    except (TypeError, ValueError):
        raise ErrorEquipo("Fecha no válida.") from None


def _correo_libre(correo: str, excepto: int | None = None) -> None:
    q = Integrante.query.filter(Integrante.correo == correo)
    if excepto:
        q = q.filter(Integrante.id != excepto)
    if q.first():
        raise ErrorEquipo("Ya hay alguien del equipo con ese correo.")


# --- Integrantes --------------------------------------------------------------------

@bp.get("/equipo")
@login_requerido
def listar():
    gente = Integrante.query.filter(Integrante.correo.isnot(None)).order_by(
        Integrante.activo.desc(), Integrante.nombre).all()
    return jsonify(integrantes=[i.a_dict() for i in gente])


@bp.post("/equipo")
@login_requerido
def agregar():
    d = _datos()
    if d.get("aviso") is not True:
        raise ErrorEquipo("Confirma que la persona conoce el aviso de privacidad.")
    correo = _correo(d.get("correo"))
    _correo_libre(correo)
    i = Integrante(nombre=_nombre(d.get("nombre")), correo=correo,
                   puede_dirigir=_booleano(d.get("puede_dirigir", True), "puede dirigir"),
                   aviso_privacidad=ahora())
    db.session.add(i)
    db.session.commit()
    current_app.logger.info("Integrante %s agregado por %s", i.id, g.usuario.usuario)
    return jsonify(integrante=i.a_dict()), 201


@bp.patch("/equipo/<int:iid>")
@login_requerido
def editar(iid: int):
    i = db.session.get(Integrante, iid)
    if i is None or i.correo is None:
        abort(404)
    d = _datos()
    if "nombre" in d:
        i.nombre = _nombre(d["nombre"])
    if "correo" in d:
        correo = _correo(d["correo"])
        _correo_libre(correo, excepto=i.id)
        i.correo = correo
    if "puede_dirigir" in d:
        i.puede_dirigir = _booleano(d["puede_dirigir"], "puede dirigir")
    if "activo" in d:
        i.activo = _booleano(d["activo"], "activo")
        if not i.activo:
            _quitar_turnos_futuros(i)
    db.session.commit()
    return jsonify(integrante=i.a_dict())


def _quitar_turnos_futuros(i: Integrante) -> None:
    from agentes.fechas import hoy_cdmx
    Turno.query.filter(Turno.integrante_id == i.id, Turno.fecha >= hoy_cdmx()).delete()


@bp.delete("/equipo/<int:iid>")
@login_requerido
def baja(iid: int):
    """Da de baja y borra sus datos personales. Sus turnos pasados quedan como 'dado de baja'."""
    i = db.session.get(Integrante, iid)
    if i is None or i.correo is None:
        abort(404)
    _quitar_turnos_futuros(i)
    i.nombre, i.correo, i.activo = "Integrante dado de baja", None, False
    db.session.commit()
    current_app.logger.info("Integrante %s dado de baja por %s", iid, g.usuario.usuario)
    return jsonify(ok=True)


# --- Turnos -------------------------------------------------------------------------

def _resumen(f: date) -> dict:
    from agentes.turnos import turnos_de
    t = turnos_de(f)
    ev = db.session.get(EventoCalendario, f)
    return {
        "dirige": t["dirige"].integrante.a_dict() if t["dirige"] else None,
        "apoyan": [x.integrante.a_dict() for x in t["apoyan"]],
        "automatico": any(x.automatico for x in ([t["dirige"]] if t["dirige"] else []) + t["apoyan"]),
        "invitacion": {"estado": ev.estado, "error": ev.error} if ev else None,
    }


@bp.get("/turnos")
@login_requerido
def ver_turnos():
    from agentes.fechas import es_dia_de_evento, hoy_cdmx
    desde = _fecha(request.args["desde"]) if "desde" in request.args else hoy_cdmx() - timedelta(7)
    hasta = _fecha(request.args["hasta"]) if "hasta" in request.args else desde + timedelta(21)
    if hasta < desde or (hasta - desde).days > MAX_DIAS_CONSULTA:
        raise ErrorEquipo("Rango de fechas no válido.")
    dias = [desde + timedelta(n) for n in range((hasta - desde).days + 1)]
    return jsonify(turnos={f.isoformat(): _resumen(f) for f in dias if es_dia_de_evento(f)})


@bp.put("/turnos/<fecha>")
@login_requerido
def asignar(fecha: str):
    from agentes.fechas import es_dia_de_evento, hoy_cdmx
    f = _fecha(fecha)
    if not es_dia_de_evento(f):
        raise ErrorEquipo("Solo hay evento los lunes y viernes.")
    if f < hoy_cdmx():
        raise ErrorEquipo("Ese evento ya pasó.")
    d = _datos()
    dirige, apoyan = d.get("dirige"), d.get("apoyan", [])
    if dirige is not None and (not isinstance(dirige, int) or isinstance(dirige, bool)):
        raise ErrorEquipo("Elige quién dirige.")
    if not isinstance(apoyan, list) or len(apoyan) > MAX_APOYOS or \
            not all(isinstance(x, int) and not isinstance(x, bool) for x in apoyan):
        raise ErrorEquipo(f"Elige hasta {MAX_APOYOS} personas que apoyan.")
    ids = ([dirige] if dirige is not None else []) + apoyan
    if len(set(ids)) != len(ids):
        raise ErrorEquipo("Una persona no puede tener dos roles el mismo día.")
    gente = {i.id: i for i in Integrante.query.filter(Integrante.id.in_(ids), Integrante.activo.is_(True))}
    if len(gente) != len(ids):
        raise ErrorEquipo("Alguna de las personas elegidas ya no está activa.")
    if dirige is not None and not gente[dirige].puede_dirigir:
        raise ErrorEquipo(f"{gente[dirige].nombre} no está marcado para dirigir.")
    Turno.query.filter_by(fecha=f).delete()
    if dirige is not None:
        db.session.add(Turno(fecha=f, rol="dirige", integrante_id=dirige))
    for x in apoyan:
        db.session.add(Turno(fecha=f, rol="apoya", integrante_id=x))
    db.session.commit()
    current_app.logger.info("Turnos del %s asignados por %s", f, g.usuario.usuario)
    return jsonify(fecha=f.isoformat(), turno=_resumen(f))


@bp.post("/turnos/repartir")
@login_requerido
def repartir_ahora():
    """Llena los huecos de las próximas 2 semanas sin esperar al domingo."""
    from agentes.fechas import hoy_cdmx, proximos_eventos
    from agentes.turnos import repartir
    nuevos = repartir(proximos_eventos(hoy_cdmx(), 14))
    return jsonify(asignados=len(nuevos))
