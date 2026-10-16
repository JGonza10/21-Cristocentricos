from datetime import date
from pathlib import Path

import pytest

from agentes import publicacion
from app.bandeja import crear_paquete
from app.extensiones import db
from app.modelos import Paquete, Publicacion
from servicios import meta

from .conftest import enviar, login

FECHA = date(2026, 10, 19)


def _paquete(app, tipo="carrusel", estado="aprobado"):
    with app.app_context():
        carpeta = Path(app.config["PAQUETES_DIR"]) / f"{FECHA}/{tipo}"
        carpeta.mkdir(parents=True, exist_ok=True)
        archivos = ["1.png", "2.png"] if tipo == "carrusel" else ["reel.mp4"]
        for a in archivos:
            (carpeta / a).write_bytes(b"contenido")
        p = crear_paquete(tipo, FECHA, f"{tipo} de prueba", "Texto para redes #SantoRosario",
                          carpeta=f"{FECHA}/{tipo}", archivos=archivos)
        p.estado = estado
        db.session.commit()
        return p.id


def _pubs(app, pid):
    with app.app_context():
        return {x.red: x.a_dict() | {"intentos": x.intentos}
                for x in Publicacion.query.filter_by(paquete_id=pid)}


def test_nunca_publica_sin_aprobacion(app):
    for estado in ("pendiente", "rechazado"):
        pid = _paquete(app, estado=estado)
        with app.app_context():
            publicacion.tarea()
            assert Publicacion.query.filter_by(paquete_id=pid).count() == 0
    assert not (Path(app.config["PAQUETES_DIR"]) / f"{FECHA}/subir_manual").exists()


def test_carrusel_aprobado_queda_listo_para_subir_a_mano(app):
    pid = _paquete(app)
    with app.app_context():
        publicacion.tarea()
    pubs = _pubs(app, pid)
    assert set(pubs) == {"instagram", "facebook", "tiktok"}
    for red, pub in pubs.items():
        assert pub["estado"] == "listo_manual"
        carpeta = Path(app.config["PAQUETES_DIR"]) / pub["ruta"]
        assert pub["ruta"] == f"{FECHA}/subir_manual/{red}/carrusel-{pid}"
        assert sorted(x.name for x in carpeta.iterdir()) == ["1.png", "2.png", "texto.txt"]
        assert "#SantoRosario" in (carpeta / "texto.txt").read_text(encoding="utf-8")
    with app.app_context():
        publicacion.tarea()                 # no repite
    assert _pubs(app, pid) == pubs


def test_reel_sin_google_va_manual_tambien_a_youtube(app):
    pid = _paquete(app, "reel")
    with app.app_context():
        publicacion.tarea()
    pubs = _pubs(app, pid)
    assert pubs["youtube"]["estado"] == "listo_manual"
    texto = (Path(app.config["PAQUETES_DIR"]) / pubs["youtube"]["ruta"] / "texto.txt").read_text(encoding="utf-8")
    assert texto.startswith("TÍTULO:\nreel de prueba · Evento en vivo #Shorts")


def test_reel_sube_a_youtube_en_privado(app, monkeypatch):
    subidas = []
    monkeypatch.setattr(publicacion.google, "configurado", lambda: True)
    monkeypatch.setattr(publicacion.youtube, "subir",
                        lambda ruta, titulo, texto: subidas.append((Path(ruta).name, titulo)) or "https://youtu.be/abc")
    pid = _paquete(app, "reel")
    with app.app_context():
        publicacion.tarea()
        publicacion.tarea()
    pubs = _pubs(app, pid)
    assert pubs["youtube"]["estado"] == "publicado" and pubs["youtube"]["url"] == "https://youtu.be/abc"
    assert subidas == [("reel.mp4", "reel de prueba · Evento en vivo #Shorts")]   # una sola vez


