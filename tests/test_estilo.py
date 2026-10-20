"""Edición de reels con el estilo del cliente (servicios/estilo.py)."""
import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from agentes import reels
from app.extensiones import db
from app.modelos import Grabacion
from servicios import estilo

from .test_reels import evento_falso

hay_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg no está instalado")
FUENTES = Path(__file__).resolve().parent.parent / "assets" / "fuentes"


def _video(ruta: Path, segundos: int = 20, tam: str = "720x1280") -> Path:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"testsrc=size={tam}:rate=15",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", str(segundos), "-c:v", "libx264",
                    "-preset", "ultrafast", "-c:a", "aac", str(ruta)], check=True)
    return ruta


def _probe(ruta: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
                        "-of", "json", str(ruta)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def test_tramo_y_color():
    assert estilo.tramo(0, None, 30) == (0, 30)
    assert estilo.tramo(-3, None, 30) == (27, 30)        # los últimos 3 segundos
    assert estilo.tramo(2, -2, 30) == (2, 28)
    assert estilo.tramo(5, 99, 30) == (5, 30)
    assert estilo.color("#7A1C2E") == (122, 28, 46, 255)
    assert estilo.color("#FFFFFF80") == (255, 255, 255, 128)
    with pytest.raises(estilo.ErrorEstilo):
        estilo.color("vino")


def test_carpeta_y_receta(tmp_path):
    raiz = estilo.preparar_carpeta(tmp_path / "estilo_cliente")
    assert {p.name for p in raiz.iterdir()} == {"referencia", "herramientas", "analisis", "pruebas", "estilo.json"}
    (raiz / "estilo.json").write_text(json.dumps({"mejora": {"nitidez": 0}, "capas": [{"archivo": "logo.png"}]}))
    e = estilo.cargar(raiz)
    assert e["mejora"]["nitidez"] == 0 and e["mejora"]["quitar_ruido"] is True    # se completa con lo de base
    assert e["formato"]["alto"] == 1920 and e["capas"] == [{"archivo": "logo.png"}]
    (raiz / "estilo.json").write_text('{"capas": [}')
    with pytest.raises(estilo.ErrorEstilo, match="renglón 1"):
        estilo.cargar(raiz)


def test_herramienta_no_sale_de_la_carpeta(tmp_path):
    raiz = estilo.preparar_carpeta(tmp_path / "e")
    (tmp_path / "secreto.txt").write_text("x")
    with pytest.raises(estilo.ErrorEstilo, match="dentro de"):
        estilo.herramienta(raiz, "../../secreto.txt")
    with pytest.raises(estilo.ErrorEstilo, match="No encontré"):
        estilo.herramienta(raiz, "no-existe.png")


def test_subtitulos_por_tramo():
    segs = [[10.0, 14.0, "Padre Eterno, te ofrezco el Divino Rostro de Jesús"], [20.0, 22.0, "Fuera"]]
    t = estilo.trozos_subtitulos(segs, 11.0, 18.0, por_renglon=20)
    assert t[0][0] == 0.0 and abs(t[-1][1] - 3.0) < 0.01           # empieza en 0 y acaba con la frase
    assert all(b.count("\n") <= 1 for _, _, b in t)                  # máximo 2 renglones
    assert not estilo.trozos_subtitulos(segs, 30, 40)


def test_pista_de_textos_con_datos(tmp_path):
    e = estilo.cargar(tmp_path)
    pista = estilo.pista_de_textos(e, tmp_path, FUENTES, 10, {"tema": "El perdón", "canal": "C", "fecha": "", "frase": ""},
                                   [(4.0, 6.0, "Hola")], tmp_path)
    texto = pista.read_text()
    assert texto.startswith("ffconcat") and texto.count("duration") >= 3
    e["textos"] = [{"texto": "{nombre}"}]
    with pytest.raises(estilo.ErrorEstilo, match="no existe"):
        estilo.pista_de_textos(e, tmp_path, FUENTES, 10, {"tema": ""}, [], tmp_path)


@hay_ffmpeg
def test_reel_con_capas_intro_y_cierre(tmp_path):
    raiz = estilo.preparar_carpeta(tmp_path / "estilo_cliente")
    h = raiz / "herramientas"
    Image.new("RGBA", (200, 200), (198, 160, 72, 200)).save(h / "logo.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=green:s=1080x200:d=2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(h / "cintilla.mp4")], check=True)
    _video(h / "cierre.mp4", 2)
    e = estilo.cargar(raiz)
    e.update(capas=[{"archivo": "logo.png", "x": 40, "y": 40, "ancho": 160},
                    {"archivo": "cintilla.mp4", "x": 0, "y": 1400, "desde": 1, "hasta": 3, "croma": "#008000"}],
             intro={"archivo": "logo.png", "segundos": 1}, cierre={"archivo": "cierre.mp4"})
    fuente = _video(tmp_path / "celular.mp4", 15)
    salida = tmp_path / "reel.mp4"
    r = estilo.editar_reel(str(fuente), 2, 10, salida, raiz, FUENTES, [[3, 6, "Dios te salve María"]],
                           {"tema": "Prueba"}, e)
    info = _probe(salida)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (1080, 1920)
    assert any(s["codec_type"] == "audio" for s in info["streams"])
    assert 10.5 <= float(info["format"]["duration"]) <= 11.5 and r["duracion"] == pytest.approx(11, abs=0.2)


@hay_ffmpeg
def test_agente_de_reels_usa_el_estilo(app, monkeypatch):
    """Con estilo.json en la carpeta, los 5 reels salen con la receta del cliente (largo incluido)."""
    with app.app_context():
        raiz = estilo.preparar_carpeta(Path(app.config["ESTILO_DIR"]))
        receta = json.loads((raiz / "estilo.json").read_text(encoding="utf-8"))
        receta["duracion"] = {"min": 10, "max": 20, "ideal": 15}
        receta["mejora"]["luz"] = False
        (raiz / "estilo.json").write_text(json.dumps(receta), encoding="utf-8")
        carpeta = Path(app.config["GRABACIONES_DIR"])
        carpeta.mkdir(parents=True)
        video = _video(carpeta / "celular.mp4", 110, "320x568")
        monkeypatch.setattr(reels.whisper, "transcribir", lambda r, m: evento_falso(duracion=100))
        g = Grabacion(nombre=video.name, fecha_evento=date(2026, 10, 19), tamano=video.stat().st_size)
        db.session.add(g)
        db.session.commit()
        nuevos = reels.procesar(g)
        assert len(nuevos) == 5 and all(p.tipo == "reel" for p in nuevos)
        assert all(10 <= p.datos["fin"] - p.datos["inicio"] <= 20 for p in nuevos)
        assert db.session.get(Grabacion, g.id).estado == "lista"

        # Una herramienta que falta se ve clara en la grabación, no como error genérico
        receta["capas"] = [{"archivo": "no-esta.png"}]
        (raiz / "estilo.json").write_text(json.dumps(receta), encoding="utf-8")
        g2 = Grabacion(nombre=video.name + ".otra", fecha_evento=date(2026, 10, 19), segmentos=evento_falso(duracion=100))
        shutil.copy(video, carpeta / g2.nombre)
        db.session.add(g2)
        db.session.commit()
        assert reels.procesar(g2) == []
        g2 = db.session.get(Grabacion, g2.id)
        assert g2.estado == "error" and "no-esta.png" in g2.error


@hay_ffmpeg
def test_analizar_referencia(tmp_path):
    ref = _video(tmp_path / "referencia.mp4", 6)
    d = estilo.analizar(ref, tmp_path / "analisis")
    assert d["ancho"] == 720 and d["alto"] == 1280 and d["duracion"] == pytest.approx(6, abs=0.2)
    assert d["brillo_promedio"] and d["volumen_lufs"] is not None and d["cuadros"]
    assert (tmp_path / "analisis" / "hoja.jpg").exists() and (tmp_path / "analisis" / "datos.json").exists()


# --- Lo que se agregó al copiar la edición del cliente (2026-10-19) ------------------

def test_linea_de_tiempo_sin_pausas():
    partes = [(10.0, 14.0), (16.0, 20.0)]                 # se cortó la pausa de 14 a 16
    assert estilo.a_salida(12, partes) == 2 and estilo.a_salida(15, partes) == 4
    assert estilo.a_salida(17, partes) == 5 and estilo.a_salida(25, partes) == 8
    segs = estilo.segmentos_en_reel([[11, 13, "uno"], [13.5, 17, "dos"], [30, 31, "fuera"]], partes)
    assert segs == [[1, 3, "uno"], [3.5, 5, "dos"]]


def test_titulo_con_el_renglon_de_abajo_mas_largo():
    from PIL import ImageDraw, ImageFont
    f = ImageFont.truetype(str(FUENTES / "Fraunces_800ExtraBold.ttf"), 79)
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    assert estilo._renglones_abajo_largo(d, "Reparación del Santo Rostro de Jesús", f, 1000) == \
        ["Reparación del", "Santo Rostro de Jesús"]


def test_maquina_de_escribir_y_palabras(tmp_path):
    e = estilo.cargar(tmp_path)
    e["textos"] = [{"texto": "{tema}", "y": 300, "desde": 0, "hasta": 4, "efecto": "maquina", "letras_por_segundo": 10}]
    e["subtitulos"].update(efecto="palabras", y=1600)
    pista = estilo.pista_de_textos(e, tmp_path, FUENTES, 10, {"tema": "El perdón", "canal": "", "fecha": "", "frase": ""},
                                   [(5.0, 7.0, "uno dos tres")], tmp_path)
    tramos = pista.read_text().count("duration")
    assert tramos >= 9 + 3                    # 9 letras que aparecen una a una + 3 palabras
    assert len(list(tmp_path.glob("txt*.png"))) >= 12


@hay_ffmpeg
def test_quita_las_pausas_largas(tmp_path):
    video = tmp_path / "pausa.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x568:rate=15",
                    "-f", "lavfi", "-i", "aevalsrc='if(between(t,3,6),0,0.5*sin(2*PI*440*t))':s=48000",
                    "-t", "10", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(video)], check=True)
    partes = estilo.partes_con_voz(str(video), 0, 10, {"activo": True, "minimo": 0.6, "margen": 0.15})
    assert len(partes) == 2 and partes[0][1] == pytest.approx(3.15, abs=0.2) and partes[1][0] == pytest.approx(5.85, abs=0.2)
    assert estilo.partes_con_voz(str(video), 0, 10, {"activo": False}) == [(0, 10)]
    raiz = estilo.preparar_carpeta(tmp_path / "e")
    e = estilo.cargar(raiz)
    e.update(quitar_pausas={"activo": True, "minimo": 0.6, "margen": 0.15}, negro_final=0.4)
    r = estilo.editar_reel(str(video), 0, 10, tmp_path / "r.mp4", raiz, FUENTES, [[1, 2, "hola"], [7, 8, "adiós"]], {}, e)
    assert r["tramos"] == 2 and 7.0 <= r["duracion"] <= 7.6


