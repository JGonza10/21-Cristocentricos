"""Tema por evento, revisión técnica, instrucciones para Claude, ideas, subida de video y avisos."""
import os
from datetime import date, datetime

import pytest

from agentes import avisos, fechas
from app.extensiones import db
from app.modelos import CHECKLIST, Idea, Integrante, Tema

from .conftest import enviar, login, token

VIERNES = date(2026, 10, 23)


@pytest.fixture(autouse=True)
def reloj_fijo(monkeypatch):
    monkeypatch.setattr(fechas, "hoy_cdmx", lambda: date(2026, 10, 17))
    monkeypatch.setattr(fechas, "ahora_cdmx", lambda: datetime(2026, 10, 17, 9, 0, tzinfo=fechas.CDMX))


def test_guardar_tema_y_verlo_en_el_calendario(app, cliente):
    login(cliente)
    r = enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "  El perdón   que libera ", "descripcion": "Cómo perdonar.",
                                                  "guion": "1. Bienvenida"}, metodo="put")
    t = r.get_json()["tema"]
    assert r.status_code == 200 and t["titulo"] == "El perdón que libera" and t["aviso_pendiente"]
    assert t["actualizado_por"] == "Gonza" and len(t["checklist"]) == len(CHECKLIST)
    lista = cliente.get("/api/temas?desde=2026-10-19&hasta=2026-10-31").get_json()["temas"]
    assert list(lista) == ["2026-10-23"]
    assert cliente.get("/api/temas/2026-10-19").get_json()["tema"] is None
    paso = next(p for p in cliente.get(f"/api/avance/{VIERNES}").get_json()["pasos"] if p["id"] == "tema")
    assert paso["estado"] == "hecho" and "El perdón que libera" in paso["detalle"]


def test_tema_no_valido(cliente):
    login(cliente)
    assert enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "ab"}, metodo="put").status_code == 400
    assert enviar(cliente, "/api/temas/2026-13-01", {"titulo": "Mes 13"}, metodo="put").status_code == 400
    assert enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "x" * 121}, metodo="put").status_code == 400
    assert enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "Bien", "guion": 5}, metodo="put").status_code == 400
    assert cliente.get("/api/temas?desde=2026-01-01&hasta=2026-12-31").status_code == 400


def test_cualquier_dia_puede_tener_evento(app, cliente):
    """Desde el 2026-10-21 el calendario queda abierto: un martes con tema ya es evento."""
    login(cliente)
    martes = "2026-10-20"
    assert cliente.get(f"/api/avance/{martes}").status_code == 400          # sin tema no hay evento
    r = enviar(cliente, f"/api/temas/{martes}", {"titulo": "Evento especial"}, metodo="put")
    assert r.status_code == 200
    d = cliente.get(f"/api/avance/{martes}").get_json()
    assert d["nombre"] == "Martes 20 de octubre" and d["tema"] == "Evento especial" and d["actual"] == "guion"
    temas = cliente.get("/api/estado").get_json()["temas"]
    assert [t["fecha"] for t in temas[:3]] == ["2026-10-19", "2026-10-20", "2026-10-23"]
    assert cliente.get("/api/avance/activo").get_json()["fecha"] == "2026-10-19"
    with app.app_context():
        assert fechas.misterios(date(2026, 10, 20))["tipo"] == "dolorosos"
        assert fechas.misterios(date(2026, 10, 22))["tipo"] == "luminosos"


def test_cambiar_titulo_vuelve_a_avisar(app, cliente):
    login(cliente)
    enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "Primero"}, metodo="put")
    with app.app_context():
        t = db.session.get(Tema, VIERNES)
        t.aviso_pendiente = False
        db.session.commit()
    enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "Primero", "notas": "solo notas"}, metodo="put")
    with app.app_context():
        assert not db.session.get(Tema, VIERNES).aviso_pendiente      # mismo título: no se repite el aviso
    enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "Otro tema"}, metodo="put")
    with app.app_context():
        assert db.session.get(Tema, VIERNES).aviso_pendiente


