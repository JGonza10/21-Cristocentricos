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


def test_texto_segun_el_dia(app):
    with app.app_context():
        lunes = carrusel.texto_carrusel(LUNES)
        viernes = carrusel.texto_carrusel(VIERNES)
    assert "Lunes 19 de octubre" in lunes and "gozosos" in lunes and "#MisteriosGozosos" in lunes
    assert "dolorosos" in viernes and "#MisteriosDolorosos" in viernes
    assert len(lunes) <= 2200


def test_enlace_del_canal_en_el_texto(app):
    app.config["CANAL_ENLACE"] = "youtube.com/@cristocentricos"
    with app.app_context():
        assert "youtube.com/@cristocentricos" in carrusel.texto_carrusel(LUNES)


def test_preparar_mete_el_paquete_a_la_bandeja(app):
    with app.app_context():
        p = carrusel.preparar_carrusel(LUNES)
        assert p.estado == "pendiente" and p.tipo == "carrusel" and p.fecha_evento == LUNES
        assert p.archivos == ["1.png", "2.png", "3.png", "4.png", "5.png"]
        assert (Path(app.config["PAQUETES_DIR"]) / p.carpeta / "5.png").exists()
        assert p.historial[0].accion == "creado"


def test_no_duplica_salvo_que_se_fuerce(app):
    with app.app_context():
        primero = carrusel.preparar_carrusel(LUNES)
        assert carrusel.preparar_carrusel(LUNES) is None
        otro = carrusel.preparar_carrusel(LUNES, forzar=True)
        assert otro.carpeta != primero.carpeta
        assert Paquete.query.filter_by(tipo="carrusel").count() == 2


def test_solo_lunes_y_viernes(app):
    with app.app_context(), pytest.raises(ValueError):
        carrusel.preparar_carrusel(date(2026, 10, 20))


@pytest.mark.parametrize("ahora, esperado", [
    (datetime(2026, 10, 17, 7, 5, tzinfo=fechas.CDMX), [LUNES]),        # sábado → el lunes
    (datetime(2026, 10, 21, 7, 5, tzinfo=fechas.CDMX), [VIERNES]),      # miércoles → el viernes
    (datetime(2026, 10, 22, 9, 0, tzinfo=fechas.CDMX), [VIERNES]),      # PC apagada el miércoles
    (datetime(2026, 10, 23, 9, 59, tzinfo=fechas.CDMX), [VIERNES]),     # aún antes de empezar
    (datetime(2026, 10, 23, 10, 0, tzinfo=fechas.CDMX), []),            # ya empezó: tarde
    (datetime(2026, 10, 20, 7, 5, tzinfo=fechas.CDMX), []),             # martes: nada que hacer
])
def test_tarea_programada(app, monkeypatch, ahora, esperado):
    monkeypatch.setattr(fechas, "ahora_cdmx", lambda: ahora)
    with app.app_context():
        nuevos = carrusel.tarea()
        assert [p.fecha_evento for p in nuevos] == esperado
        assert carrusel.tarea() == []          # la siguiente hora ya no repite


def test_comando_carrusel(app):
    runner = app.test_cli_runner()
    r = runner.invoke(args=["carrusel", "2026-10-19"])
    assert r.exit_code == 0 and "Carrusel listo" in r.output
    r = runner.invoke(args=["carrusel", "2026-10-19"])
    assert "Ya existe" in r.output
    r = runner.invoke(args=["carrusel", "2026-10-20"])
    assert r.exit_code != 0


def test_fechas_en_espanol():
    assert fechas.nombre_fecha(LUNES) == "Lunes 19 de octubre"
    assert fechas.nombre_fecha(date(2026, 9, 16)) == "Miércoles 16 de septiembre"
    assert fechas.inicio(LUNES).utcoffset().total_seconds() == -6 * 3600   # CDMX sin horario de verano
    assert fechas.proximos_rosarios(date(2026, 10, 17), 7) == [LUNES, VIERNES]
