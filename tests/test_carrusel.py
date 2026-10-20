from datetime import date, datetime
from pathlib import Path

import pytest
from PIL import Image

from agentes import carrusel, fechas
from app.modelos import Paquete

LUNES = date(2026, 10, 19)
VIERNES = date(2026, 10, 23)


def test_genera_5_imagenes_del_tamano_correcto(app, tmp_path):
    with app.app_context():
        nombres = carrusel.generar_imagenes(LUNES, tmp_path / "c")
    assert nombres == ["1.png", "2.png", "3.png", "4.png", "5.png"]
    for n in nombres:
        with Image.open(tmp_path / "c" / n) as img:
            assert img.size == (1080, 1350)


@pytest.fixture
def sin_video(monkeypatch):
    """El reel promocional tarda unos segundos con ffmpeg; aquí basta con un archivo de mentira."""
    def falso(f, carpeta):
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "promo.mp4").write_bytes(b"0")
    monkeypatch.setattr(carrusel, "_reel_promocional", falso)


def _tema(app, f, titulo="El perdón que libera", **extra):
    from app.extensiones import db
    from app.modelos import Tema
    with app.app_context():
        db.session.add(Tema(fecha=f, titulo=titulo, **extra))
        db.session.commit()


def test_texto_de_difusion_con_el_tema(app):
    _tema(app, LUNES, descripcion="Hablaremos de cómo perdonar de corazón.")
    with app.app_context():
        t = carrusel.texto_difusion(LUNES)
        sin = carrusel.texto_difusion(VIERNES)
    assert t.startswith("🙏 El perdón que libera") and "perdonar de corazón" in t
    assert "Lunes 19 de octubre" in t and "#Cristocéntricos" in t and len(t) <= 2200
    assert sin.startswith("🙏 Evento en vivo")


def test_enlace_del_canal_en_el_texto(app):
    app.config["CANAL_ENLACE"] = "youtube.com/@cristocentricos"
    with app.app_context():
        assert "youtube.com/@cristocentricos" in carrusel.texto_difusion(LUNES)


def test_cita_del_tema(app):
    _tema(app, LUNES, cita="Perdona y serás perdonado (Lc 6,37)")
    with app.app_context():
        assert carrusel._cita(LUNES) == ("Perdona y serás perdonado", "Lc 6,37")
        assert carrusel._cita(VIERNES) == carrusel.CITA_DEFECTO


def test_difusion_completa_con_reel_promocional(app):
    _tema(app, LUNES)
    app.config["REEL_PROMO"] = True              # en la versión corta va apagado
    with app.app_context():
        nuevos = carrusel.preparar_difusion(LUNES)
        assert [p.tipo for p in nuevos] == ["carrusel", "reel"]
        assert all(p.datos["momento"] == "antes" and p.estado == "pendiente" for p in nuevos)
        assert nuevos[0].archivos == ["1.png", "2.png", "3.png", "4.png", "5.png"]
        assert nuevos[0].titulo == "Difusión · El perdón que libera"
        video = Path(app.config["PAQUETES_DIR"]) / nuevos[1].carpeta / "promo.mp4"
        from servicios import ffmpeg
        assert 14 <= ffmpeg.duracion(str(video)) <= 16


def test_preparar_mete_el_paquete_a_la_bandeja(app, sin_video):
    with app.app_context():
        p = carrusel.preparar_carrusel(LUNES)
        assert p.estado == "pendiente" and p.tipo == "carrusel" and p.fecha_evento == LUNES
        assert p.archivos == ["1.png", "2.png", "3.png", "4.png", "5.png"]
        assert (Path(app.config["PAQUETES_DIR"]) / p.carpeta / "5.png").exists()
        assert p.historial[0].accion == "creado"


def test_no_duplica_salvo_que_se_fuerce(app, sin_video):
    with app.app_context():
        primero = carrusel.preparar_carrusel(LUNES)
        assert carrusel.preparar_carrusel(LUNES) is None
        otro = carrusel.preparar_carrusel(LUNES, forzar=True)
        assert otro.carpeta != primero.carpeta
        assert Paquete.query.filter_by(tipo="carrusel").count() == 2


def test_solo_lunes_y_viernes(app):
    with app.app_context(), pytest.raises(ValueError):
        carrusel.preparar_carrusel(date(2026, 10, 20))


def test_tarea_arma_la_difusion_solo_con_tema(app, monkeypatch, sin_video):
    _tema(app, VIERNES)
    _tema(app, date(2026, 11, 6), titulo="Primer evento principal")
    ahora = {"t": datetime(2026, 10, 17, 7, 5, tzinfo=fechas.CDMX)}
    monkeypatch.setattr(fechas, "ahora_cdmx", lambda: ahora["t"])
    with app.app_context():
        nuevos = carrusel.tarea()          # el lunes 19 no tiene tema; el 6 de nov aún está lejos
        assert [(p.fecha_evento, p.tipo) for p in nuevos] == [(VIERNES, "carrusel")]   # solo las 5 imágenes
        assert carrusel.tarea() == []      # no se repite
        ahora["t"] = datetime(2026, 10, 24, 7, 5, tzinfo=fechas.CDMX)
        assert {p.fecha_evento for p in carrusel.tarea()} == {date(2026, 11, 6)}   # ya entra en las 2 semanas


def test_tarea_no_arma_difusion_de_un_evento_que_ya_empezo(app, monkeypatch, sin_video):
    _tema(app, VIERNES)
    monkeypatch.setattr(fechas, "ahora_cdmx", lambda: datetime(2026, 10, 23, 10, 0, tzinfo=fechas.CDMX))
    with app.app_context():
        assert carrusel.tarea() == []


def test_comando_carrusel(app, sin_video):
    runner = app.test_cli_runner()
    r = runner.invoke(args=["carrusel", "2026-10-19"])
    assert r.exit_code == 0 and "Carrusel listo" in r.output
    r = runner.invoke(args=["carrusel", "2026-10-19"])
    assert "Ya existe" in r.output
    r = runner.invoke(args=["carrusel", "2026-10-20"])
    assert r.exit_code != 0


def test_frase_de_un_momento():
    segs = [[0, 4, "Bueno"], [4, 9, "El amor de Dios no se cansa nunca de buscarnos."], [9, 12, "eh"]]
    assert carrusel.frase_de(segs, 0, 12) == "El amor de Dios no se cansa nunca de buscarnos."
    assert carrusel.frase_de(segs, 20, 30) == ""


def test_fechas_en_espanol():
    assert fechas.nombre_fecha(LUNES) == "Lunes 19 de octubre"
    assert fechas.nombre_fecha(date(2026, 9, 16)) == "Miércoles 16 de septiembre"
    assert fechas.inicio(LUNES).utcoffset().total_seconds() == -6 * 3600   # CDMX sin horario de verano
    assert fechas.proximos_eventos(date(2026, 10, 17), 7) == [LUNES, VIERNES]


def test_frase_empieza_con_mayuscula():
    segs = [[0, 6, "mandará a sus ángeles que te cuiden en todos tus caminos"]]
    assert carrusel.frase_de(segs, 0, 6).startswith("Mandará a sus ángeles")
