# Cristocéntricos Automático · versión corta (v2.0)

Convierte cada evento en vivo (lunes y viernes, 10 a 11 am) en **5 imágenes de difusión** y **5 reels
editados con el estilo que pide el cliente**. Corre en la PC de Gonza.

Es la **versión corta**: cada evento son 7 pasos y todo el material se descarga desde la pestaña **Material**
(no se publica nada solo).

| Qué hace | Cuándo |
|---|---|
| 5 imágenes de difusión con su texto | En cuanto se guarda el tema en el calendario |
| 5 reels editados con el estilo del cliente (luz, enfoque, sin ruido, sus imágenes y animaciones) | Solo, cuando llega el video del celular a `grabaciones/` |
| Material: ver, ajustar el texto y descargar | Pestaña **Material** |
| Ideas escritas o por voz | Botón «Ideas» (y último paso de cada evento) |

### Los 7 pasos de cada evento
1. **Calendario:** se pone la cita (el evento) y el tema a grabar. Ahí mismo se sube la **imagen del tema**
   (la que va al centro de los reels, como el Santo Rostro).
2. **Guion, solo si lo hay.** Si no lo hay, «Preparar guion con Claude» copia las instrucciones para que Claude
   busque el tema en fuentes de la Iglesia (Biblia, Catecismo, Magisterio, santos) con sus citas y arme el guion.
3. **Difusión:** desde que el tema se guarda salen solas 5 imágenes (pestaña Material).
4. **Revisión técnica:** audio, cámara, internet, StreamYard, **celular grabando la segunda toma**, guion y reloj.
5. **Grabación:** StreamYard guarda el video como sale del stream (con cintillas) → canal de TV y la red indicada.
   El **celular** graba el video limpio (sin cintillas) → se copia a **`grabaciones/`** (o «Subir video del celular»).
6. **5 reels con el estilo del cliente:** se toman los 5 mejores momentos del video limpio y cada uno se edita
   igual que la referencia del cliente con sus herramientas (carpeta **`estilo_cliente/`**, ver su `LEEME.md`).
7. **Ideas:** se guarda lo que surgió en el evento.

### Carpetas que usas
| Carpeta | Qué pones ahí |
|---|---|
| `grabaciones/` | El video limpio del celular de cada evento (de donde salen los reels) |
| `estilo_cliente/referencia/` | El video que entregó el cliente como muestra de la edición |
| `estilo_cliente/herramientas/` | Sus imágenes, animaciones, intro, cierre, música y fuentes |
| `estilo_cliente/estilo.json` | La receta de edición (la ajusta Claude con `estilo-analizar`) |

## Requisitos (Windows)
- Python 3.12 o superior
- Node.js 20 o superior
- ffmpeg (para los reels): `winget install Gyan.FFmpeg`
- ~2 GB libres: la primera vez, Whisper descarga su modelo `small` (~500 MB)

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
flask --app app crear-usuario      # la de Esbeidy (o con datos/cuentas_nuevas.json)

cd frontend
npm install
npm run build
cd ..
```

## Uso diario
Doble clic en `iniciar.bat`. Se abren **dos ventanas que no debes cerrar**:
1. **Servidor**: la página en http://localhost:5021.
2. **Agentes**: preparan la difusión y editan los reels según su horario.

Si la ventana de agentes está cerrada, Inicio muestra «Agentes: Apagados».

### Estilo del cliente (reels)
```powershell
.venv\Scripts\flask --app app estilo-analizar                      # mide la referencia y saca sus cuadros
.venv\Scripts\flask --app app estilo-probar grabaciones\celular.mp4 --inicio 120 --fin 165
```
Todo el detalle de la receta está en `estilo_cliente/LEEME.md`.

## Dos computadoras
La app, los agentes, la base de datos y **todos los videos** viven en una sola PC (la "servidora").
La otra entra por Tailscale (sección siguiente): ve el material, sube grabaciones y captura ideas;
los videos nunca suben a la nube.

## Acceso de Esbeidy desde otra computadora (Tailscale)
Tailscale crea una red privada y cifrada entre tu PC y la de Esbeidy. La app **no** queda en
internet y no se abren puertos en el módem. Funciona igual si están en la misma casa o en otra ciudad.

**En tu PC (una sola vez):**
1. Instala Tailscale (https://tailscale.com/download) e inicia sesión.
2. Deja en el `.env`: `HOST=127.0.0.1` y `TAILSCALE=1`.
3. Con `iniciar.bat` corriendo, en PowerShell:
   ```powershell
   tailscale serve --bg 5021
   ```
   La primera vez te pedirá activar los certificados HTTPS en una página web; acepta.
   Te dará una dirección tipo `https://pc-gonza.algo.ts.net`.
