# Cristocéntricos en Railway (nube) + laptop

Desde el 2026-10-21 la app tiene dos partes que comparten **una sola base PostgreSQL en Railway**:

| | Nube (Railway, `MODO=nube`) | Laptop (`MODO=local`) |
|---|---|---|
| Para qué | Vigilar que todo se cumpla y llevar el orden semanal, desde cualquier lugar | Hacer el trabajo pesado |
| Pasos | 1 tema · 2 guion · 4 revisión técnica · 7 ideas (texto) · ver el avance de los 7 | 3 imágenes · **5 grabación** · **6 reels** · ideas por voz · correos |
| Archivos | Ninguno (no se suben videos a internet) | `grabaciones/`, `paquetes/`, `estilo_cliente/` |
| Worker | No corre | `python -m agentes.worker` (o `iniciar.bat`) |

Cómo se conectan: el worker de la laptop lee y escribe en la base de Railway. Cuando guardas un tema
en la nube, la laptop arma las 5 imágenes en ≤ 2 min; cuando llega el video a `grabaciones/`, la laptop
edita los reels y la nube ve los pasos 5 y 6 en «Hecho». Cada 5 min la laptop reporta su estado
(estilo del cliente, Gmail); Inicio en la nube muestra si el worker está prendido.

En la nube, Material muestra cada pieza y su texto, pero los archivos se descargan desde la laptop.

## Publicar (una sola vez)

1. En Railway: **New project → Deploy from GitHub repo** → `JGonza10/21-Cristocentricos`.
   Railway usa el `Dockerfile` y `railway.json` (healthcheck en `/api/salud`).
2. En el proyecto: **+ New → Database → PostgreSQL**.
3. En el servicio web, **Variables**:
   - `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`
   - `SECRET_KEY` = una nueva: `python -c "import secrets; print(secrets.token_hex(32))"`
   - `MODO=nube` (ya viene en el Dockerfile), `COOKIE_SECURE=1`, `MAX_USUARIOS=2`
   - Opcionales: `CANAL_NOMBRE`, `SESION_HORAS`
4. **Settings → Networking → Generate domain** (p. ej. `cristocentricos.up.railway.app`).
5. Copiar los datos de la laptop a Railway (desde la carpeta del proyecto, en la laptop):
   ```powershell
   $env:DESTINO_URL = "<DATABASE_PUBLIC_URL del Postgres de Railway>"
   .venv\Scripts\python.exe -m flask --app app copiar-base
   Remove-Item Env:DESTINO_URL
   ```
   Copia cuentas (solo hashes), temas, avance, Material, equipo e ideas. Si la base destino ya tiene
   datos, no toca nada.
6. En el `.env` de la laptop agregar `DATABASE_URL=<DATABASE_PUBLIC_URL>` (queda fuera de git) y
   reiniciar `iniciar.bat`. Desde ese momento la laptop y la nube ven lo mismo. Guardar
   `datos/cristocentricos.db` como respaldo (ya no se usa).

## Uso diario

- Desde cualquier lugar: abrir el dominio de Railway e iniciar sesión.
- En la laptop: `iniciar.bat` antes de cada evento (worker + app local para descargar Material).
- Tailscale ya no hace falta para Esbeidy; la nube la reemplaza.

## Notas

- Sin internet, la laptop no llega a la base: los videos esperan en `grabaciones/` y se procesan
  cuando vuelve la conexión.
- Costo: Railway cobra por uso (servicio web + Postgres, plan Hobby).
- Seguridad: login con bcrypt y límite de intentos (con la IP real gracias a ProxyFix), CSRF,
  cookie segura y CSP. En la nube no hay rutas que acepten videos, audio ni imágenes.
