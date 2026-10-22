"""Equipo: integrantes que reciben por correo el aviso del tema (no tienen cuenta)."""
from datetime import datetime

import pytest

from agentes import avisos, fechas
from app.extensiones import db
from app.modelos import Integrante, Tema

from .conftest import enviar, login


@pytest.fixture
def sesion(cliente):
    login(cliente)
    return cliente


def agregar(c, nombre="Ana López", correo="ana@gmail.com"):
    return enviar(c, "/api/equipo", {"nombre": nombre, "correo": correo})


def test_todo_requiere_sesion(cliente):
    assert cliente.get("/api/equipo").status_code == 401
    assert agregar(cliente).status_code == 401
    assert cliente.get("/api/estado").status_code == 401
    assert cliente.get("/api/turnos").status_code in (401, 404)     # los turnos ya no existen


def test_agregar(sesion):
    r = enviar(sesion, "/api/equipo", {"nombre": "Ana", "correo": "  ANA@Gmail.com "})
    assert r.status_code == 201 and r.get_json()["integrante"]["correo"] == "ana@gmail.com"
    assert [x["nombre"] for x in sesion.get("/api/equipo").get_json()["integrantes"]] == ["Ana"]


@pytest.mark.parametrize("nombre, correo", [("A", "a@b.mx"), ("Ana", "sin-arroba"), ("Ana", "a@b"), ("", ""),
                                            ("x" * 81, "a@b.mx"), ("Ana", "a" * 120 + "@b.mx")])
def test_validaciones(sesion, nombre, correo):
    assert agregar(sesion, nombre, correo).status_code == 400


def test_correo_repetido(sesion):
    agregar(sesion)
    r = agregar(sesion, "Otra Ana", "ANA@gmail.com")
    assert r.status_code == 400 and "Ya hay" in r.get_json()["error"]


def test_editar_pausar_y_borrar(app, sesion):
    iid = agregar(sesion).get_json()["integrante"]["id"]
    r = enviar(sesion, f"/api/equipo/{iid}", {"nombre": "Ana María", "activo": False}, "patch")
    assert r.status_code == 200 and r.get_json()["integrante"]["nombre"] == "Ana María"
    assert r.get_json()["integrante"]["activo"] is False
    assert enviar(sesion, f"/api/equipo/{iid}", {"activo": "no"}, "patch").status_code == 400
    assert enviar(sesion, f"/api/equipo/{iid}", metodo="delete").status_code == 200
    with app.app_context():
        assert db.session.get(Integrante, iid) is None              # sus datos se borran por completo
    assert enviar(sesion, f"/api/equipo/{iid}", metodo="delete").status_code == 404


def test_en_pausa_no_recibe_el_aviso(app, monkeypatch):
    from datetime import date
    enviados = []
    monkeypatch.setattr(avisos.google, "configurado", lambda: True)
    monkeypatch.setattr(avisos.correo, "enviar", lambda para, asunto, cuerpo: enviados.append(para))
    monkeypatch.setattr(fechas, "ahora_cdmx", lambda: datetime(2026, 10, 17, 9, 0, tzinfo=fechas.CDMX))
    with app.app_context():
        db.session.add_all([Integrante(nombre="Ana", correo="ana@gmail.com"),
                            Integrante(nombre="Beto", correo="beto@gmail.com", activo=False),
                            Tema(fecha=date(2026, 10, 23), titulo="El perdón", aviso_pendiente=True)])
        db.session.commit()
        avisos.tarea()
    assert "ana@gmail.com" in str(enviados) and "beto@gmail.com" not in str(enviados)
