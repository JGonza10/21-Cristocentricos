"""Cuentas nuevas con contraseña temporal (se cambia al entrar) y limpieza de tablas de la v1.0."""
import json
import sqlite3
from datetime import date
from pathlib import Path

from app import create_app
from app.extensiones import db
from app.modelos import Usuario
from app.seguridad import hashear

from .conftest import enviar, token

TEMPORAL = "Cristocéntricos"


def _app_con_cuentas(tmp_path, cuentas, maximo=2):
    archivo = tmp_path / "cuentas_nuevas.json"
    archivo.write_text(json.dumps(cuentas, ensure_ascii=False), encoding="utf-8")
    app = create_app({
        "TESTING": True, "SECRET_KEY": "x", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path / 'c.db'}",
        "SESSION_COOKIE_SECURE": False, "BCRYPT_ROUNDS": 4, "TAILSCALE": False, "LOG_DIR": tmp_path / "logs",
        "FRONTEND_DIST": tmp_path / "sin", "CUENTAS_NUEVAS": archivo, "MAX_USUARIOS": maximo,
        "ESTILO_DIR": tmp_path / "estilo", "PAQUETES_DIR": tmp_path / "paq", "GRABACIONES_DIR": tmp_path / "grab",
    })
    return app, archivo


def test_cuenta_nueva_con_password_temporal(tmp_path):
    app, archivo = _app_con_cuentas(tmp_path, [{"usuario": "Esbeidy", "nombre": "Esbeidy Caro",
                                                "password_temporal": TEMPORAL}])
    assert not archivo.exists()                         # no se queda la contraseña en un archivo
    with app.app_context():
        u = Usuario.query.filter_by(usuario="esbeidy").one()
        assert u.nombre == "Esbeidy Caro" and u.cambiar_password
    c = app.test_client()
    r = c.post("/api/auth/login", json={"usuario": "ESBEIDY", "password": TEMPORAL},
               headers={"X-CSRFToken": token(c)})
    assert r.status_code == 200 and r.get_json()["usuario"]["cambiar_password"] is True
    # Mientras no la cambie, no puede usar nada más
    r = c.get("/api/estado")
    assert r.status_code == 403 and r.get_json()["cambiar_password"] is True
    assert c.get("/api/auth/yo").status_code == 200
    # Cambio de contraseña con validaciones
    assert enviar(c, "/api/auth/cambiar-password", {"actual": "otra", "nueva": "Nueva-clave-2026"}).status_code == 400
    assert enviar(c, "/api/auth/cambiar-password", {"actual": TEMPORAL, "nueva": "corta"}).status_code == 400
    assert enviar(c, "/api/auth/cambiar-password", {"actual": TEMPORAL, "nueva": TEMPORAL}).status_code == 400
    r = enviar(c, "/api/auth/cambiar-password", {"actual": TEMPORAL, "nueva": "Rosario-2026!"})
    assert r.status_code == 200 and r.get_json()["usuario"]["cambiar_password"] is False
    assert c.get("/api/estado").status_code == 200
    # La temporal ya no sirve; la nueva sí
    c2 = app.test_client()
    assert c2.post("/api/auth/login", json={"usuario": "esbeidy", "password": TEMPORAL},
                   headers={"X-CSRFToken": token(c2)}).status_code == 401
    assert c2.post("/api/auth/login", json={"usuario": "esbeidy", "password": "Rosario-2026!"},
                   headers={"X-CSRFToken": token(c2)}).status_code == 200


def test_no_duplica_ni_pasa_el_maximo(tmp_path):
    app, _ = _app_con_cuentas(tmp_path, [{"usuario": "esbeidy", "nombre": "E", "password_temporal": TEMPORAL}],
                              maximo=1)
    with app.app_context():
        assert Usuario.query.count() == 1
    app, _ = _app_con_cuentas(tmp_path, [{"usuario": "esbeidy", "nombre": "E", "password_temporal": TEMPORAL},
                                         {"usuario": "otra", "nombre": "O", "password_temporal": TEMPORAL}],
                              maximo=1)
    with app.app_context():
        assert [u.usuario for u in Usuario.query.all()] == ["esbeidy"]