def test_revision_tecnica(cliente):
    login(cliente)
    assert enviar(cliente, f"/api/temas/{VIERNES}/checklist", {"id": "audio", "hecho": True}, metodo="put").status_code == 409
    enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "Tema"}, metodo="put")
    for k, _ in CHECKLIST[:-1]:
        enviar(cliente, f"/api/temas/{VIERNES}/checklist", {"id": k, "hecho": True}, metodo="put")
    paso = lambda: next(p for p in cliente.get(f"/api/avance/{VIERNES}").get_json()["pasos"] if p["id"] == "revision")
    assert paso()["estado"] == "pendiente" and "Faltan 1" in paso()["detalle"]
    r = enviar(cliente, f"/api/temas/{VIERNES}/checklist", {"id": CHECKLIST[-1][0], "hecho": True}, metodo="put")
    assert all(x["hecho"] for x in r.get_json()["tema"]["checklist"]) and paso()["estado"] == "hecho"
    assert enviar(cliente, f"/api/temas/{VIERNES}/checklist", {"id": "otro", "hecho": True}, metodo="put").status_code == 400


def test_instrucciones_para_claude(cliente):
    login(cliente)
    enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "El perdón", "intenciones": "Por la salud de Doña Mary",
                                              "guion": "Borrador viejo"}, metodo="put")
    texto = cliente.get(f"/api/temas/{VIERNES}/instrucciones").get_json()["texto"]
    assert "Tema: El perdón" in texto and "Viernes 23 de octubre" in texto
    assert "Por la salud de Doña Mary" in texto and "Borrador viejo" in texto and "5 frases cortas" in texto


def test_ideas_escritas_y_usarlas_como_tema(app, cliente):
    login(cliente)
    r = enviar(cliente, "/api/ideas", {"texto": "Hablar del perdón en familia\nCon ejemplos de la vida diaria"})
    iid = r.get_json()["idea"]["id"]
    assert r.status_code == 201 and r.get_json()["idea"]["autor"] == "Gonza"
    assert enviar(cliente, "/api/ideas", {"texto": "  "}).get_json()["error"] == "Escribe la idea."
    r = enviar(cliente, f"/api/ideas/{iid}/usar", {"fecha": str(VIERNES)})
    assert r.status_code == 200 and r.get_json()["tema"]["titulo"] == "Hablar del perdón en familia"
    assert r.get_json()["idea"]["estado"] == "usada"
    otra = enviar(cliente, "/api/ideas", {"texto": "Invitar a un sacerdote"}).get_json()["idea"]["id"]
    t = enviar(cliente, f"/api/ideas/{otra}/usar", {"fecha": str(VIERNES)}).get_json()["tema"]
    assert t["titulo"] == "Hablar del perdón en familia" and "Idea: Invitar a un sacerdote" in t["notas"]
    assert len(cliente.get("/api/ideas").get_json()["ideas"]) == 2
    assert enviar(cliente, f"/api/ideas/{otra}", metodo="delete").status_code == 200


def test_idea_por_audio_se_transcribe(app, cliente, monkeypatch, tmp_path):
    app.config["IDEAS_DIR"] = tmp_path / "ideas"
    login(cliente)
    r = cliente.post("/api/ideas/audio", data=b"x" * 2000, content_type="audio/webm;codecs=opus",
                     headers={"X-CSRFToken": token(cliente)})
    assert r.status_code == 201 and r.get_json()["idea"]["estado"] == "transcribiendo"
    assert cliente.post("/api/ideas/audio", data=b"x" * 2000, content_type="text/plain",
                        headers={"X-CSRFToken": token(cliente)}).status_code == 400
    from agentes import ideas
    monkeypatch.setattr(ideas.whisper, "transcribir", lambda ruta, modelo: [[0, 3, "Hacer un reel"], [3, 5, "del rosario"]])
    with app.app_context():
        assert ideas.tarea() == 1
        assert Idea.query.first().texto == "Hacer un reel del rosario"
    assert cliente.get(f"/api/ideas/{r.get_json()['idea']['id']}/audio").status_code == 200


