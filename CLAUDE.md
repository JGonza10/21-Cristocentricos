# CLAUDE.md — Cristocéntricos

## Qué es

Sistema del equipo Cristocéntricos: convierte cada **evento en vivo** (lunes y viernes, 10–11 am CDMX) en reels y carruseles con una **bandeja de aprobación** (nada se publica sin visto bueno). Incluye proceso guiado de 13 pasos por evento, tema por evento, calendario de turnos, reloj en vivo, grabación con OBS, ideas por voz, reporte semanal y estadísticas.

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

- `app/` — Flask (API JSON, auth, modelos, CLI): `bandeja.py`, `avance.py` (13 pasos), `temas.py`, `equipo.py`, `panel.py`, `reportes.py`, `estadisticas.py`, `ideas.py`, `migracion.py`.
- `agentes/` — `worker.py` (horarios), `carrusel.py`, `reels.py`, `publicacion.py`, `turnos.py`, `reporte.py`, `grabacion.py`, `ideas.py`.
- `servicios/` — ffmpeg, whisper (faster-whisper local), google, youtube, calendario, correo (Gmail API), obs, meta.
- `frontend/` — React + Vite; tokens en `src/styles/tokens.css`.
- Fuera de git: `datos/` (SQLite), `grabaciones/`, `paquetes/`, `secretos/`.

## Reglas

- **Nunca publicar sin aprobación humana.**
- **Sin APIs de IA de pago**: todo local (Whisper, reglas, ffmpeg). El guion con Claude se hace copiando instrucciones a claude.ai.
- Login primero, bcrypt, límite de intentos, SQL parametrizado, secretos en `.env`, errores amables y detalle al log.
- Responsivo: probar a 375 px, botones ≥ 44 px. Colores solo con los tokens.
- Decir **"evento"**, no "rosario" (salvo hashtags, la pista de Whisper y los misterios).
- En el proceso solo se marca u omite el paso actual (409 si se brinca).
- OBS: borrar `.sentinel/run_*` antes de abrir y usar el `monitor_id` del monitor principal (si no, graba negro).
- Fuera de alcance hasta que Gonza lo pida: Comunidad, Parroquias, Bienvenida y Respuestas.
- Pendiente con cuentas reales: autorizar Google (volver a correr `google-autorizar` por el alcance `gmail.send`) y Meta (`META_AUTO=1`).
