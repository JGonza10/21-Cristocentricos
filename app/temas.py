"""Tema de cada evento: tema, guion, intenciones y revisión técnica. /api/temas/...

    GET /api/temas?desde=AAAA-MM-DD&hasta=AAAA-MM-DD   temas del rango (para el calendario)
    GET /api/temas/<fecha>                             tema de un evento (o null)
    PUT /api/temas/<fecha>                             guarda {titulo, descripcion, cita, guion, intenciones, notas}
    PUT /api/temas/<fecha>/checklist                   {"id": "audio", "hecho": true}
    GET /api/temas/<fecha>/instrucciones               texto listo para pegarlo en Claude (guion)
    POST /api/temas/<fecha>/difusion                   arma ya la difusión (carrusel + reel promocional)

Al guardar un tema nuevo o cambiar su título se avisa al equipo (correo y Google Calendar) desde el worker.
"""
from datetime import date, timedelta

from flask import Blueprint, current_app, g, jsonify, request

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
    t = tema_de(_fecha(fecha))
    return jsonify(tema=t.a_dict() if t else None)


@bp.put("/<fecha>")
@login_requerido
def guardar(fecha: str):
    f = _fecha(fecha)
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        raise ErrorTema("La solicitud no es válida.")
    titulo = _texto(d, "titulo", obligatorio=True)
    t = tema_de(f)
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
    return jsonify(tema=t.a_dict())


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
    partes.append(
        "Quiero el guion en bloques con minutos aproximados: bienvenida, oración inicial, desarrollo del tema "
        "(con la lectura o cita), momento de intenciones, reflexión práctica para la vida diaria, oración final "
        "y despedida invitando al siguiente evento y a seguir las redes. Tono cálido, sencillo y cercano. "
        "Al final dame 3 frases cortas de alto impacto que podamos usar en reels y carruseles.")
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
