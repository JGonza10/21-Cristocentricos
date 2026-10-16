from datetime import date

import pytest

from app.bandeja import ErrorBandeja, crear_paquete, paquetes_aprobados
from app.extensiones import db
from app.modelos import Paquete, Usuario
from app.seguridad import hashear

from .conftest import PASSWORD, login, token

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

def test_sin_sesion_no_se_ve_ni_se_aprueba(cliente, paquete):
    assert cliente.get("/api/bandeja").status_code == 401
    assert cliente.get(f"/api/bandeja/{paquete}").status_code == 401
    assert post(cliente, f"/api/bandeja/{paquete}/aprobar", {"version": 1}).status_code == 401
    assert cliente.get(f"/api/bandeja/{paquete}/archivo/1.png").status_code == 401


def test_aprobar_sin_csrf_se_rechaza(sesion, paquete):
    r = sesion.post(f"/api/bandeja/{paquete}/aprobar", json={"version": 1})
    assert r.status_code == 400


# --- Flujo normal -------------------------------------------------------------------

def test_lista_pendientes_y_conteos(sesion, paquete):
    d = sesion.get("/api/bandeja").get_json()
    assert [p["id"] for p in d["paquetes"]] == [paquete]
    assert d["paquetes"][0]["estado"] == "pendiente"
    assert d["conteos"] == {"pendiente": 1, "aprobado": 0, "rechazado": 0}


def test_aprobar_registra_quien_y_lo_entrega_a_publicacion(app, sesion, paquete):
    r = post(sesion, f"/api/bandeja/{paquete}/aprobar", {"version": 1})
    assert r.status_code == 200
    p = r.get_json()["paquete"]
    assert p["estado"] == "aprobado" and p["revisado_por"] == "Gonza" and p["version"] == 2
    assert r.get_json()["conteos"]["aprobado"] == 1
    with app.app_context():
        assert [x.id for x in paquetes_aprobados()] == [paquete]
    historial = sesion.get(f"/api/bandeja/{paquete}").get_json()["historial"]
    assert [h["accion"] for h in historial] == ["creado", "aprobado"]
    assert historial[0]["quien"] == "Agente" and historial[1]["quien"] == "Gonza"


def test_rechazar_con_motivo(app, sesion, paquete):
    r = post(sesion, f"/api/bandeja/{paquete}/rechazar", {"version": 1, "motivo": "  La foto salió borrosa "})
    assert r.status_code == 200
    assert r.get_json()["paquete"]["motivo_rechazo"] == "La foto salió borrosa"
    with app.app_context():
        assert paquetes_aprobados() == []


def test_editar_texto_de_pendiente(sesion, paquete):
    r = post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "texto": "Nuevo texto\r\ncon salto"}, "patch")
    assert r.status_code == 200
    assert r.get_json()["paquete"]["texto"] == "Nuevo texto\ncon salto"
    assert r.get_json()["paquete"]["version"] == 2


def test_reabrir_aprobado_regresa_a_pendiente(app, sesion, paquete):
    post(sesion, f"/api/bandeja/{paquete}/aprobar", {"version": 1})
    r = post(sesion, f"/api/bandeja/{paquete}/reabrir", {"version": 2})
    assert r.status_code == 200
    p = r.get_json()["paquete"]
    assert p["estado"] == "pendiente" and p["revisado_por"] is None
    with app.app_context():
        assert paquetes_aprobados() == []


# --- Reglas que protegen la aprobación ----------------------------------------------

def test_no_se_edita_lo_aprobado(sesion, paquete):
    post(sesion, f"/api/bandeja/{paquete}/aprobar", {"version": 1})
    r = post(sesion, f"/api/bandeja/{paquete}", {"version": 2, "texto": "cambio a escondidas"}, "patch")
    assert r.status_code == 409
    assert "pendiente" in r.get_json()["error"]
    assert r.get_json()["paquete"]["texto"] == "Texto original #SantoRosario"


def test_dos_aprobadores_al_mismo_tiempo(app, sesion, paquete):
    """Gonza aprueba; el aprobador, con la versión vieja en pantalla, intenta rechazar."""
    with app.app_context():
        db.session.add(Usuario(usuario="aprobador", nombre="Aprobador", hash_password=hashear(PASSWORD)))
        db.session.commit()
    otro = app.test_client()
    login(otro, usuario="aprobador")

    assert post(sesion, f"/api/bandeja/{paquete}/aprobar", {"version": 1}).status_code == 200
    r = post(otro, f"/api/bandeja/{paquete}/rechazar", {"version": 1, "motivo": "no"})
    assert r.status_code == 409
    assert "Otra persona" in r.get_json()["error"]
    assert r.get_json()["paquete"]["estado"] == "aprobado"  # se le muestra la versión nueva
    assert version(app, paquete) == 2


def test_aprobar_dos_veces_no_duplica(sesion, paquete):
    post(sesion, f"/api/bandeja/{paquete}/aprobar", {"version": 1})
    assert post(sesion, f"/api/bandeja/{paquete}/aprobar", {"version": 2}).status_code == 409


def test_sin_version_se_rechaza(sesion, paquete):
    for v in (None, "1", True, 1.0):
        assert post(sesion, f"/api/bandeja/{paquete}/aprobar", {"version": v}).status_code == 400


# --- Validación de entradas ---------------------------------------------------------

def test_texto_demasiado_largo(sesion, paquete):
    r = post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "texto": "a" * 2201}, "patch")
    assert r.status_code == 400 and "2200" in r.get_json()["error"]


def test_titulo_vacio_o_de_tipo_incorrecto(sesion, paquete):
    assert post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "titulo": "   "}, "patch").status_code == 400
    assert post(sesion, f"/api/bandeja/{paquete}", {"version": 1, "titulo": ["x"]}, "patch").status_code == 400
    assert post(sesion, f"/api/bandeja/{paquete}", {"version": 1}, "patch").status_code == 400


def test_cuerpo_que_no_es_objeto(sesion, paquete):
    assert post(sesion, f"/api/bandeja/{paquete}/aprobar", [1, 2]).status_code == 400


def test_estado_invalido_y_paquete_inexistente(sesion):
    assert sesion.get("/api/bandeja?estado=publicado' OR 1=1").status_code == 400
    assert sesion.get("/api/bandeja/999").status_code == 404
    assert post(sesion, "/api/bandeja/999/aprobar", {"version": 1}).status_code == 404


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


def test_comando_paquete_demo(app):
    r = app.test_cli_runner().invoke(args=["paquete-demo"])
    assert r.exit_code == 0, r.output
    with app.app_context():
        assert Paquete.query.filter_by(estado="pendiente").count() == 2
