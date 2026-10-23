# CLAUDE.md — Cristocéntricos

## Qué es

Sistema del equipo Cristocéntricos. **Versión corta (única versión desde 2026-10-21):** proceso guiado de 7 pasos por evento (10–11 am CDMX; lunes y viernes son fijos y cualquier otro día es evento si tiene tema): tema y fecha en el calendario → agregar guion (escrito, pegado o desde .docx/.pdf/.txt; si no hay, Claude busca en fuentes de la Iglesia) → 5 imágenes de difusión (salen al guardar el tema) → revisión técnica (celular graba la segunda toma) → grabación (StreamYard con cintillas va a TV/redes; video limpio del celular a `grabaciones/`) → 5 reels editados con el **estilo del cliente** (`estilo_cliente/`) → ideas.

La v1.0 (turnos, bandeja de aprobación, publicación, reportes, estadísticas, OBS, Meta, YouTube, Calendar) se **eliminó**; solo queda en el historial de git (commit `0f822f6`). La migración borra sus tablas viejas.

- **Nube + laptop** ([docs/railway.md](docs/railway.md)): Railway (`MODO=nube`, `Dockerfile`, `requirements-nube.txt`) solo vigila el avance; la laptop (`MODO=local`) corre el worker y hace grabación y reels. Comparten el PostgreSQL de Railway (`DATABASE_URL`); los videos nunca suben. Rutas con archivos llevan `@solo_en_laptop` (409 en la nube). `flask --app app copiar-base` pasa la SQLite a Postgres. Sin Railway, sigue funcionando todo local con SQLite y Tailscale.
- Repo: https://github.com/JGonza10/21-Cristocentricos
- Diseño (tokens, colores, componentes; temas Claro y Oro): [docs/diseno.md](docs/diseno.md). Pestañas Inicio · Material · Configuración.

## Comandos (PowerShell)

```powershell
.\iniciar.bat                                   # uso diario: servidor (waitress, 127.0.0.1:5021) + worker
flask --app app run --debug --port 5021         # desarrollo: API
cd frontend; npm run dev                        # desarrollo: React :5173
python -m agentes.worker                        # agentes
cd frontend; npm run build                      # Flask sirve frontend/dist
flask --app app crear-usuario
flask --app app material-vaciar --si            # vacía la pestaña Material
pytest -q; pip-audit
```

Requiere ffmpeg en el PATH.

## Estructura

- `app/` — Flask (API JSON, auth, modelos, CLI): `bandeja.py` (Material: listar, editar texto, recortar, archivo, vaciar), `avance.py` (7 pasos), `temas.py`, `equipo.py` (integrantes que reciben el aviso por correo), `grabar.py` (subir video), `panel.py`, `ideas.py`, `migracion.py` (agrega columnas y borra tablas de la v1.0).
- `agentes/` — `worker.py` (horarios), `carrusel.py` (5 imágenes de difusión), `reels.py`, `avisos.py`, `ideas.py`.
- `servicios/` — **estilo** (edición de reels con la receta `estilo_cliente/estilo.json`: mejora, capas, textos, subtítulos, intro/cierre, música; `analizar` de la referencia), ffmpeg, whisper (faster-whisper local), google + correo (solo Gmail).
- `frontend/` — React + Vite; tokens en `src/styles/tokens.css`. Prompter sin línea guía.
- `estilo_cliente/` — `referencia/` (video muestra del cliente), `herramientas/` (sus imágenes y animaciones), `estilo.json`, `LEEME.md`. Comandos: `flask --app app estilo-analizar`, `estilo-probar`.
- `fondos/` — fondos de imagen por tema (p. ej. «No tengas miedo»: normal, claro y centro).
- Fuera de git: `datos/` (SQLite), `grabaciones/`, `paquetes/`, `secretos/`, material del cliente en `estilo_cliente/`.

## Cuentas

- Máximo 2 (`MAX_USUARIOS`): Gonza y Esbeidy.
- `datos/cuentas_nuevas.json` (`[{"usuario","nombre","password_temporal"}]`) crea cuentas al arrancar con `cambiar_password=True` y se borra solo. Con contraseña temporal solo se permiten `auth.yo`, `auth.cambiar_password` y `auth.logout` (403 con `cambiar_password: true`).

## Reglas

- **Nada se publica solo**: el material se descarga desde Material.
- Los reels deben quedar **igual a la referencia del cliente**: cualquier cambio de look va en `estilo_cliente/estilo.json`, no en el código.
- **Sin APIs de IA de pago**: todo local (Whisper, reglas, ffmpeg). El guion con Claude se hace copiando instrucciones a claude.ai.
- Login primero, bcrypt, límite de intentos, SQL parametrizado, secretos en `.env`, errores amables y detalle al log.
- Responsivo: probar a 375 px, botones ≥ 44 px. Colores solo con los tokens.
- Decir **"evento"**, no "rosario" (salvo hashtags, la pista de Whisper y los misterios).
- En el proceso solo se marca u omite el paso actual (409 si se brinca).
- La base de datos no se puede escribir desde la VM de Claude (disk I/O error): los cambios de datos van como función de la app (botón, CLI o `cuentas_nuevas.json`).
- Fuera de alcance hasta que Gonza lo pida: Comunidad, Parroquias, Bienvenida y Respuestas.
- Pendiente con cuenta real: autorizar Gmail (`google-autorizar`).