4. En https://login.tailscale.com/admin/machines, en tu PC elige **Share** y manda la invitación
   al correo de Esbeidy. Así solo ve esa computadora, nada más de tu red.

**En la PC de Esbeidy:**
1. Instala Tailscale, inicia sesión con su correo y acepta la invitación.
2. Abre `https://pc-gonza.algo.ts.net` y entra con su usuario de la app.

**Importante:** tu PC debe estar encendida y con `iniciar.bat` abierto para que Esbeidy entre.

## Desarrollo
```powershell
# Ventana 1: API
flask --app app run --debug --port 5021
# Ventana 2: interfaz con recarga automática
cd frontend; npm run dev          # abre http://localhost:5173
```

## Cuentas
Hay dos cuentas (Gonza y Esbeidy, `MAX_USUARIOS=2`). Una cuenta nueva puede entrar con una **contraseña temporal**:
en cuanto entra, la app le pide cambiarla y no deja usar nada más hasta hacerlo. Cualquiera puede cambiar la suya en
**Configuración → Cambiar contraseña**.

Para crear una cuenta con contraseña temporal sin tocar la base de datos, se deja `datos/cuentas_nuevas.json`:
```json
[{"usuario": "esbeidy", "nombre": "Esbeidy Caro", "password_temporal": "..."}]
```
Al arrancar `iniciar.bat` se crea la cuenta y **el archivo se borra solo** (la contraseña no se queda escrita).

## Material
Lo que preparan los agentes (5 imágenes de difusión y 5 reels) aparece en **Material**. Ahí puedes:
- **Ver guion en Prompter** (pantalla completa para leer durante la grabación).
- **Editar el texto** de cada pieza (máximo 2,200 caracteres) y **descargar** sus archivos.
- **Recortar** un reel (inicio y fin).
- **Vaciar Material** para empezar de cero: escribe `BORRAR` para confirmar. Borra imágenes y reels;
  los videos de `grabaciones/` no se tocan.

Si los dos editan la misma pieza a la vez, el segundo ve "Otra persona cambió este paquete" en lugar de pisar el cambio.

## Reels: cómo elige los 5 momentos
Todo se hace en tu PC, sin pagar ninguna API:
1. Whisper escribe lo que se dijo, con el segundo exacto de cada frase.
2. Busca frases clave: «primer… quinto misterio» (vale más), «intenciones», oraciones y el cierre.
3. Arma tramos que empiezan al inicio de una frase y terminan al final de otra, castigando los silencios.
4. Elige 5 sin encimarse y **cada uno se edita con la receta del cliente** (`estilo_cliente/estilo.json`):
   mejora de luz, enfoque y ruido, sus capas y animaciones, subtítulos, intro, cierre y música.

Si una grabación falla, se ve en «Grabaciones recientes». Para intentarlo otra vez:
`flask --app app reels-reintentar nombre-del-archivo.mp4`

## Equipo
En **Configuración → Equipo** agrega a cada integrante (nombre y correo; de preferencia Gmail). Reciben por
correo el aviso del tema. Cada uno se puede **Modificar**, **Pausar** (no recibe correos) o **Borrar**.

