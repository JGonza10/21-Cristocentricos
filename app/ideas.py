"""Ideas del equipo: se capturan por escrito o por audio para que nada de lo creativo se pierda.

    GET    /api/ideas                 últimas ideas
    POST   /api/ideas                 {"texto": "..."} idea escrita
    POST   /api/ideas/audio           cuerpo = audio grabado en el navegador (Whisper lo pasa a texto)
    PATCH  /api/ideas/<id>            {"texto": "..."}
    DELETE /api/ideas/<id>
    POST   /api/ideas/<id>/usar       {"fecha": "AAAA-MM-DD"} la vuelve el tema (o nota) de ese evento
    GET    /api/ideas/<id>/audio      el audio original
"""
import uuid
from datetime import date
from pathlib import Path

from flask import Blueprint, abort, current_app, g, jsonify, request, send_file

from .extensiones import db
from .modelos import Idea, Tema, ahora
from .seguridad import login_requerido

bp = Blueprint("ideas", __name__, url_prefix="/api/ideas")

TEXTO_MAX = 4000
AUDIO_MAX = 25 * 1024 * 1024        # ~25 min de voz en opus
TIPOS_AUDIO = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/mp4": ".m4a", "audio/mpeg": ".mp3",
               "audio/wav": ".wav", "audio/x-wav": ".wav"}


class ErrorIdea(Exception):
    pass


@bp.errorhandler(ErrorIdea)
def _error(e: ErrorIdea):
    return jsonify(error=str(e)), 400


def _carpeta() -> Path:
    d = Path(current_app.config["IDEAS_DIR"])
    d.mkdir(parents=True, exist_ok=True)
    return d


def _texto(d) -> str:
    texto = d.get("texto") if isinstance(d, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        raise ErrorIdea("Escribe la idea.")
    texto = texto.replace("\r\n", "\n").strip()
    if len(texto) > TEXTO_MAX:
        raise ErrorIdea(f"La idea es muy larga (máximo {TEXTO_MAX} caracteres).")
    return texto


def _idea(iid: int) -> Idea:
    i = db.session.get(Idea, iid)
    if i is None:
        abort(404)
    return i


@bp.get("")
@login_requerido
def listar():
    ideas = Idea.query.order_by(Idea.creado.desc()).limit(200).all()
    return jsonify(ideas=[i.a_dict() for i in ideas])


@bp.post("")
@login_requerido
def crear():
    i = Idea(texto=_texto(request.get_json(silent=True)), usuario_id=g.usuario.id)
    db.session.add(i)
    db.session.commit()
    return jsonify(idea=i.a_dict()), 201


@bp.post("/audio")
@login_requerido
def crear_audio():
    request.max_content_length = AUDIO_MAX
    tipo = (request.mimetype or "").split(";")[0]
    if tipo not in TIPOS_AUDIO:
        return jsonify(error="Formato de audio no válido."), 400
    datos = request.get_data(cache=False)
    if len(datos) < 1000:
        return jsonify(error="La grabación quedó vacía. Intenta de nuevo."), 400
    nombre = f"{uuid.uuid4().hex}{TIPOS_AUDIO[tipo]}"
    (_carpeta() / nombre).write_bytes(datos)
    i = Idea(texto="", audio=nombre, estado="transcribiendo", usuario_id=g.usuario.id)
    db.session.add(i)
    db.session.commit()
    return jsonify(idea=i.a_dict()), 201


@bp.patch("/<int:iid>")
@login_requerido
def editar(iid: int):
    i = _idea(iid)
    i.texto = _texto(request.get_json(silent=True))
    if i.estado == "error":
        i.estado = "lista"
    db.session.commit()
    return jsonify(idea=i.a_dict())


@bp.delete("/<int:iid>")
@login_requerido
def borrar(iid: int):
    i = _idea(iid)
    if i.audio:
        (_carpeta() / i.audio).unlink(missing_ok=True)
    db.session.delete(i)
    db.session.commit()
    return jsonify(ok=True)


@bp.post("/<int:iid>/usar")
@login_requerido
def usar(iid: int):
    from .temas import _fecha
    i = _idea(iid)
    if not i.texto.strip():
        return jsonify(error="La idea todavía no tiene texto."), 409
    d = request.get_json(silent=True) or {}
    try:
        f = _fecha(d.get("fecha", ""))
    except Exception as e:  # noqa: BLE001 — ErrorTema trae el mensaje
        return jsonify(error=getattr(e, "mensaje", "Fecha no válida.")), 400
    t = db.session.get(Tema, f)
    if t is None:
        primera = i.texto.strip().split("\n")[0]
        titulo = primera if len(primera) <= 120 else primera[:117].rsplit(" ", 1)[0] + "…"
        t = Tema(fecha=f, titulo=titulo, notas=i.texto, aviso_pendiente=True,
                 actualizado=ahora(), actualizado_por_id=g.usuario.id)
        db.session.add(t)
    else:
        t.notas = (t.notas + "\n\n" if t.notas else "") + f"Idea: {i.texto}"
        t.actualizado, t.actualizado_por_id = ahora(), g.usuario.id
    i.estado, i.fecha_evento = "usada", f
    db.session.commit()
    return jsonify(idea=i.a_dict(), tema=t.a_dict())


@bp.get("/<int:iid>/audio")
@login_requerido
def audio(iid: int):
    i = _idea(iid)
    if not i.audio or not (_carpeta() / i.audio).exists():
        abort(404)
    return send_file(_carpeta() / i.audio, conditional=True)
