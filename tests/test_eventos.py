import io
from pathlib import Path

import pytest
from PIL import Image

from servicios import guion

from .conftest import login, token

FECHA = "2026-10-22"
GUION_MD = """# Capítulo 1. No tengas miedo

## Gancho

¿Sientes que vives con miedo? Jesús mismo experimentó el miedo y la incertidumbre ante el futuro.

## Intenciones recibidas

Por la salud de Juan.

## Cita bíblica

Mateo 14, 27.

## Cierre

El miedo es una emoción humana, pero con confianza en Dios podemos sobreponernos.
"""


@pytest.fixture
def sesion(app, cliente, tmp_path):
    app.config["PAQUETES_DIR"] = tmp_path / "paquetes"
    login(cliente)
    return cliente


def _put(cliente, ruta, datos):
    return cliente.put(ruta, json=datos, headers={"X-CSRFToken": token(cliente)})


def _post(cliente, ruta, **kw):
    return cliente.post(ruta, headers={"X-CSRFToken": token(cliente)}, **kw)


def _pdf(texto: str) -> bytes:
    """PDF mínimo de una página con el texto dado (sin dependencias extra)."""
    def escapar(t):
        return t.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    lineas = " ".join(f"({escapar(l)}) Tj T*" for l in texto.splitlines())
    contenido = f"BT /F1 12 Tf 14 TL 50 750 Td {lineas} ET".encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(contenido) + contenido + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    salida, offsets = b"%PDF-1.4\n", []
    for i, obj in enumerate(objetos, 1):
        offsets.append(len(salida))
        salida += b"%d 0 obj\n" % i + obj + b"\nendobj\n"
    xref = len(salida)
    salida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    salida += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    salida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, xref)
    return salida


# --- Servicio de guion ---

def test_quita_intenciones_y_cita_biblica():
    md = guion.quitar_secciones(GUION_MD)
    assert "Intenciones" not in md and "Juan" not in md
    assert "Cita" not in md and "Mateo" not in md
    assert "## Cierre" in md and "## Gancho" in md


def test_pdf_a_markdown_detecta_titulos_e_indicaciones():
    pdf = _pdf("ESTRUCTURA:\n1. Saludo y presentacion:\nHola, buenos dias, bienvenidos.\n"
               "a) Nombrar ejemplos personales\nINTENCIONES RECIBIDAS\nPor Juan")
    md = guion.convertir(pdf)
    assert "## 1. Saludo y presentacion" in md
    assert "Hola, buenos dias, bienvenidos." in md
    assert "> a) Nombrar ejemplos personales" in md
    assert "Juan" not in md


def test_frases_difusion_evita_saludos_y_rezos():
    md = GUION_MD + "\n## Despedida\n\nYo soy Esbeidy y esto fue Cristocéntricos.\n\nDios te salve María, llena eres de gracia.\n"
    frases = guion.frases_difusion(md, "No tengas miedo")
    assert "¿Sientes que vives con miedo?" in frases
    assert not any("Esbeidy" in f or "Dios te salve" in f or "Juan" in f for f in frases)


# --- API ---

def test_eventos_piden_sesion(cliente):
    assert cliente.get(f"/api/eventos/{FECHA}").status_code == 401
    assert cliente.get("/api/integrantes").status_code == 401


def test_evento_nuevo_vacio_y_fecha_invalida(sesion):
    r = sesion.get(f"/api/eventos/{FECHA}")
    assert r.status_code == 200
    assert r.get_json()["evento"]["pasos"] == {"datos": False, "imagenes": False, "revision": False}
    assert sesion.get("/api/eventos/2026-13-40").status_code == 400


def test_paso_1_guarda_tema_y_guion_sin_secciones_quitadas(sesion):
    r = _put(sesion, f"/api/eventos/{FECHA}", {"tema": "No tengas miedo", "hora": "10:00", "guion_md": GUION_MD})
    ev = r.get_json()["evento"]
    assert r.status_code == 200 and ev["pasos"]["datos"] is True
    assert "Mateo" not in ev["guion_md"]


@pytest.mark.parametrize("datos", [{"tema": "x" * 121}, {"hora": "25:00"}, {"frases": ["ok", ""]},
                                   {"frases": "no es lista"}, {"guion_md": 5}])
def test_paso_1_valida_datos(sesion, datos):
    assert _put(sesion, f"/api/eventos/{FECHA}", datos).status_code == 400


