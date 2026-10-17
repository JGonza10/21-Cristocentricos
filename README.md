# Cristocéntricos Automático

Convierte cada evento en vivo (lunes y viernes, 10 a 11 am) en reels y un carrusel de
invitación, con una bandeja donde todo se aprueba antes de publicarse. Corre en la PC de Gonza.

**Estado:** las 8 fases del plan están programadas y probadas (ver `CLAUDE.md`). Falta conectarlas
con tus cuentas reales: Google (YouTube y Calendar) y, si quieres, Meta.

| Qué hace | Cuándo |
|---|---|
| Carrusel de invitación (5 imágenes + texto) | Solo, 2 días antes de cada lunes y viernes |
| 3 reels verticales con subtítulos | Solo, cuando llega la grabación a `grabaciones/` |
| Bandeja: aprobar, rechazar, editar texto, ajustar recorte | Cuando tú o el aprobador entran |
| Carpetas `subir_manual/<red>/` y subida a YouTube (privado) | Solo, en cuanto algo se aprueba |
| Reparto de turnos e invitaciones de Google Calendar | Domingos 6 pm (y botón «Repartir ahora») |
| Reloj CDMX con cuenta regresiva (tema perla), se abre en grande desde un enlace chico | Pestaña Evento → «Reloj» (`/reloj`) |
| Facebook e Instagram automáticos (opcional) | Si activas `META_AUTO=1` |

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
flask --app app crear-usuario      # la del aprobador

cd frontend
npm install
npm run build
cd ..
```

## Uso diario
Doble clic en `iniciar.bat`. Se abren **dos ventanas que no debes cerrar**:
1. **Servidor**: la página en http://localhost:5021.
2. **Agentes**: preparan carruseles, reels, publicaciones y turnos según su horario.

Si la ventana de agentes está cerrada, Inicio muestra «Agentes: Apagados».

### Flujo de cada evento (desde el 2026-10-17)
Cada evento (lunes y viernes, 10 a 11 am) tiene un **tema**. Inicio guía los 13 pasos en orden:
1. **Tema y guion**: en el calendario (o en la pestaña Evento) pones el tema con anticipación; lo
   ideal es tener siempre los próximos 2 eventos con tema. Al guardarlo, al equipo le llega un correo
   y se actualiza su invitación de Google Calendar. «Preparar guion con Claude» copia las
   instrucciones y abre Claude: pégalas, y el guion que te dé pégalo de vuelta y guarda.
2. **Turnos**: quién dirige y quién apoya.
3. **Difusión**: en cuanto hay tema (hasta 2 semanas antes) llegan a la bandeja un carrusel de 5
   imágenes y un reel promocional de 15 s (súbelo con un audio de moda en cada red).
4. **Revisión técnica**: la lista de audio, cámara, internet, StreamYard, OBS, guion y reloj.
5. **Transmisión** por StreamYard, como siempre. **OBS graba solo** de 9:55 a 11:05 (o con el botón
   «Empezar a grabar») y deja el video en `grabaciones/`.
6. Si se grabó en otra computadora: **«Subir grabación»** (por partes; se reanuda si se corta).
7. **5 reels** con mejora automática de luz, color y volumen, y un **carrusel con escenas** del video.
8. **Bandeja**: apruebas o rechazas. Lo aprobado se publica o queda en `subir_manual/<red>/`.
9. **Registro** automático (descárgalo para Excel desde el reporte) y **reporte semanal** los lunes.

**Ideas**: botón «Ideas» arriba a la derecha; se escriben o se graban por voz (Whisper las pasa a
texto en esta PC) y cualquiera se puede volver el tema de un evento.

## OBS (grabación automática)
Una sola vez en la PC donde corre la app (OBS ya instalado con `winget install OBSProject.OBSStudio`):
```powershell
.venv\Scripts\flask --app app obs-configurar
```
Activa el control de OBS con una contraseña nueva (queda en `.env` como `OBS_PASSWORD`). La app crea
la escena «Cristocéntricos» con la pantalla principal; el audio del escritorio y el micrófono son el
audio global de OBS. Con `OBS_AUTO=1` los días de evento abre OBS y graba solo. Transmite desde esa
misma PC para que la grabación caiga directo en `grabaciones/`.

## Dos computadoras
La app, los agentes, la base de datos y **todos los videos** viven en una sola PC (la "servidora").
La otra entra por Tailscale (sección siguiente): ve y aprueba todo, sube grabaciones y captura ideas;
los videos nunca suben a la nube.

## Acceso del aprobador desde otra computadora (Tailscale)
Tailscale crea una red privada y cifrada entre tu PC y la del aprobador. La app **no** queda en
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
   al correo del aprobador. Así solo ve esa computadora, nada más de tu red.

**En la PC del aprobador:**
1. Instala Tailscale, inicia sesión con su correo y acepta la invitación.
2. Abre `https://pc-gonza.algo.ts.net` y entra con su usuario de la app.

