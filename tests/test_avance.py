"""Avance guiado por evento: los 7 pasos."""
from datetime import date, datetime

import pytest

from agentes import fechas
from app.bandeja import crear_paquete
from app.extensiones import db
from app.modelos import Grabacion

from .conftest import enviar, login

VIERNES = date(2026, 10, 16)


@pytest.fixture(autouse=True)
def reloj_fijo(monkeypatch):
    """Sábado 17 de octubre de 2026, 9 am: el viernes 16 ya pasó."""
    monkeypatch.setattr(fechas, "hoy_cdmx", lambda: date(2026, 10, 17))
    monkeypatch.setattr(fechas, "ahora_cdmx", lambda: datetime(2026, 10, 17, 9, 0, tzinfo=fechas.CDMX))


def pasos(d):
    return {p["id"]: p["estado"] for p in d["pasos"]}


def test_evento_nuevo_empieza_en_el_tema(cliente):
    login(cliente)
    d = cliente.get(f"/api/avance/{VIERNES}").get_json()
    assert d["actual"] == "tema" and d["total"] == 7 and d["tema"] is None
    assert [p["id"] for p in d["pasos"]] == ["tema", "guion", "difusion", "revision", "grabacion", "reels", "ideas"]


def test_pasos_automaticos(app, cliente):
    login(cliente)
    with app.app_context():
        from app.modelos import CHECKLIST, Tema
        db.session.add(Tema(fecha=VIERNES, titulo="La misericordia"))
        db.session.commit()
    d = cliente.get(f"/api/avance/{VIERNES}").get_json()
    p = pasos(d)
    assert p["tema"] == "hecho" and p["guion"] == "pendiente" and d["actual"] == "guion"
    assert "Claude" in next(x for x in d["pasos"] if x["id"] == "guion")["detalle"]
    with app.app_context():
        t = db.session.get(Tema, VIERNES)
        t.guion = "Bienvenida…"
        t.checklist = {k: True for k, _ in CHECKLIST}
        crear_paquete("carrusel", VIERNES, "Difusión", archivos=[f"{n}.png" for n in range(1, 6)],
                      datos={"momento": "antes"})
        db.session.add(Grabacion(nombre="celular.mp4", fecha_evento=VIERNES, estado="procesando"))
        db.session.commit()
    d = cliente.get(f"/api/avance/{VIERNES}").get_json()
    p = pasos(d)
    assert p["guion"] == p["difusion"] == p["revision"] == p["grabacion"] == "hecho"
    assert p["reels"] == "pendiente" and d["actual"] == "reels"
    assert "5 imágenes" in next(x for x in d["pasos"] if x["id"] == "difusion")["detalle"]
    with app.app_context():
        for k in range(1, 6):
            crear_paquete("reel", VIERNES, f"Reel {k}", datos={"momento": "despues"})
        db.session.commit()
    d = cliente.get(f"/api/avance/{VIERNES}").get_json()
    assert pasos(d)["reels"] == "hecho" and d["actual"] == "ideas"
    d = enviar(cliente, f"/api/avance/{VIERNES}/ideas", {"accion": "hecho"}, metodo="put").get_json()
    assert d["completo"] and d["hechos"] == 7


def test_no_se_puede_brincar_un_paso(cliente):
    login(cliente)
    r = enviar(cliente, f"/api/avance/{VIERNES}/guion", {"accion": "hecho"}, metodo="put")
    assert r.status_code == 409 and "no se brinca" in r.get_json()["error"]


def test_marcar_omitir_y_deshacer(cliente):
    login(cliente)
    r = enviar(cliente, f"/api/avance/{VIERNES}/tema", {"accion": "omitir", "nota": "Sin tema aún"}, metodo="put")
    d = r.get_json()
    assert r.status_code == 200 and pasos(d)["tema"] == "omitido" and d["actual"] == "guion"
    tema = next(p for p in d["pasos"] if p["id"] == "tema")
    assert tema["manual"] and tema["detalle"] == "Sin tema aún" and tema["quien"] == "Gonza"
    d = enviar(cliente, f"/api/avance/{VIERNES}/guion", {"accion": "omitir"}, metodo="put").get_json()
    assert d["actual"] == "difusion"
    d = enviar(cliente, f"/api/avance/{VIERNES}/tema", {"accion": "deshacer"}, metodo="put").get_json()
    assert d["actual"] == "tema"


def test_datos_no_validos(cliente):
    login(cliente)
    assert cliente.get("/api/avance/2026-10-17").status_code == 400            # sábado sin tema
    assert enviar(cliente, f"/api/avance/{VIERNES}/otro", {"accion": "hecho"}, metodo="put").status_code == 400
    assert enviar(cliente, f"/api/avance/{VIERNES}/turnos", {"accion": "hecho"}, metodo="put").status_code == 400
    assert enviar(cliente, f"/api/avance/{VIERNES}/guion", {"accion": "borrar"}, metodo="put").status_code == 400
    assert enviar(cliente, f"/api/avance/{VIERNES}/guion", {"accion": "hecho", "nota": "x" * 201}, metodo="put").status_code == 400


def test_sin_sesion(cliente):
    assert cliente.get("/api/avance/activo").status_code == 401
    assert cliente.get("/api/bitacora.csv").status_code == 404      # ya no existe (v1.0)
    assert cliente.get("/api/reportes").status_code == 404

