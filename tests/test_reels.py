import os
import shutil
import subprocess
import time
from datetime import date
from pathlib import Path

import pytest

from agentes import reels
from app.extensiones import db
from app.modelos import Grabacion, Paquete
from servicios import ffmpeg

from .conftest import enviar, login

hay_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg no instalado")


def evento_falso(duracion=600, paso=5.0, especiales=None):
    """Segmentos de 5 s con 'Dios te salve' y algunas frases clave en ciertos segundos."""
    especiales = especiales or {}
    segs, t = [], 0.0
    while t < duracion:
        segs.append([t, t + paso, especiales.get(int(t), "Dios te salve María, llena eres de gracia")])
        t += paso
    return segs


# --- Reglas de elección (§2.1) ------------------------------------------------------

def test_elige_3_momentos_sin_traslape_y_con_duracion_correcta():
    segs = evento_falso(especiales={100: "Primer misterio gozoso: la Anunciación",
                                     300: "Pedimos por las intenciones de todos ustedes",
                                     560: "En el nombre del Padre, del Hijo y del Espíritu Santo"})
    momentos = reels.elegir_momentos(segs, [], 600)
    assert len(momentos) == 3
    for m in momentos:
        assert 30 <= m["fin"] - m["inicio"] <= 55
    for a, b in zip(momentos, momentos[1:]):
        assert a["fin"] <= b["inicio"]
    # Empiezan justo en la frase clave y salen etiquetados
    assert [m["inicio"] for m in momentos] == [100, 300, 560]
    assert [reels.etiqueta(m) for m in momentos] == ["Anuncio del primer misterio", "Intenciones",
                                                     "Cierre y bendición"]


def test_anuncio_de_misterio_gana_a_intenciones():
    segs = evento_falso(duracion=300, especiales={50: "Tercer misterio doloroso", 200: "Sus intenciones"})
    mejor = reels.elegir_momentos(segs, [], 300, cuantos=1)[0]
    assert mejor["inicio"] == 50 and mejor["ordinal"] == "tercer"


def test_evita_silencios():
    segs = evento_falso(duracion=300, especiales={50: "Segundo misterio", 200: "Cuarto misterio"})
    silencio_largo = [(55.0, 90.0)]
    mejor = reels.elegir_momentos(segs, silencio_largo, 300, cuantos=1)[0]
    assert mejor["inicio"] == 200