def test_imagen_del_tema(app, cliente):
    from io import BytesIO

    from .conftest import login, token
    login(cliente)
    ruta = "/api/temas/2026-10-23/imagen"
    assert cliente.get(ruta).status_code == 404
    buf = BytesIO()
    Image.new("RGB", (900, 1400), (120, 90, 30)).save(buf, "PNG")
    r = cliente.post(ruta, data=buf.getvalue(), headers={"X-CSRFToken": token(cliente), "Content-Type": "image/png"})
    assert r.status_code == 200
    guardada = Path(app.config["ESTILO_DIR"]) / "herramientas" / "temas" / "2026-10-23.jpg"
    with Image.open(guardada) as im:
        assert im.format == "JPEG" and max(im.size) <= 1600
    assert cliente.get("/api/temas/2026-10-23").get_json()["imagen"] is True
    assert cliente.get(ruta).mimetype == "image/jpeg"
    # La receta del cliente la encuentra como «temas/{fecha}»
    assert estilo.herramienta(Path(app.config["ESTILO_DIR"]), "temas/{fecha_iso}".format(fecha_iso="2026-10-23")) == guardada
    malo = cliente.post(ruta, data=b"no soy imagen", headers={"X-CSRFToken": token(cliente), "Content-Type": "image/png"})
    assert malo.status_code == 400
    assert cliente.post(ruta, data=b"x", headers={"X-CSRFToken": token(cliente), "Content-Type": "text/plain"}).status_code == 400
    assert cliente.delete(ruta, headers={"X-CSRFToken": token(cliente)}).status_code == 200 and not guardada.exists()
    assert cliente.post("/api/temas/2026-10-24/imagen").status_code in (400, 401)   # sábado / sin CSRF


