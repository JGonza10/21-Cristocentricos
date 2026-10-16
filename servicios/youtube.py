"""Subida a YouTube en PRIVADO (hasta que Google verifique la app y se revise el video)."""
from . import google


def subir(ruta: str, titulo: str, descripcion: str) -> str:
    """Sube un video y devuelve su enlace. Lanza excepción si algo falla."""
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    cred = google.credenciales()
    if cred is None:
        raise RuntimeError("YouTube no está autorizado")
    yt = build("youtube", "v3", credentials=cred, cache_discovery=False)
    cuerpo = {
        "snippet": {"title": titulo[:100], "description": descripcion[:5000], "categoryId": "22",
                    "defaultLanguage": "es"},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(ruta, mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    peticion = yt.videos().insert(part="snippet,status", body=cuerpo, media_body=media)
    respuesta = None
    while respuesta is None:
        _estado, respuesta = peticion.next_chunk()
    return f"https://youtu.be/{respuesta['id']}"