def test_reparte_en_el_evento():
    """Aunque los mejores estén juntos al inicio, toma uno por tercio si puede."""
    segs = evento_falso(duracion=900, especiales={0: "Primer misterio", 60: "Segundo misterio",
                                                   120: "Tercer misterio"})
    momentos = reels.elegir_momentos(segs, [], 900)
    tercios = {int(m["inicio"] // 300) for m in momentos}
    assert tercios == {0, 1, 2}


def test_grabacion_muy_corta_no_da_momentos():
    assert reels.elegir_momentos(evento_falso(duracion=20), [], 20) == []
    assert reels.elegir_momentos([], [], 600) == []


def test_cierre_solo_cuenta_al_final():
    assert reels._clasificar("En el nombre del Padre", 0.1)[0] is None
    assert reels._clasificar("En el nombre del Padre", 0.95)[0] == "cierre"


# --- Subtítulos y silencios ---------------------------------------------------------

def test_srt_con_tiempos_desde_cero_y_dos_renglones():
    segs = [[98.0, 104.0, "Primer misterio gozoso: la Anunciación del ángel Gabriel a la Virgen María"],
            [104.0, 110.0, "Dios te salve"], [200.0, 205.0, "fuera del tramo"]]
    srt = reels.srt_para(segs, 100.0, 140.0)
    bloques = [b for b in srt.strip().split("\n\n") if b]
    assert bloques[0].splitlines()[1].startswith("00:00:00,000 --> ")
    assert all(len(b.splitlines()) <= 4 for b in bloques)      # número, tiempo y máx. 2 renglones
    assert "fuera del tramo" not in srt
    assert "00:00:10,000" in srt                                # 'Dios te salve' termina en el s 10


def test_parsear_silencios():
    salida = ("[silencedetect @ 0x1] silence_start: 12.5\n[silencedetect @ 0x1] silence_end: 15 | "
              "silence_duration: 2.5\n[silencedetect @ 0x1] silence_start: -0.01\n"
              "[silencedetect @ 0x1] silence_end: 3.2 | silence_duration: 3.2\n")
    assert ffmpeg.parsear_silencios(salida) == [(12.5, 15.0), (0.0, 3.2)]


def test_texto_del_reel(app):
    with app.app_context():
        t = reels.texto_reel(date(2026, 10, 23), {"inicio": 0, "fin": 10},
                             [[0, 5, "Cuarto misterio doloroso"], [5, 10, "Jesús con la cruz a cuestas"]])
    assert t.startswith("“Cuarto misterio doloroso Jesús con la cruz a cuestas”")
    assert "Misterios dolorosos" in t and "#MisteriosDolorosos" in t


# --- Carpeta de grabaciones y bandeja -----------------------------------------------

def _envejecer(ruta: Path, segundos=120):
    viejo = time.time() - segundos
    os.utime(ruta, (viejo, viejo))


def test_espera_a_que_termine_de_copiarse(app, monkeypatch):
    llamadas = []
    monkeypatch.setattr(reels, "procesar", lambda g: llamadas.append(g.nombre) or [])
    with app.app_context():
        carpeta = Path(app.config["GRABACIONES_DIR"])
        carpeta.mkdir(parents=True)
        video = carpeta / "evento.mkv"
        video.write_bytes(b"x" * 10)
        (carpeta / "notas.txt").write_text("no es video")
        reels.revisar_carpeta()                     # 1a vuelta: solo se registra
        assert llamadas == [] and Grabacion.query.count() == 1
        video.write_bytes(b"x" * 20)                # sigue creciendo
        _envejecer(video)
        reels.revisar_carpeta()
        assert llamadas == []
        reels.revisar_carpeta()                     # ya no cambió y lleva >60 s quieto
        assert llamadas == ["evento.mkv"]


def test_grabacion_sin_voz_queda_con_error_amable(app, monkeypatch):
    monkeypatch.setattr(reels.ffmpeg, "duracion", lambda r: 600.0)
    monkeypatch.setattr(reels.ffmpeg, "silencios", lambda r: [])
    monkeypatch.setattr(reels.whisper, "transcribir", lambda r, m: [])
    with app.app_context():
        Path(app.config["GRABACIONES_DIR"]).mkdir(parents=True)
        g = Grabacion(nombre="vacio.mp4", fecha_evento=date(2026, 10, 19))
        db.session.add(g)
        db.session.commit()
        assert reels.procesar(g) == []
        g = Grabacion.query.first()
        assert g.estado == "error" and "momentos" in g.error


def test_falla_tecnica_no_expone_detalles(app, monkeypatch):
    def explota(_):
        raise ffmpeg.ErrorFfmpeg("Invalid data found when processing input C:/secreto")
    monkeypatch.setattr(reels.ffmpeg, "duracion", explota)
    with app.app_context():
        Path(app.config["GRABACIONES_DIR"]).mkdir(parents=True)
        g = Grabacion(nombre="roto.mp4", fecha_evento=date(2026, 10, 19))
        db.session.add(g)
        db.session.commit()
        reels.procesar(g)
        g = Grabacion.query.first()
        assert g.estado == "error" and "secreto" not in g.error and "logs" in g.error


@hay_ffmpeg
def test_de_punta_a_punta_con_ffmpeg(app, monkeypatch):
    """Video de prueba de 50 s → 1 reel vertical 1080×1920 con audio, en la bandeja."""
    with app.app_context():
        carpeta = Path(app.config["GRABACIONES_DIR"])
        carpeta.mkdir(parents=True)
        video = carpeta / "evento-lunes.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x180:rate=15",
                        "-f", "lavfi", "-i", "sine=frequency=440", "-t", "50", "-c:v", "libx264", "-preset",
                        "ultrafast", "-c:a", "aac", str(video)], check=True)
        segs = evento_falso(duracion=40, especiales={0: "Primer misterio gozoso, la Anunciación"})
        monkeypatch.setattr(reels.whisper, "transcribir", lambda r, m: segs)
        g = Grabacion(nombre=video.name, fecha_evento=date(2026, 10, 19), tamano=video.stat().st_size)
        db.session.add(g)
        db.session.commit()
        nuevos = reels.procesar(g)
        assert len(nuevos) == 1
        p = nuevos[0]
        assert p.titulo == "Reel 1 · Anuncio del primer misterio" and p.estado == "pendiente"
        salida = Path(app.config["PAQUETES_DIR"]) / p.carpeta / "reel.mp4"
        info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                               "-of", "csv=p=0", str(salida)], capture_output=True, text=True).stdout
        assert "video,1080,1920" in info and "audio" in info
        assert 30 <= ffmpeg.duracion(str(salida)) <= 56
        assert Grabacion.query.first().estado == "lista"


