# CLAUDE.md — Cristocéntricos Automático

> Contexto para Claude al programar este proyecto. Responder siempre en **español (México)**,
> con explicaciones simples y prácticas. Código en **Python** o **bash/PowerShell**.

## 1. Qué es
Sistema que convierte cada **evento en vivo** (lunes y viernes, 10–11 am, hora CDMX)
en **3 reels** y un **carrusel de invitación (5 imágenes)**, con una **bandeja de aprobación**:
nada se publica sin visto bueno humano.

- **Agente de reels:** al guardarse la grabación (`grabaciones/`), transcribe, elige 3 momentos
  (< 60 s), los pasa a vertical 9:16 con subtítulos y nombre del canal → bandeja.
- **Agente de carrusel:** 2 días antes de cada lunes/viernes genera 5 imágenes blanco/vino
  (invitación, misterios del día —lunes gozosos, viernes dolorosos—, en vivo, intenciones, cierre) + texto.
- **Agente de publicación:** solo actúa sobre lo aprobado. Crea `subir_manual/<red>/` con archivos
  y `texto.txt`; YouTube sube directo (privado hasta verificar la app de Google).
- **Calendario del equipo:** turnos (dirige / apoya), reparto automático domingos 6 pm,
  invitaciones a Google Calendar.
- **Reloj en vivo:** hora CDMX + cuenta regresiva, solo tema perla; en Evento es un enlace chico «Reloj» que lo abre en grande (Gonza, 2026-10-16).
- Redes: Instagram, Facebook, TikTok, YouTube y canal de TV (StreamYard).

## 2. Stack (confirmado 2026-10-16)
- **Corre local en la PC de Gonza (Windows)**. Sin Railway por ahora.
- **El aprobador entra desde otra computadora por Tailscale**: `tailscale serve --bg 5021` da HTTPS
  privado (`https://<pc>.<tailnet>.ts.net`). El servidor sigue en `127.0.0.1`; no se abren puertos.
  Con `TAILSCALE=1`, el bloqueo por origen usa la cabecera `Tailscale-User-Login`.
- Backend: Python 3.12 + **Flask** como API JSON (`/api/...`), sesiones con cookie.
- Frontend: **React + Vite** (`frontend/`). En desarrollo: Vite en :5173 con proxy a Flask :5021.
  En uso diario: `npm run build` y Flask sirve `frontend/dist`.
- BD: **SQLite** (`datos/cristocentricos.db`, en .gitignore) con SQLAlchemy. Migrar a PostgreSQL solo si algún día se sube a la nube.
- Video: **ffmpeg**. Transcripción: **faster-whisper** local (modelo `small`, español).
- Imágenes del carrusel: **Pillow** (1080×1350), con fuentes Spectral / Public Sans guardadas en `assets/fuentes/`.
- Tareas programadas: **APScheduler** en el worker. Vigilar carpeta: **watchdog** sobre `grabaciones/`.
- **Sin API de IA de pago**: todo se procesa en la PC (ver §2.1).
- `iniciar.bat` abre 2 ventanas: servidor Flask y worker de agentes.

### 2.1 Cómo elige el agente de reels los 3 momentos (reglas locales, sin API)
1. faster-whisper transcribe con marcas de tiempo por segmento.
2. Busca frases clave: "primer/segundo/.../quinto misterio", "intención", "Dios te salve", "Gloria", cierre.
3. Arma candidatos de 30–55 s que empiecen al inicio de una frase y terminen al final de otra.
4. Puntúa: anuncio de misterio > intenciones > oración completa; evita silencios (ffmpeg `silencedetect`).
5. Elige 3 sin traslape, repartidos en el evento. Subtítulos `.srt` quemados con ffmpeg + nombre del canal.
6. Texto y hashtags salen de plantillas por tipo de misterio (gozosos/dolorosos).
7. Si algo falla, la bandeja permite ajustar inicio/fin a mano antes de aprobar.

### 2.2 Usuarios y roles
- **2 cuentas con el mismo permiso**: Gonza + 1 aprobador. Ambos aprueban, rechazan y editan textos.
- Sin registro público (es app local): las cuentas se crean con `flask crear-usuario`.
- Los integrantes del calendario **no tienen cuenta**: solo nombre + correo para invitaciones.

## 3. Estructura
```
21 Cristocéntricos/
├─ app/                # Flask: API, auth, modelos, CLI
├─ frontend/           # React + Vite (src/styles/tokens.css con los tokens de §4)
├─ assets/fuentes/     # Spectral, Public Sans, JetBrains Mono (TTF para Pillow)
├─ datos/              # SQLite + logs (en .gitignore)
├─ agentes/            # reels.py, carrusel.py, publicacion.py
├─ servicios/          # ffmpeg, whisper, youtube, calendar
├─ grabaciones/        # entrada de OBS/StreamYard (en .gitignore)
├─ paquetes/           # salida por fecha → subir_manual/<red>/ (en .gitignore)
├─ secretos/           # client_secret.json, tokens (en .gitignore)
├─ tests/              # pytest
├─ servidor.py         # waitress para uso diario (127.0.0.1)
├─ .env.example  .gitignore  README.md  iniciar.bat  requirements.txt  pytest.ini
```

