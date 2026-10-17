---
name: youtube-privado
description: Cómo subir reels a YouTube desde la PC de Gonza con la YouTube Data API v3 de forma segura — OAuth de app de escritorio, token en `secretos/`, subida reanudable, siempre en privado, manejo de cuota y errores. Úsala al crear o tocar `servicios/youtube.py`, el paso de YouTube del agente de publicación o cualquier cosa con `client_secret.json`.
---

# YouTube: subida privada y segura

## Por qué siempre privado
Mientras la app de Google Cloud **no esté verificada** (auditoría de Google), YouTube deja
los videos subidos por la API **bloqueados en privado**. El sistema lo asume: sube en
`private`, y Gonza lo cambia a público a mano desde YouTube Studio después de revisarlo.
Código: `privacyStatus` va **fijo** en `"private"`; no se lee de formularios ni del `.env`.

## Dependencias
```
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
```
Agrégalas a `requirements.txt` con versión fija y corre `pip-audit` después.

## Credenciales (una sola vez)
1. Google Cloud Console → proyecto → habilitar **YouTube Data API v3**.
2. Pantalla de consentimiento: tipo *Externo*, agregar el correo del canal como *usuario de prueba*.
3. Credencial **OAuth → App de escritorio** → descargar como `secretos/client_secret.json`.
4. Primera ejecución: `python -m servicios.youtube --autorizar` abre el navegador
   (`InstalledAppFlow.run_local_server(port=0)`) y guarda `secretos/token_youtube.json`.
- Alcance mínimo: `https://www.googleapis.com/auth/youtube.upload` (nada más).
- `secretos/` ya está en `.gitignore`. Nunca imprimir el token en logs ni en errores.
- En modo *prueba*, el refresh token caduca a los 7 días: si aparece `invalid_grant`,
  mostrar "Vuelve a autorizar YouTube" y no reintentar.

## Esqueleto de `servicios/youtube.py`
```python
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

PRIVACIDAD = "private"   # fijo hasta verificar la app de Google

def subir(ruta_mp4, titulo, descripcion, etiquetas, credenciales):
    yt = build("youtube", "v3", credentials=credenciales, cache_discovery=False)
    cuerpo = {
        "snippet": {"title": titulo, "description": descripcion, "tags": etiquetas,
                    "categoryId": "29", "defaultLanguage": "es"},   # 29 = Organizaciones sin fines de lucro
        "status": {"privacyStatus": PRIVACIDAD, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(ruta_mp4), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    peticion = yt.videos().insert(part="snippet,status", body=cuerpo, media_body=media)
    respuesta = None
    while respuesta is None:
        _estado, respuesta = peticion.next_chunk(num_retries=5)   # reintenta 5xx con espera
    return respuesta["id"]
```

## Errores y qué hacer
| Error | Causa | Acción |
|---|---|---|
| `quotaExceeded` (403) | Cuota diaria agotada (10 000 unidades; cada subida cuesta mucho) | Marcar `error`, dejar el paquete `youtube/` como respaldo, reintentar mañana |
| `uploadLimitExceeded` | Límite de subidas del canal | Igual que arriba |
| `invalid_grant` | Token caducado o revocado | Pedir volver a autorizar |
| 5xx / red | Fallo temporal | `next_chunk(num_retries=5)` ya lo cubre |
Al usuario: mensaje corto en español. Al log: `HttpError.status_code` y razón, **sin** token.
Consulta el costo actual por subida en la consola de cuotas; no lo des por hecho.

## Shorts
YouTube lo trata como Short si es vertical y corto (nuestros reels: 9:16, < 60 s).
Poner `#Shorts` al final de la descripción ayuda pero no es obligatorio.

## Pruebas
Nunca llamar a Google en `pytest`. Simular con `monkeypatch` una función `subir` falsa y comprobar:
privacidad `"private"`, título ≤ 100 caracteres, que `quotaExceeded` deja la fila en `error`
y que el paquete de respaldo existe.
