# CLAUDE.md — Cristocéntricos

## Qué es

Sistema del equipo Cristocéntricos. **Versión corta (v2.0, 2026-10-19):** proceso guiado de 7 pasos por evento (lunes y viernes, 10–11 am CDMX): calendario con tema → guion (si no hay, Claude busca en fuentes de la Iglesia) → 5 imágenes de difusión al guardar el tema → revisión técnica (sin OBS; celular graba la segunda toma) → grabación (StreamYard con cintillas va a TV/redes; video limpio del celular a `grabaciones/`) → 5 reels editados con el **estilo del cliente** (`estilo_cliente/`) → ideas.

Ocultos, no borrados (`VERSION_CORTA=0` en `.env` + `frontend/src/version.js`): turnos, bandeja de aprobación, publicación, reporte semanal, estadísticas, OBS, reel promocional y carrusel de escenas. La v1.0 completa está en `versiones/Cristocentricos v.1.0.zip`.

- Corre local en la PC de Gonza; el aprobador entra por **Tailscale** (`tailscale serve --bg 5021`), sin abrir puertos.
- Repo: https://github.com/JGonza10/21-Cristocentricos
- Diseño (tokens, colores, componentes): [docs/diseno.md](docs/diseno.md).

## Comandos (PowerShell)

```powershell
.\iniciar.bat                                   # uso diario: servidor (waitress, 127.0.0.1:5021) + worker
flask --app app run --debug --port 5021         # desarrollo: API
cd frontend; npm run dev                        # desarrollo: React :5173
python -m agentes.worker                        # agentes
cd frontend; npm run build                      # Flask sirve frontend/dist
flask --app app crear-usuario
pytest -q; pip-audit
```

Requiere ffmpeg en el PATH.

## Estructura

- `app/` — Flask (API JSON, auth, modelos, CLI): `bandeja.py` (Material), `avance.py` (7 pasos; `PASOS_COMPLETOS` = los 13 de la v1.0), `temas.py`, `equipo.py`, `panel.py`, `reportes.py`, `estadisticas.py`, `ideas.py`, `migracion.py`.
- `agentes/` — `worker.py` (horarios), `carrusel.py`, `reels.py`, `publicacion.py`, `turnos.py`, `reporte.py`, `grabacion.py`, `ideas.py`.
- `servicios/` — **estilo** (edición de reels con la receta `estilo_cliente/estilo.json`: mejora, capas, textos, subtítulos, intro/cierre, música; `analizar` de la referencia), ffmpeg, whisper (faster-whisper local), google, youtube, calendario, correo (Gmail API), obs, meta.
- `frontend/` — React + Vite; tokens en `src/styles/tokens.css`.
- `estilo_cliente/` — `referencia/` (video muestra del cliente), `herramientas/` (sus imágenes y animaciones), `estilo.json`, `LEEME.md`. Comandos: `flask --app app estilo-analizar`, `estilo-probar`.
- Fuera de git: `datos/` (SQLite), `grabaciones/`, `paquetes/`, `secretos/`, `versiones/`, material del cliente en `estilo_cliente/`.

## Reglas

- **Nunca publicar sin aprobación humana** (en la versión corta no se publica nada solo: se descarga desde Material).
- Los reels deben quedar **igual a la referencia del cliente**: cualquier cambio de look va en `estilo_cliente/estilo.json`, no en el código.
- **Sin APIs de IA de pago**: todo local (Whisper, reglas, ffmpeg). El guion con Claude se hace copiando instrucciones a claude.ai.
- Login primero, bcrypt, límite de intentos, SQL parametrizado, secretos en `.env`, errores amables y detalle al log.
- Responsivo: probar a 375 px, botones ≥ 44 px. Colores solo con los tokens.
- Decir **"evento"**, no "rosario" (salvo hashtags, la pista de Whisper y los misterios).
- En el proceso solo se marca u omite el paso actual (409 si se brinca).
- OBS (solo v1.0): borrar `.sentinel/run_*` antes de abrir y usar el `monitor_id` del monitor principal (si no, graba negro).
- Fuera de alcance hasta que Gonza lo pida: Comunidad, Parroquias, Bienvenida y Respuestas.
- Pendiente con cuentas reales: autorizar Google (volver a correr `google-autorizar` por el alcance `gmail.send`) y Meta (`META_AUTO=1`).