# --- Recorte manual desde la bandeja (§2.1.7) ---------------------------------------

@pytest.fixture
def reel(app):
    with app.app_context():
        g = Grabacion(nombre="r.mp4", fecha_evento=date(2026, 10, 19), duracion=600, segmentos=[])
        db.session.add(g)
        db.session.commit()
        from app.bandeja import crear_paquete
        return crear_paquete("reel", date(2026, 10, 19), "Reel 1", "texto", carpeta="2026-10-19/reel-1-1",
                             archivos=["reel.mp4"], datos={"grabacion_id": g.id, "inicio": 100.0,
                                                           "fin": 145.0, "duracion_fuente": 600.0}).id


def test_recortar_valida_los_tiempos(cliente, reel):
    login(cliente)
    for inicio, fin in ((10, 12), (0, 70), (-1, 30), (590, 640), ("10", 40), (True, 40)):
        r = enviar(cliente, f"/api/bandeja/{reel}/recortar", {"version": 1, "inicio": inicio, "fin": fin})
        assert r.status_code == 400, (inicio, fin)


def test_recortar_y_el_worker_regenera(app, cliente, reel, monkeypatch):
    login(cliente)
    r = enviar(cliente, f"/api/bandeja/{reel}/recortar", {"version": 1, "inicio": 90.5, "fin": 130})
    assert r.status_code == 200
    assert r.get_json()["paquete"]["datos"]["recortar"] == {"inicio": 90.5, "fin": 130}
    hechos = []
    monkeypatch.setattr(reels, "_render", lambda g, a, b, c: hechos.append((a, b, c)))
    with app.app_context():
        (Path(app.config["GRABACIONES_DIR"])).mkdir(parents=True)
        (Path(app.config["GRABACIONES_DIR"]) / "r.mp4").write_bytes(b"video")
        assert reels.aplicar_recortes() == 1
        p = db.session.get(Paquete, reel)
        assert hechos == [(90.5, 130, "2026-10-19/reel-1-1")]
        assert p.datos["inicio"] == 90.5 and "recortar" not in p.datos and p.version == 3
        assert p.historial[-1].accion == "recortado"
        assert reels.aplicar_recortes() == 0


def test_recorte_sin_grabacion_original_avisa(app, cliente, reel):
    login(cliente)
    enviar(cliente, f"/api/bandeja/{reel}/recortar", {"version": 1, "inicio": 90, "fin": 130})
    with app.app_context():
        reels.aplicar_recortes()
        p = db.session.get(Paquete, reel)
        assert "recortar" not in p.datos and "grabación original" in p.datos["error_recorte"]


def test_carrusel_no_se_recorta(app, cliente):
    from app.bandeja import crear_paquete
    with app.app_context():
        pid = crear_paquete("carrusel", date(2026, 10, 19), "C").id
    login(cliente)
    r = enviar(cliente, f"/api/bandeja/{pid}/recortar", {"version": 1, "inicio": 0, "fin": 30})
    assert r.status_code == 400
