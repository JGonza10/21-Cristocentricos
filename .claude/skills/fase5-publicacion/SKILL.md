---
name: fase5-publicacion
description: Plano de la fase 5 de Cristocéntricos — el agente de publicación que arma paquetes `paquetes/<fecha>/subir_manual/<red>/` solo con contenido aprobado y sube a YouTube en privado. Úsala SIEMPRE que se programe, pruebe o cambie `agentes/publicacion.py`, los paquetes por red, el manifiesto, el estado "publicado" o la pantalla que dispara la publicación.
---

# Fase 5 — Agente de publicación

Objetivo: convertir lo **aprobado** en la bandeja en paquetes listos para subir a mano
(Instagram, Facebook, TikTok, TV) y en una subida **privada** a YouTube. Nada más.

## Reglas que no se negocian
1. **Solo aprobado.** El agente lee de la BD los elementos con `estado == "aprobado"`.
   Nunca acepta rutas ni ids "sueltos" desde un formulario sin volver a consultar su estado.
2. **Idempotente.** Correr el agente 2 veces no duplica nada: cada elemento guarda
   `publicado_en` y el hash del paquete. Si ya existe y el hash coincide → no hace nada.
3. **Escritura atómica.** Se arma en `paquetes/<fecha>/.tmp-<uuid>/` y al final se hace
   `os.replace` a `subir_manual/`. Si falla a la mitad, no queda un paquete a medias.
4. **Rutas seguras.** Toda ruta se resuelve con `Path.resolve()` y se comprueba que siga
   dentro de `RAIZ / "paquetes"` (`ruta.is_relative_to(base)`). Nombres de archivo con
   `slug` propio (a-z, 0-9, guion), nunca el nombre que venga del usuario.
5. **Bitácora.** Cada acción queda en una tabla `Bitacora` (quién aprobó, cuándo se empaquetó,
   id de YouTube). Así se responde "¿quién publicó esto?" sin adivinar.
6. **Antes de entregar**, correr la habilidad `guardia-publicacion` sobre el paquete.

## Estructura del paquete
```
paquetes/2026-10-19/
├─ manifiesto.json            # lista de archivos + sha256 + id de aprobación
└─ subir_manual/
   ├─ instagram/  reel-1.mp4 reel-2.mp4 reel-3.mp4 carrusel-01.png … carrusel-05.png texto.txt
   ├─ facebook/   (igual que instagram)
   ├─ tiktok/     reel-1.mp4 … texto.txt          # TikTok: solo video
   ├─ youtube/    reel-1.mp4 … texto.txt          # respaldo si la API falla
   └─ tv/         reel-*.mp4 texto.txt            # para StreamYard
```
`texto.txt` lleva un bloque por pieza (`=== reel-1 ===` …) con el texto ya adaptado por
`textos-por-red`. Codificación **UTF-8 con BOM** para que el Bloc de notas de Windows
muestre bien acentos y emojis.

## Modelo sugerido (añadir a `app/modelos.py`)
```python
class Publicacion(db.Model):
    __tablename__ = "publicaciones"
    id = db.Column(db.Integer, primary_key=True)
    contenido_id = db.Column(db.Integer, db.ForeignKey("contenidos.id"), nullable=False, index=True)
    red = db.Column(db.String(20), nullable=False)          # instagram|facebook|tiktok|youtube|tv
    estado = db.Column(db.String(20), nullable=False, default="empaquetado")  # empaquetado|subido|error
    ruta = db.Column(db.String(300))
    sha256 = db.Column(db.String(64))
    externo_id = db.Column(db.String(40))                   # id de video de YouTube
    error = db.Column(db.String(300))                       # mensaje corto, detalle en el log
    creado = db.Column(db.DateTime, default=ahora, nullable=False)
    __table_args__ = (db.UniqueConstraint("contenido_id", "red"),)
```
La restricción única `(contenido_id, red)` es la que garantiza la idempotencia a nivel BD.

## Flujo del agente (`agentes/publicacion.py`)
1. `pendientes = Contenido.query.filter_by(estado="aprobado")` sin `Publicacion` en esa red.
2. Por cada red: copiar archivos → escribir `texto.txt` → calcular sha256 → `os.replace`.
3. YouTube: delegar a `servicios/youtube.py` (habilidad `youtube-privado`). Si falla,
   el paquete `youtube/` queda como respaldo y la fila se marca `error`, no se reintenta en bucle.
4. Escribir `manifiesto.json` y la bitácora. Avisar en la bandeja (estado verde "Listo para subir").

## API (Flask) — todo con `@login_requerido` y CSRF
| Ruta | Qué hace |
|---|---|
| `POST /api/publicacion/<fecha>` | Arma el paquete de esa fecha (solo aprobados) |
| `GET  /api/publicacion/<fecha>` | Estado por red: empaquetado / subido / error |
| `POST /api/publicacion/<id>/marcar-subido` | Gonza confirma que ya lo subió a mano |

Validar `<fecha>` con `date.fromisoformat` (rechaza `../`). Respuestas de error amables (§5).

## Pruebas mínimas (`tests/test_publicacion.py`)
- Un elemento **pendiente** o **rechazado** nunca aparece en `subir_manual/`.
- Correr dos veces da el mismo `manifiesto.json` y no duplica filas.
- Un nombre malicioso (`../../secretos/x`) no escapa de `paquetes/`.
- `texto.txt` respeta los límites por red (usa `textos-por-red`).
- Sin sesión → 401; sin CSRF → 400.
- YouTube simulado (`monkeypatch`) siempre recibe `privacyStatus="private"`.
Usa `tmp_path` para `paquetes/`; nunca toques la carpeta real en pruebas.

## Al cerrar la fase
`pytest -q`, `pip-audit`, `npm audit`, actualizar el **Estado** en `CLAUDE.md` §8 y el README
(nueva sección "Publicar"). Entregar archivos completos.
