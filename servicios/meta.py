"""Publicación automática en Facebook e Instagram con la API Graph de Meta (fase 8).

Desactivada por defecto (META_AUTO=0). Solo se usa para paquetes ya aprobados.

Qué se puede publicar desde una PC local (sin servidor público):
  - Facebook (página): carrusel (fotos) y reel.
  - Instagram (cuenta profesional): reel, con subida "resumable" del archivo local.
  - Instagram carrusel: la API exige que cada imagen esté en una URL pública de internet;
    como esta app no está en internet, el carrusel de Instagram sigue siendo manual.

Necesita en el .env: META_PAGE_ID, META_IG_USER_ID y META_TOKEN (token de página de larga
duración con permisos pages_manage_posts, instagram_content_publish, etc.).
"""
import json
import time
from pathlib import Path

import requests
from flask import current_app

TIEMPO_ESPERA = 60          # segundos por petición
ESPERA_IG_MAX = 300         # segundos esperando a que Instagram procese el reel


class ErrorMeta(Exception):
    pass


def configurado() -> bool:
    c = current_app.config
    return bool(c["META_AUTO"] and c["META_TOKEN"] and c["META_PAGE_ID"])


def soporta(red: str, tipo: str) -> bool:
    c = current_app.config
    if not configurado():
        return False
    if red == "facebook":
        return True
    if red == "instagram":
        return tipo == "reel" and bool(c["META_IG_USER_ID"])
    return False


def _graph(ruta: str) -> str:
    return f"https://graph.facebook.com/{current_app.config['META_GRAPH_VERSION']}/{ruta}"


def _respuesta(r: requests.Response) -> dict:
    try:
        datos = r.json()
    except ValueError:
        datos = {}
    if r.status_code >= 400 or "error" in datos:
        # El mensaje de Meta va al log; al usuario se le muestra algo amable.
        raise ErrorMeta(json.dumps(datos.get("error", datos))[:800])
    return datos


def _autorizacion() -> dict:
    # El token va en la cabecera, nunca en la URL: así no aparece en logs ni en mensajes de error.
    return {"Authorization": f"OAuth {current_app.config['META_TOKEN']}"}


def _post(ruta: str, **kwargs) -> dict:
    return _respuesta(requests.post(_graph(ruta), data=kwargs.pop("data", {}), headers=_autorizacion(),
                                    timeout=TIEMPO_ESPERA, **kwargs))


def _get(ruta: str, **params) -> dict:
    return _respuesta(requests.get(_graph(ruta), params=params, headers=_autorizacion(), timeout=TIEMPO_ESPERA))


def _subir_binario(url: str, archivo: Path) -> dict:
    with archivo.open("rb") as f:
        r = requests.post(url, data=f, timeout=600, headers={
            **_autorizacion(), "offset": "0", "file_size": str(archivo.stat().st_size),
        })
    return _respuesta(r)


# --- Facebook -----------------------------------------------------------------------

def facebook_carrusel(imagenes: list[Path], texto: str) -> str:
    pagina = current_app.config["META_PAGE_ID"]
    ids = []
    for img in imagenes:
        with img.open("rb") as f:
            ids.append(_post(f"{pagina}/photos", data={"published": "false"},
                             files={"source": (img.name, f, "image/png")})["id"])
    medios = {f"attached_media[{i}]": json.dumps({"media_fbid": x}) for i, x in enumerate(ids)}
    post = _post(f"{pagina}/feed", data={"message": texto, **medios})
    return f"https://www.facebook.com/{post['id']}"


def facebook_reel(video: Path, texto: str) -> str:
    pagina = current_app.config["META_PAGE_ID"]
    inicio = _post(f"{pagina}/video_reels", data={"upload_phase": "start"})
    _subir_binario(inicio["upload_url"], video)
    _post(f"{pagina}/video_reels", data={"upload_phase": "finish", "video_id": inicio["video_id"],
                                         "video_state": "PUBLISHED", "description": texto})
    return f"https://www.facebook.com/reel/{inicio['video_id']}"


# --- Instagram ----------------------------------------------------------------------

def instagram_reel(video: Path, texto: str) -> str:
    cuenta = current_app.config["META_IG_USER_ID"]
    contenedor = _post(f"{cuenta}/media", data={"media_type": "REELS", "upload_type": "resumable",
                                                "caption": texto, "share_to_feed": "true"})
    _subir_binario(contenedor["uri"], video)
    limite = time.monotonic() + ESPERA_IG_MAX
    while True:
        estado = _get(contenedor["id"], fields="status_code").get("status_code")
        if estado == "FINISHED":
            break
        if estado in ("ERROR", "EXPIRED") or time.monotonic() > limite:
            raise ErrorMeta(f"Instagram no terminó de procesar el reel (estado {estado})")
        time.sleep(5)
    media = _post(f"{cuenta}/media_publish", data={"creation_id": contenedor["id"]})
    return _get(media["id"], fields="permalink").get("permalink") or "https://www.instagram.com/"


def publicar(red: str, tipo: str, archivos: list[Path], texto: str) -> str:
    """Publica y devuelve el enlace. Antes hay que revisar `soporta(red, tipo)`."""
    if red == "facebook":
        return facebook_carrusel(archivos, texto) if tipo == "carrusel" else facebook_reel(archivos[0], texto)
    if red == "instagram" and tipo == "reel":
        return instagram_reel(archivos[0], texto)
    raise ErrorMeta(f"{red}/{tipo} no se publica automáticamente")
