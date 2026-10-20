from app import create_app


def test_cabeceras_de_seguridad(cliente):
    r = cliente.get("/api/auth/csrf")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]


def test_404_amable_en_api(cliente):
    r = cliente.get("/api/no-existe")
    assert r.status_code == 404
    assert r.get_json() == {"error": "No encontramos lo que buscas."}


def test_error_interno_no_expone_detalles(app):
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.get("/api/explota")
    def explota():
        raise RuntimeError("detalle secreto de la base de datos")

    r = app.test_client().get("/api/explota")
    assert r.status_code == 500
    texto = r.get_data(as_text=True)
    assert "secreto" not in texto and "Traceback" not in texto


def test_sin_frontend_compilado_avisa(cliente):
    r = cliente.get("/")
    assert r.status_code == 503


def test_sirve_frontend_compilado(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>hola</h1>", encoding="utf-8")
    app = create_app({"TESTING": True, "SECRET_KEY": "x", "SQLALCHEMY_DATABASE_URI": "sqlite://",
                      "FRONTEND_DIST": dist, "LOG_DIR": tmp_path / "logs"})
    c = app.test_client()
    assert "hola" in c.get("/").get_data(as_text=True)
    assert "hola" in c.get("/calendario").get_data(as_text=True)  # rutas de React


def test_sin_secret_key_no_arranca(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    import pytest
    with pytest.raises(RuntimeError):
        create_app({"SECRET_KEY": None, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
