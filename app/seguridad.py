"""Contraseñas, validaciones y bloqueo por intentos fallidos."""
import re
from datetime import timedelta
from functools import wraps

import bcrypt
from flask import current_app, g, has_app_context, jsonify, request, session
from sqlalchemy import func

from .extensiones import db
from .modelos import IntentoLogin, Usuario, ahora

PATRON_USUARIO = re.compile(r"^[a-z0-9._@+-]{3,40}$")  # acepta correos (usuario dueño)
PASSWORD_MIN = 10
PASSWORD_MAX_BYTES = 72  # límite de bcrypt

# Hash falso: se verifica contra él cuando el usuario no existe, para que la
# respuesta tarde lo mismo y no revele qué usuarios existen.
_HASH_FALSO = bcrypt.hashpw(b"usuario-inexistente", bcrypt.gensalt(rounds=12))


def _rondas() -> int:
    return current_app.config.get("BCRYPT_ROUNDS", 12) if has_app_context() else 12


def hashear(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=_rondas())).decode()


def verificar(password: str, hash_guardado: str | None) -> bool:
    datos = password.encode("utf-8")
    if len(datos) > PASSWORD_MAX_BYTES:
        return False
    try:
        if hash_guardado is None:
            bcrypt.checkpw(datos, _HASH_FALSO)
            return False
        return bcrypt.checkpw(datos, hash_guardado.encode())
    except ValueError:
        return False


def normalizar_usuario(texto) -> str | None:
    if not isinstance(texto, str):
        return None
    texto = texto.strip().lower()
    return texto if PATRON_USUARIO.match(texto) else None


def problema_password(password) -> str | None:
    """Devuelve un mensaje si la contraseña no sirve, o None si está bien."""
    if not isinstance(password, str) or len(password) < PASSWORD_MIN:
        return f"La contraseña debe tener al menos {PASSWORD_MIN} caracteres."
    if len(password.encode("utf-8")) > PASSWORD_MAX_BYTES:
        return "La contraseña es demasiado larga (máximo 72 bytes)."
    if password.isdigit() or password.isalpha():
        return "Usa letras y números (o símbolos) en la contraseña."
    return None


def origen_cliente() -> str:
    """Quién hace la petición, para el bloqueo por equipo.

    Detrás de `tailscale serve` todas las peticiones llegan desde 127.0.0.1, así que
    usamos la cuenta de Tailscale que Serve agrega en la cabecera Tailscale-User-Login.
    Solo se confía en esa cabecera si TAILSCALE=1 (el servidor escucha en 127.0.0.1 y
    únicamente Tailscale puede llegar a él desde fuera).
    """
    ip = request.remote_addr or "desconocida"
    if current_app.config.get("TAILSCALE") and ip == "127.0.0.1":
        cuenta = (request.headers.get("Tailscale-User-Login") or "").strip()[:40]
        if cuenta:
            return f"ts:{cuenta}"
    return ip


def esta_bloqueado(usuario: str, ip: str) -> bool:
    cfg = current_app.config
    desde = ahora() - timedelta(minutes=cfg["LOGIN_VENTANA_MIN"])

    ultimo_ok = (
        db.session.query(func.max(IntentoLogin.fecha))
        .filter(IntentoLogin.usuario == usuario, IntentoLogin.exito.is_(True))
        .scalar()
    )
    inicio = max(desde, ultimo_ok) if ultimo_ok else desde

    fallos_usuario = IntentoLogin.query.filter(
        IntentoLogin.usuario == usuario,
        IntentoLogin.exito.is_(False),
        IntentoLogin.fecha > inicio,
    ).count()
    fallos_ip = IntentoLogin.query.filter(
        IntentoLogin.ip == ip,
        IntentoLogin.exito.is_(False),
        IntentoLogin.fecha > desde,
    ).count()
    return fallos_usuario >= cfg["LOGIN_MAX_FALLOS"] or fallos_ip >= cfg["LOGIN_MAX_FALLOS_IP"]


def registrar_intento(usuario: str, ip: str, exito: bool) -> None:
    db.session.add(IntentoLogin(usuario=usuario[:40], ip=ip[:45], exito=exito))
    db.session.commit()


def usuario_actual() -> Usuario | None:
    uid = session.get("uid")
    if not uid:
        return None
    u = db.session.get(Usuario, uid)
    if u is None or not u.activo:
        session.clear()
        return None
    return u


def solo_en_laptop(vista):
    """Para rutas que manejan videos, audio o archivos pesados: en la nube (MODO=nube) no se hacen.

    Esos archivos viven solo en la laptop (grabaciones/, paquetes/, estilo_cliente/); la nube
    solo vigila el avance. Va debajo de @login_requerido.
    """
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if current_app.config.get("EN_NUBE"):
            return jsonify(error="Esto se hace en la laptop: los videos y archivos no se suben a internet.",
                           solo_laptop=True), 409
        return vista(*args, **kwargs)
    return envoltura


# Lo único que puede hacer quien tiene contraseña temporal: ver quién es, cambiarla o salir.
PERMITIDO_CON_TEMPORAL = {"auth.yo", "auth.cambiar_password", "auth.logout"}


def login_requerido(vista):
    """Decorador para rutas que solo pueden usar usuarios con sesión.

    Con contraseña temporal (cuenta nueva) solo se puede cambiar la contraseña.
    """
    @wraps(vista)
    def envoltura(*args, **kwargs):
        u = usuario_actual()
        if u is None:
            return jsonify(error="Inicia sesión para continuar."), 401
        if u.cambiar_password and request.endpoint not in PERMITIDO_CON_TEMPORAL:
            return jsonify(error="Primero cambia tu contraseña temporal.", cambiar_password=True), 403
        g.usuario = u
        return vista(*args, **kwargs)
    return envoltura
