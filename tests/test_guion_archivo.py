"""Guion desde un archivo (.txt, .md, .docx, .pdf): devuelve el texto para revisarlo antes de guardar."""
import io
import zipfile

from .conftest import login, token

RUTA = "/api/temas/2026-10-23/guion/archivo"


def _subir(cliente, nombre, datos):
    return cliente.post(RUTA, data=datos, headers={"X-CSRFToken": token(cliente), "X-Nombre": nombre,
                                                   "Content-Type": "application/octet-stream"})


def _docx(parrafos):
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    cuerpo = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in parrafos)
    xml = f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{w}"><w:body>{cuerpo}</w:body></w:document>'
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("word/document.xml", xml)
    return b.getvalue()


def _pdf(texto):
    contenido = f"BT /F1 12 Tf 50 750 Td ({texto}) Tj ET"
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            f"<< /Length {len(contenido)} >>\nstream\n{contenido}\nendstream",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n{o}\nendobj\n".encode()
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offs).encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF".encode()
    return out


def test_pide_sesion(cliente):
    assert _subir(cliente, "g.txt", b"hola").status_code == 401


def test_txt_con_acentos(cliente):
    login(cliente)
    r = _subir(cliente, "guion.txt", "Oración inicial\r\nPrimer misterio  \n".encode("utf-8"))
    assert r.status_code == 200 and r.get_json()["texto"] == "Oración inicial\nPrimer misterio"


def test_txt_de_windows_cp1252(cliente):
    login(cliente)
    assert _subir(cliente, "g.md", "Señal de la cruz".encode("cp1252")).get_json()["texto"] == "Señal de la cruz"


def test_docx(cliente):
    login(cliente)
    r = _subir(cliente, "Guion.DOCX", _docx(["Bienvenida", "Primer misterio gozoso"]))
    assert r.get_json()["texto"] == "Bienvenida\nPrimer misterio gozoso"


def test_pdf(cliente):
    login(cliente)
    r = _subir(cliente, "guion.pdf", _pdf("Primer misterio doloroso"))
    assert r.status_code == 200 and "Primer misterio doloroso" in r.get_json()["texto"]


def test_rechaza_otros_tipos_y_archivos_rotos(cliente):
    login(cliente)
    assert _subir(cliente, "virus.exe", b"MZ").status_code == 400
    assert _subir(cliente, "roto.docx", b"no es zip").status_code == 400
    assert _subir(cliente, "roto.pdf", b"%PDF-basura").status_code == 400
    assert _subir(cliente, "vacio.txt", b"   ").status_code == 400


def test_guion_demasiado_largo(cliente):
    login(cliente)
    r = _subir(cliente, "largo.txt", ("x" * 20001).encode())
    assert r.status_code == 400 and "caracteres" in r.get_json()["error"]
