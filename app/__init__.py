"""Fábrica de la aplicación Flask de Cristocéntricos."""
import json
import logging
import os
from datetime import timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, send_from_directory

from . import auth, avance, bandeja, cli, equipo, errores, grabar, ideas, panel, temas
from .migracion import migrar
from .extensiones import csrf, db

RAIZ = Path(__file__).resolve().parent.parent

CSP = (
    "default-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; "
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
        LOG_DIR=RAIZ / "datos" / "logs",
        IDEAS_DIR=RAIZ / "datos" / "ideas",
        CUENTAS_NUEVAS=RAIZ / "datos" / "cuentas_nuevas.json",
        DIFUSION_AL_GUARDAR=os.environ.get("DIFUSION_AL_GUARDAR", "1") == "1",
        ESTILO_DIR=Path(os.environ.get("ESTILO_DIR", RAIZ / "estilo_cliente")),
        # nube = Railway: solo vigila el avance (sin videos ni archivos); local = la laptop que hace todo.
        MODO="nube" if os.environ.get("MODO", "local").strip().lower() == "nube" else "local",
    )
    if config:
        app.config.update(config)
    app.config["EN_NUBE"] = app.config["MODO"] == "nube"
    app.config["SQLALCHEMY_DATABASE_URI"] = url_base_de_datos(app.config["SQLALCHEMY_DATABASE_URI"])
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
        # La laptop llega a la base de Railway por internet: revisar la conexión antes de usarla.
        app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {"pool_pre_ping": True, "pool_recycle": 300})
    if app.config["EN_NUBE"]:
        # Las imágenes las arma la laptop (el worker revisa cada 2 minutos); la nube no guarda archivos.
        app.config["DIFUSION_AL_GUARDAR"] = False
        # Railway pone un proxy delante: así se ve la IP real (bloqueo por intentos) y que es HTTPS.
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
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
    app.register_blueprint(temas.bp)
    app.register_blueprint(ideas.bp)
    app.register_blueprint(grabar.bp)
    errores.registrar(app)
    cli.registrar(app)
    _registrar_frontend(app)

    @app.after_request
    def cabeceras_seguridad(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Content-Security-Policy", CSP)
        resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(self), geolocation=()")
        return resp

    with app.app_context():
        db.create_all()
        for cambio in migrar():
            app.logger.info("Migración: %s", cambio)
        _cuentas_nuevas(app)
    return app


def url_base_de_datos(url: str) -> str:
    """Railway da «postgres://» o «postgresql://»; SQLAlchemy necesita el driver psycopg 3."""
    for prefijo in ("postgres://", "postgresql://"):
        if url.startswith(prefijo):
            return "postgresql+psycopg://" + url[len(prefijo):]
    return url


def _cuentas_nuevas(app: Flask) -> None:
    """Da de alta las cuentas de datos/cuentas_nuevas.json con contraseña temporal y borra el archivo.

    Formato: [{"usuario": "esbeidy", "nombre": "Esbeidy Caro", "password_temporal": "..."}].
    La persona tiene que cambiar la contraseña la primera vez que entra. El archivo vive fuera de git.
    """
    from sqlalchemy.exc import IntegrityError

    from .modelos import Usuario
    from .seguridad import hashear, normalizar_usuario
    ruta = Path(app.config["CUENTAS_NUEVAS"])
    if not ruta.is_file():
        return
    try:
        cuentas = json.loads(ruta.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        app.logger.error("datos/cuentas_nuevas.json no se pudo leer; no se creó ninguna cuenta.")
        return
    for c in cuentas if isinstance(cuentas, list) else []:
        usuario = normalizar_usuario(c.get("usuario"))
        temporal = c.get("password_temporal")
        if not usuario or not isinstance(temporal, str) or len(temporal) < 8:
            app.logger.error("Cuenta nueva no válida en cuentas_nuevas.json: %s", c.get("usuario"))
            continue
        if Usuario.query.filter_by(usuario=usuario).first():
            continue
        if Usuario.query.count() >= app.config["MAX_USUARIOS"]:
            app.logger.error("No se creó %s: ya hay %s cuentas (MAX_USUARIOS).", usuario, app.config["MAX_USUARIOS"])
            continue
        db.session.add(Usuario(usuario=usuario, nombre=str(c.get("nombre") or usuario)[:80],
                               hash_password=hashear(temporal), cambiar_password=True))
        try:
            db.session.commit()
            app.logger.info("Cuenta %s creada con contraseña temporal.", usuario)
        except IntegrityError:              # el servidor y el worker arrancan a la vez
            db.session.rollback()
    ruta.unlink(missing_ok=True)            # no dejar la contraseña temporal en un archivo


def _configurar_log(app: Flask) -> None:
    carpeta = Path(app.config["LOG_DIR"])
    carpeta.mkdir(parents=True, exist_ok=True)
    manejador = RotatingFileHandler(carpeta / "app.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    manejador.setLevel(logging.INFO)
    app.logger.addHandler(manejador)
    if app.config.get("EN_NUBE"):
        consola = logging.StreamHandler()
        consola.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        app.logger.addHandler(consola)
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
