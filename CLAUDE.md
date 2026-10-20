# CLAUDE.md — Cristocéntricos (versión reducida)

> Contexto para Claude al programar este proyecto. Responder siempre en **español (México)**,
> con explicaciones simples y prácticas. Código en **Python** o **bash/PowerShell**.

## 1. Qué es
App local para preparar cada **programa en vivo** del equipo (ej. «Capítulo 1. No tengas miedo»,
programa matutino de Esbeidy Solís). Tres pasos consecutivos; cada uno desbloquea el siguiente:
1. **Fecha, hora, tema y guion** (PDF/.md → Markdown) + frases para difusión.
2. **Imágenes de difusión** con tema y fecha (5 PNG 1080×1350, blanco y vino).
3. **Revisión técnica del día**: audio, StreamYard, grabación, reloj y **prompter**.

- **Sin "intenciones recibidas" ni "cita bíblica"**: se quitan solas del guion.
- **Prompter** (`#prompter/<fecha>`): en la tableta, avanza al escuchar la lectura (Web Speech API,
  es-MX, solo hacia adelante), pausa, ◀ ▶ por párrafo, tocar palabra para saltar, tamaño y espejo.
  En el guion, las líneas `>` son indicaciones (se ven en amarillo, no se siguen).
- **Calendario**: solo el mes, el tema de cada fecha y los nombres del equipo (agregar/quitar, asignar al día).
- La grabación la descarga Gonza de StreamYard a mano.

**Siguiente (no hecho):** agente de reels que use la grabación + el guion para encontrar 3 momentos
(faster-whisper local, ffmpeg 9:16 con subtítulos; imagen al centro opcional). Todo con aprobación humana.

## 2. Stack
- **Local en la PC de Gonza (Windows)**, `iniciar.bat` abre el servidor (waitress, `servidor.py`).
- Acceso desde otra PC o la tableta por **Tailscale**: `tailscale serve --bg 5000` da HTTPS privado.
  El servidor sigue en `127.0.0.1`; no se abren puertos. El micrófono del prompter exige HTTPS.
- Backend: Python 3.12 + **Flask** (API JSON `/api/...`), SQLite (`datos/cristocentricos.db`) con SQLAlchemy.
- Frontend: **React + Vite** (`frontend/`), Flask sirve `frontend/dist`.
- Guion: **pypdf**. Imágenes: **Pillow** con Spectral Bold y Public Sans (`assets/fuentes/`).
- **Sin API de IA de pago**: todo se procesa en la PC.
- **2 cuentas con el mismo permiso** (Gonza + 1), creadas con `flask crear-usuario`. El equipo del
  calendario no tiene cuenta: solo su nombre.

## 3. Estructura
```
app/          eventos.py (API de pasos, integrantes), auth.py, modelos.py, cli.py, seguridad.py
servicios/    guion.py (PDF→MD, quitar secciones, frases), difusion.py (5 imágenes)
frontend/src/ paginas/ (Inicio, Evento, Calendario, Prompter, Configuracion, Login),
              prompter.js (lógica pura del prompter), fechas.js, styles/tokens.css
guiones/      guion y frases del primer programa (2026-10-22)
assets/fuentes/  TTF para Pillow (licencia OFL)
tests/        pytest · frontend/src/__tests__/ node:test
datos/ paquetes/  base de datos e imágenes generadas (en .gitignore)
```

## 4. Diseño
Fuente única: `frontend/src/styles/tokens.css`. Nunca colores sueltos en componentes.
Panel lavanda; morado (`--accent`) = única acción; degradado lila→rosa solo en pestaña activa y login.
Verde `--ok` = listo, ámbar `--warn` = falta algo, gris `--off` = bloqueado.
Prompter siempre oscuro (`--pr-*`). Imágenes para redes en **blanco y vino**
(`#ffffff`, `#fbf9f7`, vino `#7a1c2e`, vino suave `#f3e4e7`, texto `#3a1420`, oro `#8f6b10`), títulos Spectral.
Pestañas: Inicio · Evento · Calendario · Configuración ("Ajustes" en celular).
Botones ≥ 44px, ancho máximo 940px, probar a 375px y en tableta (1024px).

## 5. Reglas obligatorias (proceso seguro de Gonza)
- Login primero; contraseñas con bcrypt; límite de intentos; cookies `HttpOnly`, `Secure`, `SameSite=Lax`.
- Secretos solo en `.env`. SQL parametrizado (ORM); validar todo input.
- Errores: mensaje amable al usuario, detalle solo en log.
- Nombres del equipo → aviso de privacidad breve (LFPDPPP).
- `pytest`, `npm test`, `pip-audit` y `npm audit` antes de entregar.

## 6. Forma de trabajar con Gonza
- Windows + PowerShell. Paso a paso, verificando antes de avanzar.
- Explicar con ejemplos simples. Al final, 2–4 líneas de sugerencias solo si aportan.

## 7. Comandos
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd frontend; npm install; npm run build; cd ..
flask --app app crear-usuario
flask --app app limpiar-datos      # base en blanco (--con-usuarios borra también las cuentas)
.\iniciar.bat

pytest -q
cd frontend; npm test; cd ..
pip-audit
```

**Estado (2026-10-20):** versión reducida lista para la primera prueba (jueves 22); en vivo el lunes 26.
