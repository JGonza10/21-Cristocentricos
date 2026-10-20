# Cristocéntricos

Prepara cada programa en vivo del equipo en 3 pasos: **fecha, tema y guion** → **imágenes de
difusión** → **revisión técnica con prompter**. Incluye un calendario con el tema de cada fecha y los
nombres del equipo. Corre en la PC de Gonza.

## Requisitos (Windows)
- Python 3.12 o superior
- Node.js 20 o superior

## Repositorio
https://github.com/JGonza10/21-Cristocentricos (público: nunca subir `.env`, la base de datos ni videos).

## Trabajar en otra computadora (laptop)
```powershell
cd C:\Claude_2026\Proyectos
git clone https://github.com/JGonza10/21-Cristocentricos.git "21 Cristocentricos"
cd "21 Cristocentricos"
```
Luego sigue "Instalación" (abajo). Cada laptop tiene su propio `.env` y su propia base de datos:
la base de datos real vive en la PC del sistema, la laptop es para programar.
Antes de empezar a trabajar: `git pull`. Al terminar: `git add .`, `git commit -m "..."`, `git push`.

## Instalación (una sola vez)
```powershell
cd "C:\Claude_2026\Proyectos\21 Cristocéntricos"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # pega el resultado en SECRET_KEY del .env

flask --app app crear-usuario      # tu cuenta
flask --app app crear-usuario      # la del aprobador

cd frontend
npm install
npm run build
cd ..
```

## Empezar en blanco (antes de la primera prueba)
```powershell
flask --app app limpiar-datos                 # borra eventos, equipo e imágenes; deja las cuentas
flask --app app limpiar-datos --con-usuarios  # también borra las cuentas (luego: crear-usuario)
```
Pide confirmación antes de borrar.

## Uso diario
Doble clic en `iniciar.bat`. Se abre la ventana del servidor (no la cierres) y el navegador en
http://localhost:5000.

## Acceso del aprobador desde otra computadora (Tailscale)
Tailscale crea una red privada y cifrada entre tu PC y la del aprobador. La app **no** queda en
internet y no se abren puertos en el módem. Funciona igual si están en la misma casa o en otra ciudad.

**En tu PC (una sola vez):**
1. Instala Tailscale (https://tailscale.com/download) e inicia sesión.
2. Deja en el `.env`: `HOST=127.0.0.1` y `TAILSCALE=1`.
3. Con `iniciar.bat` corriendo, en PowerShell:
   ```powershell
   tailscale serve --bg 5000
   ```
   La primera vez te pedirá activar los certificados HTTPS en una página web; acepta.
   Te dará una dirección tipo `https://pc-gonza.algo.ts.net`.
4. En https://login.tailscale.com/admin/machines, en tu PC elige **Share** y manda la invitación
   al correo del aprobador. Así solo ve esa computadora, nada más de tu red.

**En la PC del aprobador:**
1. Instala Tailscale, inicia sesión con su correo y acepta la invitación.
2. Abre `https://pc-gonza.algo.ts.net` y entra con su usuario de la app.

**Importante:** tu PC debe estar encendida y con `iniciar.bat` abierto para que el aprobador entre.

## Pasos de cada evento
En la pestaña **Evento** (o desde el **Calendario**) cada paso se desbloquea al terminar el anterior:
1. **Fecha, tema y guion.** Sube el PDF o un `.md` del programa (se convierte solo a Markdown) o pega
   el texto. Se quitan solas las secciones "intenciones recibidas" y "cita bíblica". Las líneas que
   empiezan con `>` son indicaciones: el prompter las muestra en amarillo y no las sigue.
   Revisa las frases para difusión (las 2 primeras salen en las imágenes).
2. **Imágenes de difusión.** 5 imágenes 1080×1350 en blanco y vino; quedan en `paquetes/<fecha>/difusion/`.
   Si cambias tema, fecha, hora o frases, hay que volver a generarlas.
3. **Revisión técnica del día**, con el botón **Abrir prompter**.

## Prompter en la tableta
1. Instala Tailscale en la tableta y acepta la invitación a tu PC (igual que el aprobador).
2. Abre `https://pc-gonza.algo.ts.net` en **Chrome** (Android) o **Safari** (iPad) y entra con tu usuario.
   Tiene que ser la dirección `https`: sin ella el navegador no deja usar el micrófono.
3. Evento → Revisión técnica → **Abrir prompter** → **Escuchar** y acepta el permiso del micrófono.
4. El texto avanza conforme se lee. **Pausa** lo detiene; ◀ ▶ saltan de párrafo; tocar una palabra
   lleva el prompter ahí; A− / A+ cambian el tamaño; ⇋ es modo espejo. Con teclado: espacio y flechas.

El reconocimiento de voz del navegador necesita internet (Google o Apple procesan el audio). Si se
corta la red, el prompter se maneja con los botones.

## Desarrollo
```powershell
# Ventana 1: API
flask --app app run --debug
# Ventana 2: interfaz con recarga automática
cd frontend; npm run dev          # abre http://localhost:5173
```

## Variables de entorno (.env)
| Variable | Para qué sirve | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Firma las sesiones. Obligatoria. | 64 caracteres hex |
| `COOKIE_SECURE` | Cookie solo por conexión segura | `1` |
| `SESION_HORAS` | Duración de la sesión | `8` |
| `MAX_USUARIOS` | Máximo de cuentas | `2` |
| `HOST` / `PORT` | Dónde escucha el servidor | `127.0.0.1` / `5000` |
| `TAILSCALE` | El aprobador entra por `tailscale serve` | `1` |

## Comandos útiles
```powershell
flask --app app crear-usuario
flask --app app cambiar-password gonza
flask --app app limpiar-datos
pytest                 # pruebas
cd frontend; npm test  # pruebas del prompter
pip-audit              # dependencias vulnerables (Python)
cd frontend; npm audit # dependencias vulnerables (JavaScript)
```

## Seguridad incluida
- Contraseñas con bcrypt; mínimo 10 caracteres con letras y números.
- Bloqueo de 15 minutos tras 5 intentos fallidos por usuario (o 20 por equipo).
- Token CSRF en todas las acciones; cookie de sesión `HttpOnly`, `Secure`, `SameSite=Lax`.
- Errores amables en pantalla; el detalle técnico queda en `datos/logs/app.log`.
- Cabeceras de seguridad (CSP, sin iframes, nosniff).
- El servidor solo escucha en esta PC (`127.0.0.1`); desde fuera solo se entra por Tailscale (HTTPS).
- Con Tailscale, el bloqueo por intentos fallidos se lleva por cuenta de Tailscale.

## Publicación
No se publica en internet: es una app local. Si algún día se sube a Railway, cambiar SQLite
por PostgreSQL y revisar el checklist de seguridad con Claude antes.

## Privacidad
El calendario del equipo guarda solo el nombre de los integrantes, para organizar quién participa en
cada fecha. No se guardan correos ni se comparte con nadie (aviso breve en la pantalla, LFPDPPP).