def test_cuenta_normal_no_pide_cambio(cliente, app):
    with app.app_context():
        db.session.add(Usuario(usuario="beto", nombre="Beto", hash_password=hashear("Clave-segura-9")))
        db.session.commit()
    r = cliente.post("/api/auth/login", json={"usuario": "beto", "password": "Clave-segura-9"},
                     headers={"X-CSRFToken": token(cliente)})
    assert r.get_json()["usuario"]["cambiar_password"] is False
    assert cliente.get("/api/estado").status_code == 200


def test_migracion_borra_tablas_de_la_v1(tmp_path):
    base = tmp_path / "vieja.db"
    con = sqlite3.connect(base)
    for t in ("publicaciones", "turnos", "eventos_calendario", "bitacora_eventos", "reportes", "seguidores"):
        con.execute(f"CREATE TABLE {t} (id INTEGER PRIMARY KEY)")
    con.execute("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, usuario VARCHAR(40) NOT NULL, nombre VARCHAR(80) "
                "NOT NULL, hash_password VARCHAR(100) NOT NULL, activo BOOLEAN NOT NULL, creado DATETIME NOT NULL, "
                "ultimo_acceso DATETIME)")
    con.execute("INSERT INTO usuarios VALUES (1, 'gonza', 'Gonza', 'x', 1, '2026-10-01', NULL)")
    con.commit()
    con.close()
    app = create_app({"TESTING": True, "SECRET_KEY": "x", "SQLALCHEMY_DATABASE_URI": f"sqlite:///{base}",
                      "LOG_DIR": tmp_path / "logs", "CUENTAS_NUEVAS": tmp_path / "no.json"})
    with app.app_context():
        tablas = set(db.inspect(db.engine).get_table_names())
        assert not tablas & {"publicaciones", "turnos", "reportes", "seguidores", "bitacora_eventos"}
        u = db.session.get(Usuario, 1)
        assert u.usuario == "gonza" and not u.cambiar_password       # la columna nueva se agregó sin perder datos


def test_vaciar_material(app, cliente):
    from app.bandeja import crear_paquete
    from app.modelos import Grabacion, Paquete
    from .conftest import login
    login(cliente)
    with app.app_context():
        carpeta = Path(app.config["PAQUETES_DIR"]) / "2026-10-23" / "reel-1-1"
        carpeta.mkdir(parents=True)
        (carpeta / "reel.mp4").write_bytes(b"0")
        crear_paquete("reel", date(2026, 10, 23), "Reel 1", carpeta="2026-10-23/reel-1-1", archivos=["reel.mp4"])
        crear_paquete("carrusel", date(2026, 10, 23), "Difusión")
        grab = Path(app.config["GRABACIONES_DIR"])
        grab.mkdir(parents=True, exist_ok=True)
        (grab / "sigue.mp4").write_bytes(b"0")
        db.session.add(Grabacion(nombre="sigue.mp4", fecha_evento=date(2026, 10, 23), estado="lista"))
        db.session.add(Grabacion(nombre="movida.mp4", fecha_evento=date(2026, 10, 23), estado="lista"))
        db.session.commit()
    assert enviar(cliente, "/api/bandeja/vaciar", {"confirmar": "no"}).status_code == 400
    r = enviar(cliente, "/api/bandeja/vaciar", {"confirmar": "borrar"})
    assert r.status_code == 200 and r.get_json()["paquetes"] == 2 and r.get_json()["grabaciones"] == 1
    with app.app_context():
        assert Paquete.query.count() == 0
        assert [g.nombre for g in Grabacion.query.all()] == ["sigue.mp4"]   # la que sigue en la carpeta se queda
        assert not any(Path(app.config["PAQUETES_DIR"]).iterdir())