def test_error_de_youtube_reintenta_y_luego_deja_plan_b(app, monkeypatch):
    monkeypatch.setattr(publicacion.google, "configurado", lambda: True)

    def falla(*_):
        raise RuntimeError("quotaExceeded token=SECRETO")
    monkeypatch.setattr(publicacion.youtube, "subir", falla)
    pid = _paquete(app, "reel")
    with app.app_context():
        publicacion.tarea()
        assert _pubs(app, pid)["youtube"]["estado"] == "error"
        publicacion.tarea()
        publicacion.tarea()
        publicacion.tarea()                       # ya no intenta una 4a vez
    yt = _pubs(app, pid)["youtube"]
    assert yt["intentos"] == 3 and "SECRETO" not in yt["error"] and "Reintentar" in yt["error"]
    assert (Path(app.config["PAQUETES_DIR"]) / yt["ruta"] / "reel.mp4").exists()


def test_si_lo_regresan_a_pendientes_no_se_sube(app, monkeypatch):
    monkeypatch.setattr(publicacion.google, "configurado", lambda: True)
    monkeypatch.setattr(publicacion.youtube, "subir", lambda *a: pytest.fail("no debía subir"))
    pid = _paquete(app, "reel")
    with app.app_context():
        viejo = db.session.get(Paquete, pid)
        Paquete.query.filter_by(id=pid).update({"estado": "pendiente"})
        db.session.commit()
        publicacion.publicar_paquete(viejo)      # objeto viejo que aún dice "aprobado"
        assert Publicacion.query.count() == 0


# --- Botones de la bandeja ----------------------------------------------------------

def test_marcar_subido_a_mano(app, cliente):
    pid = _paquete(app)
    with app.app_context():
        publicacion.tarea()
    login(cliente)
    r = enviar(cliente, f"/api/bandeja/{pid}/publicaciones/instagram", {"accion": "subido"})
    assert r.status_code == 200
    estados = {x["red"]: x["estado"] for x in r.get_json()["paquete"]["publicaciones"]}
    assert estados["instagram"] == "publicado" and estados["facebook"] == "listo_manual"
    assert enviar(cliente, f"/api/bandeja/{pid}/publicaciones/instagram", {"accion": "subido"}).status_code == 409
    assert enviar(cliente, f"/api/bandeja/{pid}/publicaciones/myspace", {"accion": "subido"}).status_code == 404


def test_reintentar_un_error(app, cliente):
    pid = _paquete(app, "reel")
    with app.app_context():
        db.session.add(Publicacion(paquete_id=pid, red="youtube", estado="error", intentos=3, error="x"))
        db.session.commit()
    login(cliente)
    assert enviar(cliente, f"/api/bandeja/{pid}/publicaciones/youtube", {"accion": "reintentar"}).status_code == 200
    assert _pubs(app, pid)["youtube"]["intentos"] == 0


def test_publicaciones_requieren_sesion(app, cliente):
    pid = _paquete(app)
    assert enviar(cliente, f"/api/bandeja/{pid}/publicaciones/instagram", {"accion": "subido"}).status_code == 401


def test_no_se_reabre_lo_ya_publicado(app, cliente):
    pid = _paquete(app)
    with app.app_context():
        publicacion.tarea()
    login(cliente)
    enviar(cliente, f"/api/bandeja/{pid}/publicaciones/facebook", {"accion": "subido"})
    with app.app_context():
        version = db.session.get(Paquete, pid).version
    r = enviar(cliente, f"/api/bandeja/{pid}/reabrir", {"version": version})
    assert r.status_code == 409 and "publicó" in r.get_json()["error"]


def test_reabrir_borra_las_carpetas_manuales(app, cliente):
    pid = _paquete(app)
    with app.app_context():
        publicacion.tarea()
        version = db.session.get(Paquete, pid).version
    login(cliente)
    assert enviar(cliente, f"/api/bandeja/{pid}/reabrir", {"version": version}).status_code == 200
    assert _pubs(app, pid) == {}
    assert list((Path(app.config["PAQUETES_DIR"]) / f"{FECHA}/subir_manual").rglob("*.png")) == []