def test_subir_pdf_convierte_a_markdown(sesion):
    pdf = _pdf("1. Saludo:\nHola, buenos dias.\nJesus mismo sintio miedo ante el futuro, confia en Dios.")
    r = _post(sesion, f"/api/eventos/{FECHA}/guion",
              data={"archivo": (io.BytesIO(pdf), "programa.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 200
    assert "## 1. Saludo" in r.get_json()["evento"]["guion_md"]


def test_subir_archivo_que_no_es_pdf(sesion):
    r = _post(sesion, f"/api/eventos/{FECHA}/guion",
              data={"archivo": (io.BytesIO(b"MZ\x90\x00"), "virus.pdf")}, content_type="multipart/form-data")
    assert r.status_code == 400


def test_pasos_en_orden(sesion, app):
    ruta = f"/api/eventos/{FECHA}"
    assert _post(sesion, f"{ruta}/imagenes").status_code == 409          # falta el paso 1
    _put(sesion, ruta, {"tema": "No tengas miedo", "guion_md": GUION_MD, "frases": ["Confía en Dios."]})
    assert _put(sesion, f"{ruta}/revision", {"audio": True}).status_code == 409  # falta el paso 2

    r = _post(sesion, f"{ruta}/imagenes")
    ev = r.get_json()["evento"]
    assert r.status_code == 200 and ev["pasos"]["imagenes"] is True and len(ev["imagenes"]) == 5
    png = sesion.get(ev["imagenes"][0])
    assert png.status_code == 200
    assert Image.open(io.BytesIO(png.data)).size == (1080, 1350)
    assert (Path(app.config["PAQUETES_DIR"]) / FECHA / "difusion" / "5.png").exists()

    todo = {k["id"]: True for k in ev["revision_items"]}
    assert "prompter" in todo
    assert _put(sesion, f"{ruta}/revision", {"no-existe": True}).status_code == 400
    ev = _put(sesion, f"{ruta}/revision", todo).get_json()["evento"]
    assert ev["pasos"]["revision"] is True

    # Si cambia el tema, las imágenes ya no sirven y hay que regenerarlas.
    ev = _put(sesion, ruta, {"tema": "Otro tema"}).get_json()["evento"]
    assert ev["pasos"] == {"datos": True, "imagenes": False, "revision": False}


def test_integrantes_y_calendario(sesion):
    r = _post(sesion, "/api/integrantes", json={"nombre": "  Esbeidy   Solís "})
    assert r.status_code == 201
    iid = r.get_json()["integrante"]["id"]
    assert _post(sesion, "/api/integrantes", json={"nombre": "esbeidy solís"}).status_code == 409
    assert _post(sesion, "/api/integrantes", json={"nombre": "x"}).status_code == 400

    _put(sesion, f"/api/eventos/{FECHA}", {"tema": "No tengas miedo"})
    ev = _put(sesion, f"/api/eventos/{FECHA}/integrantes", {"ids": [iid]}).get_json()["evento"]
    assert ev["integrantes"] == [{"id": iid, "nombre": "Esbeidy Solís"}]

    mes = sesion.get("/api/eventos?mes=2026-10").get_json()["eventos"]
    assert mes[0]["tema"] == "No tengas miedo" and mes[0]["integrantes"][0]["nombre"] == "Esbeidy Solís"
    assert sesion.get("/api/eventos?mes=2026-13").status_code == 400

    assert sesion.delete(f"/api/integrantes/{iid}", headers={"X-CSRFToken": token(sesion)}).status_code == 200
    assert sesion.get("/api/eventos?mes=2026-10").get_json()["eventos"][0]["integrantes"] == []


def test_proximos_eventos(sesion, monkeypatch):
    from datetime import date
    from app import eventos
    monkeypatch.setattr(eventos, "hoy_cdmx", lambda: date(2026, 10, 20))
    for f, t in [("2026-10-19", "Pasado"), ("2026-10-26", "Lunes"), ("2026-10-22", "Jueves")]:
        _put(sesion, f"/api/eventos/{f}", {"tema": t})
    d = sesion.get("/api/eventos/proximos").get_json()
    assert [e["tema"] for e in d["eventos"]] == ["Jueves", "Lunes"]
    assert d["hoy"] == "2026-10-20"


def test_microfono_permitido_para_el_prompter(cliente):
    assert "microphone=(self)" in cliente.get("/api/auth/csrf").headers["Permissions-Policy"]