**Importante:** tu PC debe estar encendida y con `iniciar.bat` abierto para que el aprobador entre.

## Desarrollo
```powershell
# Ventana 1: API
flask --app app run --debug --port 5021
# Ventana 2: interfaz con recarga automática
cd frontend; npm run dev          # abre http://localhost:5173
```

## Bandeja de aprobación (pestaña Contenido)
Todo lo que preparan los agentes entra como **pendiente**. Desde ahí cualquiera de los dos puede:
- **Editar el texto** (máximo 2,200 caracteres, el límite de Instagram) y guardarlo.
- **Aprobar**: solo lo aprobado lo tomará el agente de publicación (fase 5).
- **Rechazar**, con un motivo opcional.
- **Regresar a pendientes** algo ya aprobado o rechazado, para corregirlo.

Si los dos tienen la bandeja abierta y actúan sobre el mismo paquete, el segundo ve el aviso
"Otra persona cambió este paquete" y la versión nueva, en lugar de pisar el cambio del primero.
Cada acción queda en el historial (quién, qué y cuándo).

Para probarla sin esperar a los agentes:
```powershell
flask --app app carrusel 2026-10-19   # genera ya el carrusel de ese lunes
flask --app app paquete-demo          # paquetes de ejemplo (solo texto)
```

## Reels: cómo elige los 3 momentos
Todo se hace en tu PC, sin pagar ninguna API:
1. Whisper escribe lo que se dijo, con el segundo exacto de cada frase.
2. Busca frases clave: «primer… quinto misterio» (vale más), «intenciones», oraciones y el cierre.
3. Arma tramos de 30 a 55 s que empiezan al inicio de una frase y terminan al final de otra.
4. Castiga los silencios (`silencedetect` de ffmpeg) y elige 3 sin encimarse, uno por tercio del evento.
5. ffmpeg lo pasa a vertical 1080×1920: el video al centro sobre su propio fondo difuminado,
   subtítulos y el nombre del canal.

Si una grabación falla, se ve en «Grabaciones recientes». Para intentarlo otra vez:
`flask --app app reels-reintentar nombre-del-archivo.mkv`

## Equipo y turnos
En **Ajustes → Equipo** agrega a cada integrante (nombre y correo; de preferencia Gmail). Antes de
guardarlo hay que confirmar que se le informó el aviso de privacidad. Los domingos a las 6 pm se
reparten solos los lugares vacíos de la semana: le toca a quien lleva menos turnos en los últimos 90
días. En la pestaña **Evento** puedes cambiar a mano quién dirige y quién apoya.

## Reloj en vivo y overlay
Casi no se usa, así que en la pestaña **Evento** solo hay un enlace chico «Reloj» que lo abre en
grande en otra ventana: hora de la CDMX y cuenta regresiva, en tema perla. La dirección es
`http://localhost:5021/reloj`:
- **OBS**: Fuentes → + → Navegador → pega la dirección, 1920×1080.
- **StreamYard**: abre el reloj en una ventana y compártela.

El overlay no pide contraseña porque no muestra ningún dato privado, solo la hora.

## Conectar Google (YouTube, Calendar y Gmail), una sola vez
1. Entra a https://console.cloud.google.com, crea un proyecto y activa **YouTube Data API v3**,
   **Google Calendar API** y **Gmail API** (Gmail manda el aviso del tema al equipo).
2. En «Pantalla de consentimiento de OAuth» elige *Externo* y agrega tu correo como usuario de prueba.
3. En «Credenciales» → *Crear credenciales* → *ID de cliente de OAuth* → **App de escritorio**.
   Descarga el JSON y guárdalo como `secretos/client_secret.json`.