# --- Meta (fase 8) ------------------------------------------------------------------

class Resp:
    def __init__(self, datos, codigo=200):
        self._datos, self.status_code = datos, codigo

    def json(self):
        return self._datos


@pytest.fixture
def meta_activo(app):
    app.config.update(META_AUTO=True, META_TOKEN="token-de-prueba", META_PAGE_ID="111", META_IG_USER_ID="222")


def test_meta_desactivado_por_defecto(app):
    with app.app_context():
        assert not meta.configurado()
        assert not meta.soporta("facebook", "reel")


def test_que_soporta_meta(app, meta_activo):
    with app.app_context():
        assert meta.soporta("facebook", "carrusel") and meta.soporta("facebook", "reel")
        assert meta.soporta("instagram", "reel")
        assert not meta.soporta("instagram", "carrusel")      # requiere URL pública
        assert not meta.soporta("tiktok", "reel")


def test_facebook_carrusel(app, meta_activo, monkeypatch, tmp_path):
    llamadas = []

    def post(url, data=None, files=None, timeout=None, headers=None):
        llamadas.append((url.rsplit("/", 2)[-2:], dict(data or {}), headers))
        return Resp({"id": f"foto{len(llamadas)}"} if "photos" in url else {"id": "111_999"})
    monkeypatch.setattr(meta.requests, "post", post)
    imgs = []
    for n in ("1.png", "2.png"):
        (tmp_path / n).write_bytes(b"png")
        imgs.append(tmp_path / n)
    with app.app_context():
        url = meta.publicar("facebook", "carrusel", imgs, "Hola")
    assert url == "https://www.facebook.com/111_999"
    assert [c[0] for c in llamadas] == [["111", "photos"], ["111", "photos"], ["111", "feed"]]
    assert llamadas[-1][1]["attached_media[1]"] == '{"media_fbid": "foto2"}'
    assert all(c[2]["Authorization"] == "OAuth token-de-prueba" for c in llamadas)
    assert all("token-de-prueba" not in str(c[0]) + str(c[1]) for c in llamadas)   # nunca en URL ni cuerpo


def test_instagram_reel_espera_a_que_procese(app, meta_activo, monkeypatch, tmp_path):
    estados = iter(["IN_PROGRESS", "FINISHED"])
    monkeypatch.setattr(meta.time, "sleep", lambda s: None)

    def post(url, data=None, files=None, timeout=None, headers=None):
        if url.endswith("/media"):
            return Resp({"id": "cont1", "uri": "https://rupload.facebook.com/ig-api-upload/cont1"})
        if "rupload" in url:
            assert headers["Authorization"] == "OAuth token-de-prueba"
            return Resp({"success": True})
        return Resp({"id": "media9"})

    def get(url, params=None, timeout=None, headers=None):
        assert "access_token" not in params
        if params.get("fields") == "status_code":
            return Resp({"status_code": next(estados)})
        return Resp({"permalink": "https://www.instagram.com/reel/xyz/"})
    monkeypatch.setattr(meta.requests, "post", post)
    monkeypatch.setattr(meta.requests, "get", get)
    video = tmp_path / "reel.mp4"
    video.write_bytes(b"mp4")
    with app.app_context():
        assert meta.publicar("instagram", "reel", [video], "Hola") == "https://www.instagram.com/reel/xyz/"


def test_error_de_meta_queda_con_mensaje_amable(app, meta_activo, monkeypatch):
    monkeypatch.setattr(meta.requests, "post",
                        lambda *a, **k: Resp({"error": {"message": "Invalid OAuth access token"}}, 400))
    pid = _paquete(app)
    with app.app_context():
        publicacion.tarea()
    pubs = _pubs(app, pid)
    assert pubs["facebook"]["estado"] == "error" and "OAuth" not in pubs["facebook"]["error"]
    assert pubs["instagram"]["estado"] == "listo_manual"      # carrusel de IG sigue manual
