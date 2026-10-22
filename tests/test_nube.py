"""Modo nube (Railway): solo vigila el avance; videos, audio y archivos se quedan en la laptop."""
import json
from datetime import date, datetime

import pytest

from agentes import fechas
from app import url_base_de_datos
from app.extensiones import db
from app.modelos import EstadoAgente, Paquete, ahora

from .conftest import enviar, login, token


@pytest.fixture
def nube(app):
    app.config.update(MODO="nube", EN_NUBE=True, DIFUSION_AL_GUARDAR=False)
    return app


@pytest.fixture(autouse=True)
def reloj_fijo(monkeypatch):
    monkeypatch.setattr(fechas, "hoy_cdmx", lambda: date(2026, 10, 17))
    monkeypatch.setattr(fechas, "ahora_cdmx", lambda: datetime(2026, 10, 17, 9, 0, tzinfo=fechas.CDMX))


def test_url_de_railway_usa_psycopg():
    assert url_base_de_datos("postgres://u:p@h:5432/db") == "postgresql+psycopg://u:p@h:5432/db"
    assert url_base_de_datos("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert url_base_de_datos("sqlite:///x.db") == "sqlite:///x.db"


def test_salud_sin_sesion(cliente):
    assert cliente.get("/api/salud").get_json() == {"ok": True}


def test_en_la_nube_se_vigila_pero_no_se_suben_archivos(nube, cliente):
    login(cliente)
    assert cliente.get("/api/auth/yo").get_json()["modo"] == "nube"
    r = enviar(cliente, "/api/temas/2026-10-23", {"titulo": "El perdón"}, metodo="put")
    assert r.status_code == 200 and r.get_json()["difusion"] == 0      # las imágenes las arma la laptop
    assert enviar(cliente, "/api/avance/2026-10-23/guion", {"accion": "omitir"}, metodo="put").status_code == 200
    cabeceras = {"X-CSRFToken": token(cliente)}
    bloqueadas = [
        cliente.post("/api/grabaciones/subir", data=b"x", headers=cabeceras),
        cliente.post("/api/ideas/audio", data=b"x" * 2000, headers={**cabeceras, "Content-Type": "audio/webm"}),
        cliente.post("/api/temas/2026-10-23/imagen", data=b"x", headers={**cabeceras, "Content-Type": "image/png"}),
        cliente.post("/api/temas/2026-10-23/difusion", json={}, headers=cabeceras),
        cliente.post("/api/bandeja/vaciar", json={"confirmar": "BORRAR"}, headers=cabeceras),
    ]
    for r in bloqueadas:
        assert r.status_code == 409 and r.get_json()["solo_laptop"]


def test_material_en_la_nube_no_sirve_archivos(nube, cliente):
    with nube.app_context():
        db.session.add(Paquete(tipo="reel", fecha_evento=date(2026, 10, 19), titulo="Reel 1", carpeta="x",
                               archivos=["reel.mp4"]))
        db.session.commit()
    login(cliente)
    assert len(cliente.get("/api/bandeja").get_json()["paquetes"]) == 1    # se ve que existe
    assert cliente.get("/api/bandeja/1/archivo/reel.mp4").status_code == 409


def test_la_nube_muestra_lo_que_reporto_la_laptop(nube, cliente):
    with nube.app_context():
        reporte = {"estilo": {"referencia": 1, "herramientas": 4, "receta": True}, "google": True}
        db.session.add(EstadoAgente(nombre="laptop", latido=ahora(), mensaje=json.dumps(reporte)))
        db.session.add(EstadoAgente(nombre="worker", latido=ahora()))
        db.session.commit()
    login(cliente)
    e = cliente.get("/api/estado").get_json()
    assert e["modo"] == "nube" and e["google"] is True and e["estilo"]["referencia"] == 1 and e["worker_activo"]


def test_copiar_base(app, tmp_path):
    """La SQLite de la laptop se copia a una base vacía (en Railway, PostgreSQL)."""
    destino = f"sqlite:///{(tmp_path / 'destino.db').as_posix()}"
    runner = app.test_cli_runner()
    r = runner.invoke(args=["copiar-base", "--destino", destino])
    assert r.exit_code == 0 and "usuarios: 1" in r.output
    r = runner.invoke(args=["copiar-base", "--destino", destino])
    assert r.exit_code != 0 and "ya tiene datos" in r.output
