from collections import Counter
from datetime import date, timedelta

import pytest

from agentes import fechas, turnos
from app.extensiones import db
from app.modelos import EventoCalendario, Integrante, Turno

from .conftest import enviar, login

HOY = date(2026, 10, 16)            # viernes
LUNES = date(2026, 10, 19)
VIERNES = date(2026, 10, 23)


@pytest.fixture(autouse=True)
def hoy_fijo(monkeypatch):
    monkeypatch.setattr(fechas, "hoy_cdmx", lambda: HOY)


@pytest.fixture
def sesion(cliente):
    login(cliente)
    return cliente


def agregar(c, nombre="Ana López", correo="ana@gmail.com", **extra):
    return enviar(c, "/api/equipo", {"nombre": nombre, "correo": correo, "aviso": True, **extra})


def _gente(app, n=3, dirigen=None):
    with app.app_context():
        ids = []
        for k in range(n):
            i = Integrante(nombre=f"Persona {k}", correo=f"p{k}@correo.mx",
                           puede_dirigir=True if dirigen is None else k in dirigen)
            db.session.add(i)
            db.session.commit()
            ids.append(i.id)
        return ids


# --- Integrantes --------------------------------------------------------------------

def test_todo_requiere_sesion(cliente):
    assert cliente.get("/api/equipo").status_code == 401
    assert cliente.get("/api/turnos").status_code == 401
    assert agregar(cliente).status_code == 401
    assert enviar(cliente, f"/api/turnos/{LUNES}", {"dirige": 1}, "put").status_code == 401
    assert enviar(cliente, "/api/turnos/repartir").status_code == 401
    assert cliente.get("/api/estado").status_code == 401


def test_agregar_requiere_aviso_de_privacidad(sesion):
    r = enviar(sesion, "/api/equipo", {"nombre": "Ana", "correo": "ana@gmail.com"})
    assert r.status_code == 400 and "privacidad" in r.get_json()["error"]
    r = agregar(sesion, correo="  ANA@Gmail.com ")
    assert r.status_code == 201
    i = r.get_json()["integrante"]
    assert i["correo"] == "ana@gmail.com" and i["aviso_privacidad"]


@pytest.mark.parametrize("nombre, correo", [
    ("A", "a@b.mx"), ("Ana", "sin-arroba"), ("Ana", "a@b"), ("Ana", ["x"]), ("x" * 81, "a@b.mx"),
    ("Ana", "a@b.mx' OR 1=1 --"),
])
def test_validaciones(sesion, nombre, correo):
    assert agregar(sesion, nombre=nombre, correo=correo).status_code == 400


def test_correo_repetido(sesion):
    agregar(sesion)
    assert agregar(sesion, nombre="Otra Ana").status_code == 400


def test_editar_y_desactivar(app, sesion):
    iid = agregar(sesion).get_json()["integrante"]["id"]
    r = enviar(sesion, f"/api/equipo/{iid}", {"nombre": "Ana María", "puede_dirigir": False}, "patch")
    assert r.get_json()["integrante"]["nombre"] == "Ana María"
    assert enviar(sesion, f"/api/equipo/{iid}", {"activo": "no"}, "patch").status_code == 400


def test_baja_borra_datos_personales_y_turnos_futuros(app, sesion):
    iid = agregar(sesion).get_json()["integrante"]["id"]
    with app.app_context():
        db.session.add_all([Turno(fecha=date(2026, 10, 9), rol="dirige", integrante_id=iid),
                            Turno(fecha=LUNES, rol="dirige", integrante_id=iid)])
        db.session.commit()
    assert enviar(sesion, f"/api/equipo/{iid}", metodo="delete").status_code == 200
    with app.app_context():
        i = db.session.get(Integrante, iid)
        assert i.correo is None and "baja" in i.nombre and not i.activo
        assert [t.fecha for t in Turno.query.all()] == [date(2026, 10, 9)]   # el pasado se conserva
    assert sesion.get("/api/equipo").get_json()["integrantes"] == []
    assert enviar(sesion, f"/api/equipo/{iid}", metodo="delete").status_code == 404


# --- Asignar turnos a mano ----------------------------------------------------------

def test_asignar_turnos(app, sesion):
    a, b, c = _gente(app)
    r = enviar(sesion, f"/api/turnos/{LUNES}", {"dirige": a, "apoyan": [b, c]}, "put")
    assert r.status_code == 200
    t = r.get_json()["turno"]
    assert t["dirige"]["id"] == a and [x["id"] for x in t["apoyan"]] == [b, c] and not t["automatico"]
    # Cambiar reemplaza lo anterior
    enviar(sesion, f"/api/turnos/{LUNES}", {"dirige": b, "apoyan": []}, "put")
    datos = sesion.get(f"/api/turnos?desde={LUNES}&hasta={VIERNES}").get_json()["turnos"]
    assert datos[str(LUNES)]["dirige"]["id"] == b and datos[str(LUNES)]["apoyan"] == []
    assert datos[str(VIERNES)]["dirige"] is None