## 4. Diseño — usar SIEMPRE estos tokens
Fuente única: `frontend/src/styles/tokens.css`. Nunca escribir colores sueltos en los componentes.
Concepto: *panel lavanda claro; el morado es el único color de acción; la pestaña activa lleva el degradado lila → rosa.*

### 4.1 Tipografía (Google Fonts)
- Todo: **Public Sans** 400 / 600 / 700 / 800 — `--f-body`. Títulos en 800, sin serif.
- Números/reloj: **JetBrains Mono** 500/700 — `--f-mono`.

### 4.2 Colores — modo claro
```css
--bg:#f9f7fc; --surface:#ffffff; --surface-2:#faf8fd;
--ink:#241b31; --ink-2:#554767; --muted:#72677e; --muted-2:#81778b; --line:#e7e0ef;
--accent:#7d45cb; --accent-strong:#65409a; --accent-soft:#f0e8fc; --on-accent:#ffffff;
--grad-tab:linear-gradient(90deg,#a56be5,#cd76dd);
--grad-hero:linear-gradient(135deg,#faf7ff,#efeafe 55%,#e9e9ff);
--ok:#2b7a4b; --ok-soft:#e1f1e7; --warn:#8a5d00; --warn-soft:#fbf0d3; --off:#a39bab;
```
### 4.3 Colores — modo oscuro
```css
--bg:#15111c; --surface:#1e1828; --surface-2:#241d30;
--ink:#f1ecf8; --ink-2:#d2c7e0; --muted:#b3a8c2; --muted-2:#9d92ac; --line:#3a3048;
--accent:#b48cf0; --accent-strong:#c9a8f5; --accent-soft:#2e2442; --on-accent:#1a1225;
--grad-tab:linear-gradient(90deg,#8b55d0,#b45cc4);
--grad-hero:linear-gradient(135deg,#221a31,#211c38 55%,#1f2140);
--ok:#78c995; --ok-soft:#1b3326; --warn:#e6b84e; --warn-soft:#3a2f12; --off:#6e6479;
```
Se aplica con `@media (prefers-color-scheme:dark){:root:not([data-theme="light"])}` y `:root[data-theme="dark"]`.
El selector Claro/Oscuro de la cabecera guarda la elección en el navegador.

### 4.4 Imágenes para redes (carrusel y reels)
Las piezas que se publican **no** usan el morado de la app: siguen en **blanco y vino**
(`#ffffff`, `#fbf9f7`, vino `#7a1c2e`, vino suave `#f3e4e7`, texto `#3a1420`, oro `#8f6b10`),
con títulos en **Spectral** 700 y texto en Public Sans. Fuentes TTF en `assets/fuentes/`.

### 4.5 Significado de colores
| Color | Uso |
|---|---|
| Morado (`--accent`) | Acciones, botones, números, enlaces, pestaña activa |
| Degradado lila→rosa | Solo la pestaña activa y el sello del login |
| Verde (`--ok`) | Funcionando / activo / publicado |
| Ámbar (`--warn`) | Falta algo: sin asignar, sin configurar |
| Gris (`--off`) | Inactivo, ya pasó, automático |

### 4.6 Estructura de pantallas
- **Cabecera** fija: "† Cristocéntricos · sistema del equipo", selector Claro/Oscuro, botón Salir.
- **Pestañas**: Inicio · Contenido · Evento · Configuración (en celular dice "Ajustes").
- **Inicio**: tarjeta principal del próximo evento (degradado), 3 tarjetas de estado (Bandeja, Agentes,
  Invitaciones), "Esta semana y la que sigue" (lun/vie con botón Ver) y "Agenda editorial".
- **Contenido**: bandeja de aprobación (fases 2–5). **Evento**: detalle de un evento, turnos y reloj.
- **Configuración**: cuenta y seguridad.

### 4.7 Componentes
- Botón primario: fondo `--accent`, radio 12px, alto ≥ 44px. Botón suave: `--accent-soft` + texto morado.
- Tarjeta: `--surface`, borde `--line`, radio 20px, padding 22px (18px en celular).
- Fila de lista: `--surface-2`, borde `--line`, radio 14px; la de hoy lleva barra morada a la izquierda.
- Etiqueta (eyebrow): 0.7rem, 700, mayúsculas, `letter-spacing:.1em`, color `--accent-strong`.
- Estado: punto de color + texto en negrita (`.estado.ok / .warn / .off`).
- Pastilla: radio 99px, mayúsculas 0.68rem.
- Ancho máximo 940px, margen lateral 16px, cuerpo 16px/1.55. Probar siempre a 375px.

