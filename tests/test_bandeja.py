from datetime import date

import pytest

from app.bandeja import ErrorBandeja, crear_paquete
from app.extensiones import db
from app.modelos import Paquete

from .conftest import login, token

FECHA = date(2026, 10, 19)


@pytest.fixture
def paquete(app):
    with app.app_context():
        return crear_paquete("carrusel", FECHA, "Invitación lunes 19", "Texto original #SantoRosario",
                             carpeta="2026-10-19/carrusel", archivos=["1.png", "2.png"]).id


@pytest.fixture
def sesion(cliente):
    login(cliente)
    return cliente


def post(c, ruta, datos=None, metodo="post"):
    return getattr(c, metodo)(ruta, json=datos or {}, headers={"X-CSRFToken": token(c)})


def version(app, pid):
    with app.app_context():
        return db.session.get(Paquete, pid).version


# --- Acceso -------------------------------------------------------------------------

def test_sin_sesion_no_se_ve(cliente, paquete):
    assert cliente.get("/api/bandeja").status_code == 401
    assert cliente.get(f"/api/bandeja/{paquete}").status_code == 401
    assert post(cliente, "/api/bandeja/vaciar", {"confirmar": "BORRAR"}).status_code == 401
    assert cliente.get(f"/api/bandeja/{paquete}/archivo/1.png").status_code == 401


def test_lista_y_conteos(sesion, paquete):
    d = sesion.get("/api/bandeja").get_json()
    assert [p["id"] for p in d["paquetes"]] == [paquete]
    assert d["conteos"] == {"total": 1, "carrusel": 1, "reel": 0}
    assert post(sesion, f"/api/bandeja/{paquete}/aprobar", {"version": 1}).status_code in (404, 405)   # ya no se aprueba


def test_editar_texto_de_pendiente(sesion, paquete):
    r = post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "texto": "Nuevo texto\r\ncon salto"}, "patch")
    assert r.status_code == 200
    assert r.get_json()["paquete"]["texto"] == "Nuevo texto\ncon salto"
    assert r.get_json()["paquete"]["version"] == 2


def test_sin_version_se_rechaza(sesion, paquete):
    for v in (None, "1", True, 1.0):
        assert post(sesion, f"/api/bandeja/{paquete}", {"version": v, "texto": "x"}, "patch").status_code == 400


def test_dos_personas_editan_a_la_vez(sesion, paquete):
    assert post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "texto": "Primera"}, "patch").status_code == 200
    r = post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "texto": "Segunda"}, "patch")
    assert r.status_code == 409 and r.get_json()["paquete"]["texto"] == "Primera"


# --- Validación de entradas ---------------------------------------------------------

def test_texto_demasiado_largo(sesion, paquete):
    r = post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "texto": "a" * 2201}, "patch")
    assert r.status_code == 400 and "2200" in r.get_json()["error"]


def test_titulo_vacio_o_de_tipo_incorrecto(sesion, paquete):
    assert post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "titulo": "   "}, "patch").status_code == 400
    assert post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "titulo": ["x"]}, "patch").status_code == 400
    assert post(sesion, f"/api/bandeja/{paquete}", {"version": 1}, "patch").status_code == 400


def test_cuerpo_que_no_es_objeto(sesion, paquete):
    assert post(sesion, f"/api/bandeja/{paquete}", [1, 2], "patch").status_code == 400


def test_pieza_inexistente(sesion):
    assert sesion.get("/api/bandeja?estado=publicado' OR 1=1").status_code == 200   # el filtro ya no existe
    assert sesion.get("/api/bandeja/999").status_code == 404
    assert post(sesion, "/api/bandeja/999", {"version": 1, "texto": "x"}, "patch").status_code == 404


def test_texto_con_html_se_guarda_tal_cual(sesion, paquete):
    """React lo muestra como texto (no lo interpreta), así que no hay que transformarlo."""
    texto = "<script>alert(1)</script>"
    r = post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "texto": texto}, "patch")
    assert r.get_json()["paquete"]["texto"] == texto


def test_crear_paquete_valida_lo_que_mandan_los_agentes(app):
    with app.app_context():
        for kwargs in (
            {"tipo": "video"},
            {"archivos": ["../../.env"]},
            {"archivos": ["sub/1.png"]},
            {"carpeta": "../secretos"},
            {"titulo": ""},
        ):
            base = {"tipo": "reel", "fecha_evento": FECHA, "titulo": "Reel"}
            with pytest.raises(ErrorBandeja):
                crear_paquete(**{**base, **kwargs})
        assert Paquete.query.count() == 0


# --- Archivos de vista previa -------------------------------------------------------

def test_vista_previa_de_archivo(app, sesion, paquete, tmp_path):
    carpeta = tmp_path / "paquetes" / "2026-10-19" / "carrusel"
    carpeta.mkdir(parents=True)
    (carpeta / "1.png").write_bytes(b"\x89PNG imagen")
    (carpeta / "secreto.png").write_bytes(b"no declarado")
    app.config["PAQUETES_DIR"] = tmp_path / "paquetes"

    r = sesion.get(f"/api/bandeja/{paquete}/archivo/1.png")
    assert r.status_code == 200 and r.data == b"\x89PNG imagen"
    assert "no-store" in r.headers["Cache-Control"]
    # Solo los archivos que el paquete declara, y nada fuera de su carpeta
    assert sesion.get(f"/api/bandeja/{paquete}/archivo/secreto.png").status_code == 404
    assert sesion.get(f"/api/bandeja/{paquete}/archivo/..%2F..%2F.env").status_code == 404
    # Declarado pero aún no existe en disco
    assert sesion.get(f"/api/bandeja/{paquete}/archivo/2.png").status_code == 404