@pytest.mark.parametrize("fecha, cuerpo_fn", [
    (date(2026, 10, 20), lambda a, b: {"dirige": a}),                 # martes
    (date(2026, 10, 12), lambda a, b: {"dirige": a}),                 # ya pasó
    (LUNES, lambda a, b: {"dirige": a, "apoyan": [a]}),               # dos roles
    (LUNES, lambda a, b: {"dirige": 9999}),                           # no existe
    (LUNES, lambda a, b: {"dirige": "1"}),
    (LUNES, lambda a, b: {"dirige": a, "apoyan": [b, b + 1, b + 2, b + 3]}),
    (LUNES, lambda a, b: {"dirige": b}),                              # no puede dirigir
])
def test_asignar_valida(app, sesion, fecha, cuerpo_fn):
    a, b = _gente(app, 2, dirigen={0})
    assert enviar(sesion, f"/api/turnos/{fecha}", cuerpo_fn(a, b), "put").status_code == 400


def test_rango_de_consulta(sesion):
    assert sesion.get("/api/turnos?desde=2026-01-01&hasta=2026-12-31").status_code == 400
    assert sesion.get("/api/turnos?desde=ayer").status_code == 400
    assert len(sesion.get("/api/turnos").get_json()["turnos"]) >= 6


# --- Reparto automático -------------------------------------------------------------

def test_reparto_justo(app):
    ids = _gente(app, 3)
    app.config["APOYOS_POR_ROSARIO"] = 1
    dias = fechas.proximos_rosarios(LUNES, 20)        # 6 rosarios
    with app.app_context():
        nuevos = turnos.repartir(dias)
        assert len(nuevos) == 12
        for f in dias:
            t = turnos.turnos_de(f)
            assert t["dirige"] and len(t["apoyan"]) == 1
            assert t["dirige"].integrante_id != t["apoyan"][0].integrante_id
        carga = Counter(t.integrante_id for t in Turno.query.all())
        assert set(carga) == set(ids) and max(carga.values()) - min(carga.values()) <= 1
        dirigen = Counter(t.integrante_id for t in Turno.query.filter_by(rol="dirige"))
        assert max(dirigen.values()) - min(dirigen.values()) <= 1
        assert turnos.repartir(dias) == []           # no cambia lo ya asignado


def test_reparto_respeta_quien_puede_dirigir_y_lo_manual(app):
    a, b, c = _gente(app, 3, dirigen={2})
    with app.app_context():
        db.session.add(Turno(fecha=LUNES, rol="apoya", integrante_id=a))
        db.session.commit()
        turnos.repartir([LUNES, VIERNES])
        assert turnos.turnos_de(LUNES)["dirige"].integrante_id == c
        assert [t.integrante_id for t in turnos.turnos_de(LUNES)["apoyan"]] == [a]
        assert turnos.turnos_de(VIERNES)["dirige"].integrante_id == c


def test_reparto_ignora_inactivos(app):
    a, b = _gente(app, 2)
    with app.app_context():
        db.session.get(Integrante, a).activo = False
        db.session.commit()
        turnos.repartir([LUNES])
        assert {t.integrante_id for t in Turno.query.all()} == {b}


def test_semana_siguiente_desde_el_domingo():
    assert turnos.semana_siguiente(date(2026, 10, 18)) == [LUNES, VIERNES]
    assert turnos.semana_siguiente(date(2026, 10, 19)) == [LUNES + timedelta(7), VIERNES + timedelta(7)]


def test_boton_repartir_ahora(app, sesion):
    _gente(app, 2)
    r = enviar(sesion, "/api/turnos/repartir")
    assert r.status_code == 200 and r.get_json()["asignados"] == 10     # hoy + 4 rosarios × (dirige + apoya)


# --- Invitaciones de Google Calendar ------------------------------------------------

def test_invitaciones_solo_cuando_cambia_el_equipo(app, monkeypatch):
    llamadas = []
    monkeypatch.setattr(turnos.google, "configurado", lambda: True)
    monkeypatch.setattr(turnos.calendario, "sincronizar",
                        lambda f, cal, titulo, desc, correos, gid: llamadas.append((f, correos, gid)) or "ev1")
    a, b = _gente(app, 2)
    with app.app_context():
        db.session.add_all([Turno(fecha=LUNES, rol="dirige", integrante_id=a),
                            Turno(fecha=LUNES, rol="apoya", integrante_id=b)])
        db.session.commit()
        assert turnos.sincronizar_invitaciones() == 1
        assert llamadas == [(LUNES, ["p0@correo.mx", "p1@correo.mx"], None)]
        assert turnos.sincronizar_invitaciones() == 0                  # nada cambió
        Turno.query.filter_by(integrante_id=b).delete()
        db.session.commit()
        assert turnos.sincronizar_invitaciones() == 1
        assert llamadas[-1] == (LUNES, ["p0@correo.mx"], "ev1")        # actualiza el mismo evento
        assert db.session.get(EventoCalendario, LUNES).estado == "enviada"


def test_invitacion_que_falla_se_marca_y_se_reintenta(app, monkeypatch):
    monkeypatch.setattr(turnos.google, "configurado", lambda: True)

    def falla(*a):
        raise RuntimeError("401 invalid_grant")
    monkeypatch.setattr(turnos.calendario, "sincronizar", falla)
    a, = _gente(app, 1)
    with app.app_context():
        db.session.add(Turno(fecha=LUNES, rol="dirige", integrante_id=a))
        db.session.commit()
        turnos.sincronizar_invitaciones()
        ev = db.session.get(EventoCalendario, LUNES)
        assert ev.estado == "error" and "invalid_grant" not in ev.error


def test_sin_google_no_intenta(app, monkeypatch):
    monkeypatch.setattr(turnos.calendario, "sincronizar", lambda *a: pytest.fail("no debía llamar"))
    with app.app_context():
        assert turnos.sincronizar_invitaciones() == 0