def test_subir_video_por_partes(app, cliente, tmp_path):
    app.config["GRABACIONES_DIR"] = tmp_path / "grab"
    (tmp_path / "grab").mkdir()
    login(cliente)
    contenido = os.urandom(3000)

    def parte(inicio, datos, nombre="Mi vivo.MP4", fecha="2026-10-16"):
        return cliente.post("/api/grabaciones/subir", data=datos, headers={
            "X-CSRFToken": token(cliente), "X-Archivo": nombre, "X-Inicio": str(inicio),
            "X-Total": str(len(contenido)), "X-Fecha": fecha})

    assert parte(0, contenido[:1000]).get_json() == {"recibido": 1000, "listo": False}
    r = parte(2000, contenido[2000:])                     # se saltó una parte: avisa dónde va
    assert r.status_code == 409 and r.get_json()["recibido"] == 1000
    parte(1000, contenido[1000:2000])
    r = parte(2000, contenido[2000:]).get_json()
    assert r["listo"] and r["nombre"] == "Mi vivo.mp4"
    final = tmp_path / "grab" / "Mi vivo.mp4"
    assert final.read_bytes() == contenido
    momento = datetime.fromtimestamp(final.stat().st_mtime, fechas.CDMX)
    assert fechas.fecha_de_grabacion(momento) == date(2026, 10, 16)     # cuenta para el evento elegido
    assert parte(0, b"x", nombre="virus.exe").status_code == 400
    assert parte(0, b"x", fecha="2026-10-30").status_code == 400          # evento futuro


def test_avisos_del_tema_por_correo(app, monkeypatch):
    enviados = []
    monkeypatch.setattr(avisos.google, "configurado", lambda: True)
    monkeypatch.setattr(avisos.correo, "enviar", lambda para, asunto, texto: enviados.append((para, asunto, texto)))
    with app.app_context():
        db.session.add_all([Integrante(nombre="Ana", correo="ana@gmail.com"),
                            Integrante(nombre="Beto", correo="beto@gmail.com"),
                            Tema(fecha=VIERNES, titulo="El perdón", aviso_pendiente=True),
                            Tema(fecha=date(2026, 10, 9), titulo="Viejo", aviso_pendiente=True)])
        db.session.commit()
        assert avisos.tarea() == 1
        para, asunto, texto = enviados[0]
        assert para == ["ana@gmail.com", "beto@gmail.com"] and asunto == "Tema del viernes 23 de octubre: El perdón"
        assert not db.session.get(Tema, VIERNES).aviso_pendiente
        assert not db.session.get(Tema, date(2026, 10, 9)).aviso_pendiente   # pasado: no se manda
        assert avisos.tarea() == 0


def test_avisos_esperan_a_que_se_conecte_google(app, monkeypatch):
    monkeypatch.setattr(avisos.google, "configurado", lambda: False)
    with app.app_context():
        db.session.add_all([Integrante(nombre="Ana", correo="ana@gmail.com"),
                            Tema(fecha=VIERNES, titulo="El perdón", aviso_pendiente=True)])
        db.session.commit()
        assert avisos.tarea() == 0
        t = db.session.get(Tema, VIERNES)
        assert t.aviso_pendiente and "Google sin conectar" in t.aviso_error


def test_generar_difusion_desde_la_app(app, cliente, monkeypatch):
    login(cliente)
    assert enviar(cliente, f"/api/temas/{VIERNES}/difusion").status_code == 409
    # Al guardar el tema salen solas las 5 imágenes
    r = enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "El perdón"}, metodo="put")
    assert r.get_json()["difusion"] == 1
    assert enviar(cliente, f"/api/temas/{VIERNES}/difusion").get_json()["creados"] == 0
    assert enviar(cliente, f"/api/temas/{VIERNES}/difusion", {"otra": True}).get_json()["creados"] == 1
    # Guardar sin cambiar el título no repite; cambiarlo hace una versión nueva
    assert enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "El perdón", "guion": "x"}, metodo="put").get_json()["difusion"] == 0
    assert enviar(cliente, f"/api/temas/{VIERNES}", {"titulo": "El perdón en familia"}, metodo="put").get_json()["difusion"] == 1
    with app.app_context():
        from app.modelos import Paquete
        assert Paquete.query.filter_by(tipo="reel").count() == 0
        assert Paquete.query.filter_by(tipo="carrusel").count() == 3