# --- Cortes suaves (cuadros intermedios) y música del cierre ------------------------

def test_puentes_y_linea_de_tiempo():
    partes = [(10.0, 14.0), (14.1, 18.0), (19.0, 20.0)]
    assert estilo.puentes_de(partes, {"tipo": "corte"}, 30) == [0.0, 0.0]
    p = estilo.puentes_de(partes, {"tipo": "morph", "duracion": 0.27}, 30)
    assert p[0] == pytest.approx(0.0667, abs=0.001)          # la pausa era de 0.1 s: el puente no la rebasa
    assert p[1] == pytest.approx(0.2667, abs=0.001)
    # con puentes, lo que va después del corte se recorre lo que dura el puente
    assert estilo.a_salida(15, partes, p) == pytest.approx(4 + p[0] + 0.9, abs=0.001)
    assert estilo.a_salida(18.5, partes, p) == pytest.approx(4 + p[0] + 3.9 + p[1], abs=0.001)   # cae en el puente


@hay_ffmpeg
def test_cortes_con_cuadros_intermedios_y_musica_de_cierre(tmp_path):
    video = tmp_path / "pausa.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=320x568:rate=30",
                    "-f", "lavfi", "-i", "aevalsrc='if(between(t,3,6),0,0.5*sin(2*PI*440*t))':s=48000",
                    "-t", "10", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(video)], check=True)
    raiz = estilo.preparar_carpeta(tmp_path / "e")
    h = raiz / "herramientas"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=white:s=1080x1920:d=3",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(h / "cierre.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=4",
                    "-c:a", "aac", str(h / "musica.m4a")], check=True)
    e = estilo.cargar(raiz)
    e.update(quitar_pausas={"activo": True, "minimo": 0.6, "margen": 0.15},
             transiciones={"tipo": "morph", "duracion": 0.27},
             cierre={"archivo": "cierre.mp4", "segundos": 2, "audio": "musica.m4a", "ganancia_db": 3}, negro_final=0.3)
    salida = tmp_path / "r.mp4"
    r = estilo.editar_reel(str(video), 0, 10, salida, raiz, FUENTES, [[1, 2, "hola"], [7, 8, "adiós"]], {}, e)
    assert r["tramos"] == 2 and r["transiciones"] == 1
    assert r["duracion"] == pytest.approx(7.3 + 0.2667 + 2, abs=0.35)
    info = _probe(salida)
    assert float(info["format"]["duration"]) == pytest.approx(r["duracion"], abs=0.15)
    # en el cierre suena la música (no silencio)
    sal = subprocess.run(["ffmpeg", "-hide_banner", "-ss", f"{r['duracion'] - 1.8:.2f}", "-t", "1", "-i", str(salida),
                          "-vn", "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    media = float(sal.split("mean_volume:")[1].split("dB")[0])
    assert media > -40
