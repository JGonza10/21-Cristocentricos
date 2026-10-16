import pytest

from app import create_app
from app.extensiones import db
from app.modelos import Usuario
from app.seguridad import hashear

PASSWORD = "contraseña-segura-1"


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "solo-para-pruebas",
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SESSION_COOKIE_SECURE": False,
        "BCRYPT_ROUNDS": 4,
        "TAILSCALE": False,  # no depender del .env real; la prueba que lo necesita lo activa
        "LOG_DIR": tmp_path / "logs",
        "FRONTEND_DIST": tmp_path / "sin-frontend",
        "PAQUETES_DIR": tmp_path / "paquetes",
        "GRABACIONES_DIR": tmp_path / "grabaciones",
        "SECRETOS_DIR": tmp_path / "secretos",
    })
    with app.app_context():
        db.session.add(Usuario(usuario="gonza", nombre="Gonza", hash_password=hashear(PASSWORD)))
        db.session.commit()
    yield app


@pytest.fixture
def cliente(app):
    return app.test_client()


def token(cliente):
    return cliente.get("/api/auth/csrf").get_json()["csrf"]


def login(cliente, usuario="gonza", password=PASSWORD):
    return cliente.post("/api/auth/login", json={"usuario": usuario, "password": password},
                        headers={"X-CSRFToken": token(cliente)})


def enviar(cliente, ruta, datos=None, metodo="post"):
    """POST/PATCH/PUT/DELETE con token CSRF."""
    return getattr(cliente, metodo)(ruta, json=datos if datos is not None else {},
                                    headers={"X-CSRFToken": token(cliente)})
