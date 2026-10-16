from app.extensiones import db
from app.modelos import Usuario

from .conftest import PASSWORD, login, token


def test_login_correcto_y_quien_soy(cliente):
    r = login(cliente)
    assert r.status_code == 200
    assert r.get_json()["usuario"]["usuario"] == "gonza"
    cookie = r.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie
    assert cliente.get("/api/auth/yo").get_json()["usuario"]["nombre"] == "Gonza"


def test_usuario_con_mayusculas_y_espacios(cliente):
    assert login(cliente, usuario="  GONZA ").status_code == 200


def test_password_incorrecta_y_usuario_inexistente_dan_mismo_mensaje(cliente):
    a = login(cliente, password="otra-cosa-123")
    b = login(cliente, usuario="nadie", password="otra-cosa-123")
    assert a.status_code == b.status_code == 401
    assert a.get_json() == b.get_json()


def test_sin_token_csrf_se_rechaza(cliente):
    r = cliente.post("/api/auth/login", json={"usuario": "gonza", "password": PASSWORD})
    assert r.status_code == 400
    assert "sesión" in r.get_json()["error"].lower()


def test_bloqueo_tras_5_intentos_fallidos(cliente):
    for _ in range(5):
        assert login(cliente, password="mala-password-1").status_code == 401
    # Aun con la contraseña correcta, queda bloqueado temporalmente
    r = login(cliente)
    assert r.status_code == 429


def test_bloqueo_por_ip_aunque_cambie_el_usuario(app, cliente):
    app.config["LOGIN_MAX_FALLOS_IP"] = 3
    for nombre in ("ana", "beto", "carla"):
        login(cliente, usuario=nombre, password="mala-password-1")
    assert login(cliente).status_code == 429


def test_inyeccion_sql_no_entra(cliente):
    r = login(cliente, usuario="' OR 1=1 --", password="' OR '1'='1")
    assert r.status_code == 401


def test_datos_con_tipo_incorrecto(cliente):
    r = cliente.post("/api/auth/login", json={"usuario": ["x"], "password": 123},
                     headers={"X-CSRFToken": token(cliente)})
    assert r.status_code == 400


def test_sin_sesion_no_hay_acceso(cliente):
    assert cliente.get("/api/auth/yo").status_code == 401


def test_logout_cierra_la_sesion(cliente):
    login(cliente)
    r = cliente.post("/api/auth/logout", headers={"X-CSRFToken": token(cliente)})
    assert r.status_code == 200
    assert cliente.get("/api/auth/yo").status_code == 401


def test_usuario_desactivado_pierde_acceso(app, cliente):
    login(cliente)
    with app.app_context():
        Usuario.query.filter_by(usuario="gonza").first().activo = False
        db.session.commit()
    assert cliente.get("/api/auth/yo").status_code == 401
    assert login(cliente).status_code == 401


def test_password_guardada_con_bcrypt(app):
    with app.app_context():
        h = Usuario.query.first().hash_password
    assert h.startswith("$2b$") and PASSWORD not in h


def test_tailscale_bloquea_por_cuenta_y_no_por_ip(app, cliente):
    app.config["TAILSCALE"] = True
    app.config["LOGIN_MAX_FALLOS_IP"] = 3
    # Alguien desde Tailscale falla 3 veces con usuarios distintos...
    for nombre in ("ana", "beto", "carla"):
        cliente.post("/api/auth/login", json={"usuario": nombre, "password": "mala-password-1"},
                     headers={"X-CSRFToken": token(cliente), "Tailscale-User-Login": "intruso@gmail.com"})
    # ...queda bloqueado él,
    r = cliente.post("/api/auth/login", json={"usuario": "gonza", "password": PASSWORD},
                     headers={"X-CSRFToken": token(cliente), "Tailscale-User-Login": "intruso@gmail.com"})
    assert r.status_code == 429
    # pero el aprobador, desde su propia cuenta de Tailscale, sí puede entrar.
    r = cliente.post("/api/auth/login", json={"usuario": "gonza", "password": PASSWORD},
                     headers={"X-CSRFToken": token(cliente), "Tailscale-User-Login": "aprobador@gmail.com"})
    assert r.status_code == 200


def test_sin_tailscale_se_ignora_la_cabecera(app, cliente):
    app.config["LOGIN_MAX_FALLOS_IP"] = 3
    for cuenta in ("a@x.com", "b@x.com", "c@x.com"):
        cliente.post("/api/auth/login", json={"usuario": "otro", "password": "mala-password-1"},
                     headers={"X-CSRFToken": token(cliente), "Tailscale-User-Login": cuenta})
    assert login(cliente).status_code == 429  # cuenta por IP, la cabecera no sirve para evadir


def test_correo_sirve_como_usuario(app, cliente):
    from app.seguridad import hashear, normalizar_usuario
    assert normalizar_usuario(" JuanGonza@Live.com.mx ") == "juangonza@live.com.mx"
    assert normalizar_usuario("a b@x.com") is None
    with app.app_context():
        db.session.add(Usuario(usuario="juangonza@live.com.mx", nombre="Gonza", hash_password=hashear(PASSWORD)))
        db.session.commit()
    assert login(cliente, usuario="juangonza@live.com.mx").status_code == 200