4. En la PC del sistema:
   ```powershell
   flask --app app google-autorizar
   ```
   Se abre el navegador; acepta los permisos. Se crea `secretos/token_google.json`.
5. Listo: Inicio mostrará «Google Calendar conectado».

**Importante:** mientras Google no verifique la app, los videos se suben en **privado** (así lo
pide Google para apps sin verificar). Revísalo en YouTube Studio y cámbialo a público tú.

## Publicación automática en Meta (opcional, fase 8)
Por defecto Facebook e Instagram son manuales (carpetas en `subir_manual/`). Para automatizar:
1. Crea una app en https://developers.facebook.com y conecta tu página de Facebook y tu cuenta
   profesional de Instagram.
2. Saca un **token de página de larga duración** con los permisos `pages_manage_posts`,
   `pages_read_engagement`, `instagram_basic` e `instagram_content_publish`.
3. En el `.env`: `META_AUTO=1`, `META_PAGE_ID`, `META_IG_USER_ID` y `META_TOKEN`.

Qué se publica solo: el carrusel y el reel en Facebook, y el reel en Instagram. **El carrusel de
Instagram sigue siendo manual**, porque la API de Instagram pide que cada imagen esté en una dirección
pública de internet, y esta app vive solo en tu PC.

Esta parte está probada con respuestas simuladas, no contra Meta real. La primera vez revisa que
el post haya salido bien. Si algo falla, el paquete queda «Con error» y la carpeta para subir a
mano se prepara sola.

## Variables de entorno (.env)
| Variable | Para qué sirve | Ejemplo |
|---|---|---|
| `SECRET_KEY` | Firma las sesiones. Obligatoria. | 64 caracteres hex |
| `COOKIE_SECURE` | Cookie solo por conexión segura | `1` |
| `SESION_HORAS` | Duración de la sesión | `8` |
| `MAX_USUARIOS` | Máximo de cuentas | `2` |
| `HOST` / `PORT` | Dónde escucha el servidor | `127.0.0.1` / `5021` |
| `TAILSCALE` | El aprobador entra por `tailscale serve` | `1` |
| `CANAL_NOMBRE` | Nombre en carruseles, reels y overlay | `Cristocéntricos` |
| `CANAL_ENLACE` | Enlace del canal (opcional) en el carrusel | `youtube.com/@...` |
| `WHISPER_MODELO` | Modelo de transcripción | `small` |
| `APOYOS_POR_EVENTO` | Cuántos apoyan además de quien dirige | `1` |
| `GOOGLE_CALENDAR_ID` | Calendario de las invitaciones | `primary` |
| `META_AUTO` | Publicación automática en Meta | `0` |
| `META_PAGE_ID` / `META_IG_USER_ID` | IDs de la página y de Instagram | números |
| `META_TOKEN` | Token de página (secreto) | — |

## Comandos útiles
```powershell
flask --app app crear-usuario
flask --app app cambiar-password gonza
flask --app app paquete-demo   # paquetes de ejemplo en la bandeja
flask --app app carrusel 2026-10-19 [--forzar]
flask --app app reels-reintentar evento.mkv
flask --app app repartir       # turnos vacíos de las próximas 2 semanas
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
- **Nada se publica sin aprobación**: el agente de publicación vuelve a revisar el estado justo
  antes de subir. Lo ya publicado no se puede regresar a pendientes.
- Si los dos aprobadores actúan a la vez sobre el mismo paquete, el segundo recibe un aviso.
- Tokens de Google y Meta solo en `secretos/` y `.env` (ambos fuera de git).
- Las vistas previas solo entregan archivos declarados del paquete, dentro de `paquetes/`.

## Publicación
No se publica en internet: es una app local. Si algún día se sube a Railway, cambiar SQLite
por PostgreSQL y revisar el checklist de seguridad con Claude antes.

## Privacidad (LFPDPPP)
El calendario del equipo guarda nombre y correo de los integrantes, solo para asignar turnos y mandar
invitaciones. Al agregar a alguien se confirma que se le informó el aviso de privacidad (queda la
fecha). «Dar de baja» borra su nombre y su correo (derecho de cancelación) y sus turnos futuros.

## Licencias de las fuentes
Spectral, Public Sans y JetBrains Mono (`assets/fuentes/`) son libres (SIL Open Font License);
las licencias están junto a los archivos.
