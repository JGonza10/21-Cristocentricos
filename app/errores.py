"""Errores amables para el usuario; el detalle técnico solo va al log."""
from flask import current_app, jsonify, request
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException

MENSAJES = {
    400: "La solicitud no es válida.",
    401: "Inicia sesión para continuar.",
    403: "No tienes permiso para esto.",
    404: "No encontramos lo que buscas.",
    405: "Acción no permitida.",
    413: "El archivo o los datos son demasiado grandes.",
    429: "Demasiados intentos. Espera un momento.",
}


def registrar(app):
    @app.errorhandler(CSRFError)
    def csrf_error(e):
        current_app.logger.warning("CSRF rechazado en %s: %s", request.path, e.description)
        return jsonify(error="Tu sesión expiró. Recarga la página e intenta de nuevo."), 400

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify(error=MENSAJES.get(e.code, "Algo salió mal.")), e.code

    @app.errorhandler(Exception)
    def error_interno(e):
        current_app.logger.exception("Error no controlado en %s", request.path)
        return jsonify(error="Algo salió mal. Intenta de nuevo; si sigue pasando, avísale a Gonza."), 500
