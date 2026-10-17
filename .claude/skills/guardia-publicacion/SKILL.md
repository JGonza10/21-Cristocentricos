---
name: guardia-publicacion
description: Revisión obligatoria de un paquete de `paquetes/<fecha>/` antes de darlo por listo — formato de video (9:16, < 60 s, H.264/AAC), imágenes 1080×1350, textos dentro de límites, sin secretos ni archivos extraños, manifiesto íntegro. Úsala al terminar el agente de publicación, cuando Gonza pregunte "¿ya está listo para subir?" o antes de cualquier subida a YouTube.
---

# Guardia de publicación

Es la última barrera antes de que algo salga a redes. Si la guardia falla, el paquete
**no** se marca como listo y la bandeja muestra en ámbar qué falta.

## Cómo correrla
```bash
python .claude/skills/guardia-publicacion/scripts/revisar_paquete.py paquetes/2026-10-19
```
En PowerShell es igual. Requiere `ffprobe` (viene con ffmpeg). Pillow es opcional
(si está, también revisa medidas de imágenes). Sale con código 0 si todo está bien, 1 si hay
fallas — así el agente puede usarla con `subprocess.run(..., check=False)`.

## Qué revisa
| Revisión | Regla |
|---|---|
| Estructura | Existe `subir_manual/` y cada red tiene `texto.txt` |
| Reels | `.mp4`, H.264 + AAC, 1080×1920 (9:16), duración < 60 s, ≤ 250 MB |
| Carrusel | `.png`/`.jpg` de 1080×1350, de 1 a 10 imágenes (esperamos 5) |
| TikTok | Solo video (sin imágenes) |
| Textos | UTF-8 válido; nada vacío |
| Secretos | Ningún `.env`, `client_secret*`, `token*`, `.db`, ni texto con `SECRET_KEY=` o `refresh_token` |
| Extraños | Solo `.mp4 .png .jpg .txt .json`; nada de ejecutables ni enlaces simbólicos |
| Manifiesto | Si hay `manifiesto.json`, cada sha256 coincide con el archivo real |

## Además, revisar a mano (no lo hace el script)
- En la BD, todo lo empaquetado está en `aprobado` (consultar `Publicacion` vs `Contenido`).
- Ver 2–3 segundos de cada reel: subtítulos legibles y nombre del canal visible.
- Colores de piezas: blanco y vino (§4.4), nunca el morado de la app.

## Si algo falla
Reportar a Gonza en una lista corta: archivo → problema → cómo arreglarlo
(p. ej. "reel-2.mp4 dura 63 s → recortar fin en la bandeja"). No "arreglar" a escondidas
videos o textos ya aprobados: cualquier cambio vuelve a la bandeja para nueva aprobación.