## 5. Reglas obligatorias (proceso seguro de Gonza)
- **Login primero**, antes de cualquier otra función. Contraseñas con **bcrypt/argon2**.
- Secretos solo en `.env` (nunca en código ni en git). `.gitignore` desde el primer commit.
- SQL siempre **parametrizado**; validar todo input de formularios.
- Cookies `HttpOnly`, `Secure`, `SameSite=Lax`; límite de intentos fallidos de login.
- Errores: mensaje amable al usuario, detalle solo en log.
- **Responsivo desde el primer borrador** (probar a 375px, botones ≥ 44px).
- **Nunca publicar sin aprobación humana**.
- Datos de integrantes (nombre, correo) → aviso de privacidad breve (LFPDPPP).
- `pytest` para login, aprobación y generación de paquetes. `pip-audit` antes de publicar.
- `README.md` con instalación, variables de entorno y despliegue.

## 6. Forma de trabajar con Gonza
- Windows + PowerShell. Paso a paso, verificando antes de avanzar.
- Escribir los archivos **directamente en esta carpeta**; al cerrar cambios, entregar archivos **completos** (no diffs).
- Explicar con ejemplos simples. Al final, 2–4 líneas de sugerencias (aprendizaje / automatización) solo si aportan.

## 7. Comandos
```powershell
# Una sola vez
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd frontend; npm install; cd ..
flask --app app crear-usuario      # Gonza y el aprobador

# Desarrollo (3 ventanas)
flask --app app run --debug --port 5021   # API :5021
cd frontend; npm run dev           # React :5173
python -m agentes.worker           # agentes

# Uso diario
cd frontend; npm run build; cd ..
.\iniciar.bat

pytest -q
pip-audit
```
Requisito externo: **ffmpeg** en el PATH (`winget install Gyan.FFmpeg`).

## 8. Fases (todas en alcance; este orden)
1. Esqueleto Flask + React, tokens de diseño, **login** (2 usuarios, bcrypt, límite de intentos)
2. **Bandeja de aprobación** (pendiente / aprobado / rechazado, editar texto)
3. **Agente de carrusel** (5 imágenes, 2 días antes de lunes/viernes)
4. **Agente de reels** (watchdog + Whisper + reglas §2.1 + ffmpeg)
5. **Agente de publicación** (`subir_manual/<red>/` + YouTube API en privado)
6. **Calendario del equipo** (turnos, reparto domingos 6 pm, Google Calendar)
7. **Reloj en vivo** + overlay de transmisión (solo perla, enlace chico en Evento)
8. (Futuro) Publicación automática en Meta

**Estado (2026-10-16):** fases 1 a 8 programadas — 122 pruebas, pip-audit y npm audit sin vulnerabilidades.
- Bandeja: `app/bandeja.py` (`crear_paquete()`, `paquetes_aprobados()`, `actualizar_por_agente()`).
- Agentes: `agentes/{carrusel,reels,publicacion,turnos}.py`, horario en `agentes/worker.py`.
- Servicios: `servicios/{ffmpeg,whisper,google,youtube,calendario,meta}.py`.
- Equipo/turnos: `app/equipo.py`. Estado general: `app/panel.py`. Overlay: `frontend/reloj.html`.
- Migración automática de columnas en `app/migracion.py` (SQLite en WAL).
- Pendiente con cuentas reales: autorizar Google y, si se quiere, Meta (`META_AUTO=1`, probado solo con simulaciones).

Cada fase termina con: pruebas `pytest`, revisión de seguridad y archivos completos entregados.

## 9. Decisiones tomadas
| # | Tema | Decisión |
|---|---|---|
| 1 | Despliegue | Local en la PC de Gonza, SQLite, `iniciar.bat` |
| 2 | Frontend | React + Vite, servido por Flask en uso diario |
| 3 | Alcance | Bandeja + carrusel, reels, calendario y reloj (orden de §8) |
| 4 | IA para reels | Solo local, reglas simples, sin API de pago |
| 5 | Usuarios | Gonza + 1 aprobador, mismo permiso |
| 6 | Acceso remoto | Aprobador en otra PC vía Tailscale (máquina compartida), sin abrir puertos |

## Palabra "evento" en vez de "rosario" (Gonza, 2026-10-16)
Todo lo visible y los nombres internos dicen **evento** (`frontend/src/evento.js`, `proximoEvento`, `es_dia_de_evento`, `proximos_eventos`, `APOYOS_POR_EVENTO`). Se quedan a propósito: los hashtags `#SantoRosario` / `#RosarioEnVivo` (búsqueda en redes), la pista de Whisper en `servicios/whisper.py` (reconoce las oraciones) y los nombres de los misterios. No reintroducir "rosario" en textos nuevos.
