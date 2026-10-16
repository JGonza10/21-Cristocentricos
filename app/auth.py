"""Rutas de inicio y cierre de sesión: /api/auth/..."""
from flask import Blueprint, current_app, g, jsonify, request, session
from flask_wtf.csrf import generate_csrf

from .extensiones import db
from .modelos import Usuario, ahora
from .seguridad import (esta_bloqueado, login_requerido, normalizar_usuario,
                        origen_cliente, registrar_intento, verificar)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

MSG_INCORRECTO = "Usuario o contraseña incorrectos."


@bp.get("/csrf")
def obtener_csrf():
    return jsonify(csrf=generate_csrf())


@bp.post("/login")
def login():
    datos = request.get_json(silent=True) or {}
    texto_usuario = datos.get("usuario")
    password = datos.get("password")
    ip = origen_cliente()

    if not isinstance(password, str) or not isinstance(texto_usuario, str):
        return jsonify(error="Escribe tu usuario y tu contraseña."), 400

    usuario = normalizar_usuario(texto_usuario)
    clave_registro = usuario or "(invalido)"

    if esta_bloqueado(clave_registro, ip):
        current_app.logger.warning("Login bloqueado: usuario=%s ip=%s", clave_registro, ip)
        minutos = current_app.config["LOGIN_VENTANA_MIN"]
        return jsonify(error=f"Demasiados intentos. Espera {minutos} minutos e intenta de nuevo."), 429

    u = Usuario.query.filter_by(usuario=usuario).first() if usuario else None
    ok = verificar(password, u.hash_password if (u and u.activo) else None)
    registrar_intento(clave_registro, ip, ok)

    if not ok:
        current_app.logger.info("Login fallido: usuario=%s ip=%s", clave_registro, ip)
        return jsonify(error=MSG_INCORRECTO), 401

    session.clear()  # evita fijación de sesión
    session["uid"] = u.id
    session.permanent = True
    u.ultimo_acceso = ahora()
    db.session.commit()
    current_app.logger.info("Login correcto: usuario=%s ip=%s", u.usuario, ip)
    return jsonify(usuario=u.a_dict(), csrf=generate_csrf())


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@bp.get("/yo")
@login_requerido
def yo():
    return jsonify(usuario=g.usuario.a_dict())
