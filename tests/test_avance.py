"""Avance guiado por evento y reporte semanal automático."""
from datetime import date, datetime

import pytest

from agentes import fechas, reporte
from app.bandeja import crear_paquete
from app.extensiones import db
from app.modelos import Grabacion, Integrante, Publicacion, Reporte, Turno

from .conftest import enviar, login

VIERNES = date(2026, 10, 16)
LUNES_SEMANA = date(2026, 10, 12)


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


def test_pasos_automaticos_version_corta(app, cliente):
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
    assert cliente.get("/api/avance/2026-10-17").status_code == 400            # sábado
    assert enviar(cliente, f"/api/avance/{VIERNES}/otro", {"accion": "hecho"}, metodo="put").status_code == 400
    assert enviar(cliente, f"/api/avance/{VIERNES}/turnos", {"accion": "hecho"}, metodo="put").status_code == 400
    assert enviar(cliente, f"/api/avance/{VIERNES}/guion", {"accion": "borrar"}, metodo="put").status_code == 400
    assert enviar(cliente, f"/api/avance/{VIERNES}/guion", {"accion": "hecho", "nota": "x" * 201}, metodo="put").status_code == 400


def test_evento_activo_es_hoy_o_el_proximo_y_los_pasados_van_a_la_bitacora(app, cliente):
    login(cliente)
    with app.app_context():
        db.session.add(Grabacion(nombre="vivo.mkv", fecha_evento=VIERNES, estado="lista"))
        db.session.commit()
    d = cliente.get("/api/avance/activo").get_json()
    assert d["fecha"] == "2026-10-19"           # el viernes ya pasó: aunque se trabajó, ya no es el activo
    with app.app_context():
        from app.avance import archivar_pasados
        assert archivar_pasados() == 1          # solo el viernes (los otros pasados no tuvieron actividad)
        assert archivar_pasados() == 0          # no se repite
    b = cliente.get("/api/bitacora").get_json()["bitacora"]
    assert [x["fecha"] for x in b] == ["2026-10-16"] and b[0]["video"] == "vivo.mkv"
    assert b[0]["total"] == 7 and b[0]["pasos"]["grabacion"] in ("hecho", "pendiente")
    csv = cliente.get("/api/bitacora.csv")
    assert csv.status_code == 200 and "paso_tema" in csv.get_data(as_text=True)


def test_sin_sesion(cliente):
    assert cliente.get("/api/avance/activo").status_code == 401
    assert cliente.get("/api/bitacora.csv").status_code == 401
    assert cliente.get("/api/reportes").status_code == 401


def test_reporte_semanal_con_datos_y_que_mejorar(app, cliente):
    login(cliente)
    with app.app_context():
        ana = Integrante(nombre="Ana", correo="ana@gmail.com")
        db.session.add(ana)
        db.session.commit()
        db.session.add(Turno(fecha=VIERNES, rol="dirige", integrante_id=ana.id))
        reel = crear_paquete("reel", VIERNES, "Reel 1")
        reel.estado = "aprobado"
        db.session.add(Publicacion(paquete_id=reel.id, red="youtube", estado="publicado"))
        db.session.add(Publicacion(paquete_id=reel.id, red="tiktok", estado="error"))
        db.session.commit()
    r = enviar(cliente, "/api/reportes/generar", {"semana": "2026-10-14"})
    datos = r.get_json()["reporte"]
    assert r.status_code == 200 and datos["semana"] == "2026-10-12"            # se ajusta al lunes
    assert datos["totales"]["eventos"] == 2 and datos["totales"]["publicadas"] == 1
    assert datos["equipo"] == {"Ana": {"dirige": 1, "apoya": 0}}
    viernes = next(e for e in datos["eventos"] if e["fecha"] == "2026-10-16")
    assert viernes["dirige"] == "Ana" and viernes["reels"] == 1
    textos = " ".join(datos["mejorar"])
    assert "lunes 12 de octubre no tuvo a nadie" in textos and "TikTok: 1 publicación falló" in textos
    assert "Captura los seguidores" in textos
    # El reporte aparece en la lista (oculto en la versión corta, pero sigue funcionando)
    assert cliente.get("/api/reportes").get_json()["reportes"][0]["semana"] == "2026-10-12"
    assert cliente.get("/api/reportes/2026-10-12").status_code == 200
    assert cliente.get("/api/reportes/2026-10-05").status_code == 404


def test_reporte_no_acepta_semana_futura(cliente):
    login(cliente)
    assert enviar(cliente, "/api/reportes/generar", {"semana": "2026-11-02"}).status_code == 400


def test_seguidores_y_meta(app, cliente):
    login(cliente)
    r = enviar(cliente, "/api/seguidores", {"instagram": 120, "facebook": 380}, metodo="put")
    assert r.status_code == 200 and r.get_json()["seguidores"]["facebook"]["cantidad"] == 380
    assert enviar(cliente, "/api/seguidores", {"instagram": -1}, metodo="put").status_code == 400
    assert enviar(cliente, "/api/seguidores", {"myspace": 3}, metodo="put").status_code == 400
    assert enviar(cliente, "/api/seguidores", {"instagram": True}, metodo="put").status_code == 400
    with app.app_context():
        datos = reporte.generar(date(2026, 10, 17)).datos
    assert datos["seguidores"]["total"] == 500 and datos["seguidores"]["avance_pct"] == 50
    assert any("Faltan 500 seguidores" in m for m in datos["mejorar"])


def test_tarea_semanal_reporta_la_semana_anterior(app, monkeypatch):
    monkeypatch.setattr(fechas, "hoy_cdmx", lambda: date(2026, 10, 19))
    with app.app_context():
        semana = reporte.tarea_semanal()
        assert semana == LUNES_SEMANA and db.session.get(Reporte, LUNES_SEMANA)
