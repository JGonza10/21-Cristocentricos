"""Fábrica de la aplicación Flask de Cristocéntricos Automático."""
import logging
import os
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, send_from_directory

from . import auth, avance, bandeja, cli, equipo, errores, panel, reportes
from .migracion import migrar
from .extensiones import csrf, db

RAIZ = Path(__file__).resolve().parent.parent

CSP = (
    "default-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data: blob:; "
    "style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
    "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def create_app(config: dict | None = None) -> Flask:
    load_dotenv(RAIZ / ".env")
    app = Flask(__name__, static_folder=None)

    (RAIZ / "datos").mkdir(exist_ok=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", f"sqlite:///{(RAIZ / 'datos' / 'cristocentricos.db').as_posix()}"
        ),
        SESSION_COOKIE_NAME="cristo_sesion",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1") == "1",
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.environ.get("SESION_HORAS", "8"))),
        WTF_CSRF_TIME_LIMIT=None,  # el token vive lo mismo que la sesión
        MAX_CONTENT_LENGTH=1 * 1024 * 1024,
        MAX_USUARIOS=int(os.environ.get("MAX_USUARIOS", "2")),
        TAILSCALE=os.environ.get("TAILSCALE", "0") == "1",
        BCRYPT_ROUNDS=12,
        LOGIN_MAX_FALLOS=5,
        LOGIN_MAX_FALLOS_IP=20,
        LOGIN_VENTANA_MIN=15,
        FRONTEND_DIST=RAIZ / "frontend" / "dist",
        PAQUETES_DIR=RAIZ / "paquetes",
        GRABACIONES_DIR=RAIZ / "grabaciones",
        SECRETOS_DIR=RAIZ / "secretos",
        FUENTES_DIR=RAIZ / "assets" / "fuentes",
        CANAL_NOMBRE=os.environ.get("CANAL_NOMBRE", "Cristocéntricos"),
        CANAL_ENLACE=os.environ.get("CANAL_ENLACE", ""),
        WHISPER_MODELO=os.environ.get("WHISPER_MODELO", "small"),
        APOYOS_POR_EVENTO=int(os.environ.get("APOYOS_POR_EVENTO", "1")),
        META_SEGUIDORES=int(os.environ.get("META_SEGUIDORES", "1000")),
        GOOGLE_CALENDAR_ID=os.environ.get("GOOGLE_CALENDAR_ID", "primary"),
        META_AUTO=os.environ.get("META_AUTO", "0") == "1",
        META_PAGE_ID=os.environ.get("META_PAGE_ID", ""),
        META_IG_USER_ID=os.environ.get("META_IG_USER_ID", ""),
        META_TOKEN=os.environ.get("META_TOKEN", ""),
        META_GRAPH_VERSION=os.environ.get("META_GRAPH_VERSION", "v23.0"),
        LOG_DIR=RAIZ / "datos" / "logs",
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("Falta SECRET_KEY en el archivo .env (copia .env.example y llénalo).")

    _configurar_log(app)
    db.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(bandeja.bp)
    app.register_blueprint(equipo.bp)
    app.register_blueprint(panel.bp)
    app.register_blueprint(avance.bp)
    app.register_blueprint(reportes.bp)
    errores.registrar(app)
    cli.registrar(app)
    _registrar_frontend(app)

    @app.after_request
    def cabeceras_seguridad(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Content-Security-Policy", CSP)
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return resp

    with app.app_context():
        db.create_all()
        for columna in migrar():
            app.logger.info("Migración: se agregó la columna %s", columna)
    return app


def _configurar_log(app: Flask) -> None:
    carpeta = Path(app.config["LOG_DIR"])
    carpeta.mkdir(parents=True, exist_ok=True)
    manejador = RotatingFileHandler(carpeta / "app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    manejador.setLevel(logging.INFO)
    app.logger.addHandler(manejador)
    app.logger.setLevel(logging.INFO)


def _registrar_frontend(app: Flask) -> None:
    """Sirve la app de React compilada (frontend/dist) en todas las rutas que no son /api."""

    @app.get("/", defaults={"ruta": ""})
    @app.get("/<path:ruta>")
    def frontend(ruta):
        if ruta.startswith("api/"):
            abort(404)
        dist = Path(app.config["FRONTEND_DIST"])
        if not (dist / "index.html").exists():
            return jsonify(error="La interfaz no está compilada. Ejecuta: cd frontend; npm run build"), 503
        if ruta == "reloj" and (dist / "reloj.html").is_file():
            return send_from_directory(dist, "reloj.html")  # overlay público, sin datos
        if ruta and (dist / ruta).is_file():
            return send_from_directory(dist, ruta)
        return send_from_directory(dist, "index.html")