## Reloj
`http://localhost:5021/reloj` muestra la hora de la CDMX y la cuenta regresiva en grande. En StreamYard
abre el reloj en una ventana y compártela. No pide contraseña porque no muestra ningún dato privado.

## Conectar Gmail (aviso del tema al equipo), una sola vez
1. Entra a https://console.cloud.google.com, crea un proyecto y activa **Gmail API**.
2. En «Pantalla de consentimiento de OAuth» elige *Externo* y agrega tu correo como usuario de prueba.
3. En «Credenciales» → *Crear credenciales* → *ID de cliente de OAuth* → **App de escritorio**.
   Descarga el JSON y guárdalo como `secretos/client_secret.json`.
4. En la PC del sistema: `flask --app app google-autorizar` y acepta el permiso de enviar correo.

## Variables de entorno (.env)
| Variable | Para qué sirve | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Firma las sesiones. Obligatoria. | 64 caracteres hex |
| `COOKIE_SECURE` | Cookie solo por conexión segura | `1` |
| `SESION_HORAS` | Duración de la sesión | `8` |
| `MAX_USUARIOS` | Máximo de cuentas (Gonza + Esbeidy) | `2` |
| `HOST` / `PORT` | Dónde escucha el servidor | `127.0.0.1` / `5021` |
| `TAILSCALE` | Esbeidy entra por `tailscale serve` | `1` |
| `CANAL_NOMBRE` | Nombre en imágenes y reels | `Cristocéntricos` |
| `CANAL_ENLACE` | Enlace del canal (opcional) en el carrusel | `youtube.com/@...` |
| `WHISPER_MODELO` | Modelo de transcripción | `small` |
| `DIFUSION_AL_GUARDAR` | Las 5 imágenes salen al guardar el tema | `1` |
| `ESTILO_DIR` | Carpeta del estilo del cliente (vacío = `estilo_cliente/`) | — |
| `MODO` | `local` (laptop, hace todo) o `nube` (Railway, solo vigila) | `local` |
| `DATABASE_URL` | Vacío = SQLite; con Railway, la URL pública de su PostgreSQL | — |

## Comandos útiles
```powershell
flask --app app crear-usuario
flask --app app cambiar-password gonza
flask --app app carrusel 2026-10-23 [--forzar]   # las 5 imágenes de difusión de ese día
flask --app app material-vaciar --si             # vacía la pestaña Material
flask --app app reels-reintentar evento.mp4
flask --app app estilo-analizar                  # mide el video de referencia del cliente
flask --app app estilo-probar grabaciones/celular.mp4 --inicio 120 --fin 165
flask --app app google-autorizar
python -m agentes.worker       # la ventana de agentes, a mano
pytest                 # pruebas
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
- Contraseña temporal: la cuenta nueva no puede usar nada hasta cambiarla.
- **Nada se publica solo**: el material se descarga desde la pestaña Material.
- Si los dos editan a la vez la misma pieza, el segundo recibe un aviso.
- El token de Google solo en `secretos/` y los secretos en `.env` (ambos fuera de git).
- Las vistas previas solo entregan archivos declarados del paquete, dentro de `paquetes/`.

## Publicación (Railway + laptop)
La nube (Railway, `MODO=nube`) sirve para vigilar el avance y llevar el orden semanal desde cualquier
lugar; la grabación (paso 5) y los reels (paso 6) se hacen en la laptop, que comparte la base
PostgreSQL de Railway. Los videos nunca suben a internet. Pasos y detalle: [docs/railway.md](docs/railway.md).

## Privacidad (LFPDPPP)
El equipo guarda nombre y correo de los integrantes, solo para mandarles el aviso del tema. Gonza pidió quitar la casilla del aviso de privacidad (2026-10-17): se informa de palabra.
«Borrar» borra su nombre y su correo (derecho de cancelación).

## Licencias de las fuentes
Spectral, Public Sans y JetBrains Mono (`assets/fuentes/`) son libres (SIL Open Font License);
las licencias están junto a los archivos.
