"""Modo ejemplo: siembra eventos completos y el botón avanza el evento demo hasta el final."""
from datetime import date, datetime

import pytest

from agentes import fechas
from app import create_app
from app.extensiones import db
from app.modelos import Usuario
from app.seguridad import hashear

from .conftest import PASSWORD, enviar, login

AHORA = datetime(2026, 10, 17, 9, 0, tzinfo=fechas.CDMX)  # sábado: el viernes 16 es el demo


@pytest.fixture(autouse=True)
def reloj_fijo(monkeypatch):
    monkeypatch.setattr(fechas, "hoy_cdmx", lambda: AHORA.date())
    monkeypatch.setattr(fechas, "ahora_cdmx", lambda: AHORA)


@pytest.fixture
def app_ejemplo(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "x", "SQLALCHEMY_DATABASE_URI": "sqlite://",
                      "SESSION_COOKIE_SECURE": False, "BCRYPT_ROUNDS": 4, "TAILSCALE": False, "EJEMPLO": True,
                      "LOG_DIR": tmp_path / "logs", "FRONTEND_DIST": tmp_path / "sin"})
    from app import ejemplo
    with app.app_context():
        db.session.add(Usuario(usuario="gonza", nombre="Gonza", hash_password=hashear(PASSWORD)))
        db.session.commit()
        assert ejemplo.sembrar() == date(2026, 10, 16)
    return app


def test_la_app_real_no_tiene_modo_ejemplo(cliente):
    login(cliente)
    assert cliente.get("/api/ejemplo").status_code == 404
    assert cliente.get("/api/estado").get_json()["ejemplo"] is False


def test_ejemplo_completo_paso_a_paso(app_ejemplo):
    c = app_ejemplo.test_client()
    login(c)
    assert c.get("/api/estado").get_json()["ejemplo"] is True
    activo = c.get("/api/avance/activo").get_json()
    assert activo["fecha"] == "2026-10-16" and activo["actual"] == "turnos"   # los anteriores ya están completos
    assert c.get("/api/avance/2026-10-12").get_json()["completo"]
    assert c.get("/api/reportes").get_json()["reportes"]

    vistos = []
    for _ in range(12):
        d = enviar(c, "/api/ejemplo/avanzar", {"fecha": "2026-10-16"}).get_json()
        vistos.append(d["mensaje"])
        if d["avance"]["completo"]:
            break
    assert d["avance"]["completo"] and d["avance"]["hechos"] == 11
    assert "ya completó" in enviar(c, "/api/ejemplo/avanzar", {"fecha": "2026-10-16"}).get_json()["mensaje"]

    r = enviar(c, "/api/ejemplo/reiniciar").get_json()
    assert r["fecha"] == "2026-10-16"
    assert c.get("/api/avance/activo").get_json()["actual"] == "turnos"
