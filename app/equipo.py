"""Equipo: /api/equipo/...

Los integrantes no tienen cuenta: solo nombre y correo para mandarles el aviso del tema.
Se pueden editar, pausar (no reciben correos) o borrar (se borran su nombre y su correo).
"""
import re

from flask import Blueprint, abort, current_app, g, jsonify, request

from .extensiones import db
from .modelos import Integrante
from .seguridad import login_requerido

bp = Blueprint("equipo", __name__, url_prefix="/api")

PATRON_CORREO = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,100}\.[^@\s.]{2,}$")


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
    correo = _correo(d.get("correo"))
    _correo_libre(correo)
    i = Integrante(nombre=_nombre(d.get("nombre")), correo=correo)
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
    if "activo" in d:
        i.activo = _booleano(d["activo"], "activo")
    db.session.commit()
    return jsonify(integrante=i.a_dict())


@bp.delete("/equipo/<int:iid>")
@login_requerido
def baja(iid: int):
    """Borra al integrante con sus datos personales."""
    i = db.session.get(Integrante, iid)
    if i is None or i.correo is None:
        abort(404)
    db.session.delete(i)
    db.session.commit()
    current_app.logger.info("Integrante %s borrado por %s", iid, g.usuario.usuario)
    return jsonify(ok=True)
