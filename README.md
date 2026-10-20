# Cristocéntricos Automático · versión corta (v2.0)

Convierte cada evento en vivo (lunes y viernes, 10 a 11 am) en **5 imágenes de difusión** y **5 reels
editados con el estilo que pide el cliente**. Corre en la PC de Gonza.

**Versión corta (2026-10-19):** el proceso de cada evento son 7 pasos. Turnos, bandeja de aprobación,
publicación automática, reporte semanal y estadísticas quedan **ocultos** (el código sigue ahí;
`VERSION_CORTA=0` los regresa). Lo que había hasta esta fecha está en `versiones/Cristocentricos v.1.0.zip`.

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
   (OBS ya no se usa.)
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
flask --app app crear-usuario      # la del aprobador

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

## OBS (solo versión 1.0: en la versión corta ya no se usa)
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

## Estadísticas
Pestaña **Estadísticas** (en celular, «Datos»): eliges el periodo (último mes, 3 o 6 meses, este año, 12 meses
o fechas a mano) y ves gráficas interactivas: avance de cada evento (clic = ficha del evento), piezas por
evento, estado de las piezas, cómo se cumple cada paso, publicaciones por red, seguidores e ideas por semana.
Pasa el mouse para ver el detalle y usa la leyenda para prender o apagar series. Solo cuentan los eventos que
se trabajaron en la app (y los de hoy en adelante). Datos: `GET /api/estadisticas?desde=&hasta=` (hasta 2 años).

## Eventos pasados y bitácora
Inicio solo muestra el proceso del evento de hoy y de los próximos. Cada hora, los eventos que ya pasaron
(y que se trabajaron) se guardan en la bitácora: tema, pasos hechos, video, reels, aprobados y
publicaciones por red. Se descarga para Excel desde el reporte semanal: **Bitácora de eventos (Excel)**.

## Equipo y turnos
En **Ajustes → Equipo** agrega a cada integrante (nombre y correo; de preferencia Gmail). Cada uno
se puede **Modificar**, **Pausar** (no recibe turnos, invitaciones ni correos: sirve para hacer pruebas
sin molestar a nadie) o **Borrar**. Los domingos a las 6 pm se
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
flask --app app estilo-analizar   # mide el video de referencia del cliente
flask --app app estilo-probar grabaciones/celular.mp4 --inicio 120 --fin 165
flask --app app repartir       # turnos vacíos de las próximas 2 semanas (versión 1.0)
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
invitaciones. Gonza pidió quitar la casilla del aviso de privacidad (2026-10-17): se informa de palabra.
«Borrar» borra su nombre y su correo (derecho de cancelación) y sus turnos futuros.

## Licencias de las fuentes
Spectral, Public Sans y JetBrains Mono (`assets/fuentes/`) son libres (SIL Open Font License);
las licencias están junto a los archivos.
