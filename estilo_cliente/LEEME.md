# Estilo del cliente

Aquí vive todo lo que hace falta para que los 5 reels de cada evento queden **exactamente como los
pide el cliente**. El agente de reels lo lee solo cada vez que llega un video a `grabaciones/`.

```
estilo_cliente/
  referencia/     ← el video que entregó el cliente como muestra de la edición
  herramientas/   ← sus imágenes (PNG con fondo transparente), animaciones (MOV/WEBM con transparencia,
                    GIF, o MP4 con fondo verde), intro, cierre, música y fuentes (.ttf)
  estilo.json     ← la receta: qué herramienta va, dónde, en qué segundo, y cómo se mejora el video
  analisis/       ← lo genera «estilo-analizar» (cuadros y medidas de la referencia)
  pruebas/        ← reels de prueba de «estilo-probar»
```

## De dónde sale cada reel

1. El **video limpio del celular** (sin cintillas) se copia a `grabaciones/` (o se sube con
   «Subir video del celular» en Inicio). Si llega de otro lado, igual: lo que caiga en `grabaciones/` se edita.
2. Whisper lo escucha en esta PC y el sistema elige **5 momentos** (el largo lo marca `estilo.json → duracion`).
3. Cada momento se edita con la receta: mejora de luz y enfoque, quita ruido exterior, encuadre vertical,
   capas del cliente, textos, subtítulos, música, intro y cierre.
4. Los reels quedan en la pestaña **Material**, listos para descargar.

## Pasos para dejarlo igual a la referencia

1. Pon el video del cliente en `referencia/` y sus imágenes y animaciones en `herramientas/`.
2. En PowerShell, dentro de la carpeta del proyecto:
   ```powershell
   .venv\Scripts\flask --app app estilo-analizar
   ```
   Saca `analisis/<video>/hoja.jpg` (todos los cuadros juntos, con su segundo) y `datos.json`
   (tamaño, cortes, brillo, color y volumen de la referencia).
3. Con eso se ajusta `estilo.json` (Claude lo puede hacer: pídele «ajusta estilo.json a la referencia»).
4. Prueba sin tocar la base de datos:
   ```powershell
   .venv\Scripts\flask --app app estilo-probar grabaciones\celular.mp4 --inicio 120 --fin 165 --tema "La Santa Faz"
   ```
   El reel queda en `pruebas/`. Compáralo con la referencia y repite el paso 3 hasta que quede igual.

## La receta (estilo.json)

En el archivo real no van los comentarios `//` (aquí solo explican cada campo).
Los tiempos `desde` / `hasta` son segundos del reel (sin contar la intro). Un número negativo cuenta desde
el final (`"desde": -3` = los últimos 3 segundos) y `"hasta": null` = hasta el final. Las posiciones `x`, `y`
son píxeles del cuadro de 1080×1920 (esquina superior izquierda), o `"centro"`.

```jsonc
{
  "activo": true,                       // false = se usa el look de la versión 1.0
  "formato": {"ancho": 1080, "alto": 1920, "fps": 30,
              "encuadre": "llenar",     // llenar (recorta) · fondo_difuminado · ajustar (barras)
              "foco_y": 0.35},          // con "llenar": 0 = conserva arriba, 0.5 = centro
  "duracion": {"min": 30, "max": 55, "ideal": 45},
  "mejora": {"luz": true, "contraste": 1.05, "saturacion": 1.06, "gamma": 1.0,
             "nitidez": 0.6,            // enfoque (0 = nada, 1 = mucho)
             "quitar_grano": true,      // ruido de imagen con poca luz
             "quitar_ruido": true,      // ruido exterior: zumbidos, aire, ventiladores
             "volumen_lufs": -14},      // volumen parejo para redes
  "intro":  {"archivo": "intro.mp4"},   // o una imagen: {"archivo": "portada.png", "segundos": 2}; null = sin intro
  "cierre": {"archivo": "cierre.mp4"},
  "capas": [
    {"archivo": "logo.png", "x": 40, "y": 60, "ancho": 220, "desde": 0, "hasta": null, "fundido": 0.4},
    {"archivo": "cintilla.mov", "x": 0, "y": 1500, "desde": 2, "hasta": 8},
    {"archivo": "brillo.mp4", "x": "centro", "y": "centro", "croma": "#00FF00", "repetir": true, "opacidad": 0.8}
  ],
  "textos": [
    {"texto": "{tema}", "fuente": "Spectral_700Bold.ttf", "tamano": 62, "color": "#7A1C2E",
     "fondo": "#FFFFFFEE", "x": "centro", "y": 1600, "desde": 0, "hasta": 3.2, "ancho_max": 900}
  ],
  "subtitulos": {"activo": true, "fuente": "PublicSans_800ExtraBold.ttf", "tamano": 50, "color": "#FFFFFF",
                 "fondo": "#7A1C2EE0", "y": 1600, "caracteres_por_renglon": 24, "mayusculas": false},
  "musica": {"archivo": "fondo.mp3", "volumen": 0.12},
  "fundido": 0.25
}
```

### Lo que se agregó para copiar la edición del cliente

| Opción | Qué hace | Ejemplo |
|---|---|---|
| `"quitar_pausas"` | Corta los silencios largos (como hace el cliente) | `{"activo": true, "minimo": 0.6, "margen": 0.15}` |
| capa `"archivo": "temas/{fecha_iso}"` + `"opcional": true` | La **imagen del tema** de cada evento (se sube en el tema del evento, en la app) | el Santo Rostro |
| capa `"ajuste": "cubrir"` | Llena el recuadro `ancho`×`alto` sin deformar | |
| texto `"efecto": "maquina"` | Las letras aparecen una a una, ya en su lugar | `"letras_por_segundo": 15` |
| subtítulos `"efecto": "palabras"` | Las palabras aparecen conforme se dicen | |
| `"sombra": true` | Sombra suave detrás del texto | `"color_sombra": "#000000C8"` |
| `"ancla": "arriba"` | `y` marca dónde empieza el primer renglón | |
| `"corte": "abajo_largo"` | Título en 2 renglones con el de abajo más largo | |
| cierre `"segundos"` | Usa solo los primeros segundos de la animación de cierre | `4.6` |
| `"negro_final"` | Fundido a negro al final | `0.4` |
| `"transiciones"` | Cortes que no se notan: agrega cuadros intermedios donde se quitó una pausa. `morph` mueve la imagen poco a poco de una toma a la otra (flujo óptico); `disolver` las mezcla; `corte` = corte seco | `{"tipo": "morph", "duracion": 0.27}` |
| cierre `"audio"` + `"ganancia_db"` | Música propia del cierre (la animación no trae audio) | `"musica_cierre_virgen.m4a"`, `11` |

- **Datos para los textos:** `{tema}`, `{fecha}` (texto: «Viernes 23 de octubre»), `{fecha_iso}` (2026-10-23),
  `{canal}` y `{frase}` (lo que se dice en ese reel).
- **Colores:** `#RRGGBB` o `#RRGGBBAA` (las dos últimas letras = transparencia).
- **Fuentes:** primero se buscan en `herramientas/`, luego en `assets/fuentes/` (incluye Fraunces y Open Sans,
  las que más se parecen a las del cliente).
- **Animaciones con fondo verde o negro:** pon `"croma": "#00FF00"` (o el color del fondo) y se vuelve transparente.
- Si `estilo.json` tiene un error o falta una herramienta, la grabación queda «Con error» y el mensaje dice cuál.

## La receta actual (19 de octubre de 2026)

Sale de `referencia/Cristocentricos_V0001.mp4`, que es la edición del cliente del video limpio
`Cristocentricos_V0007.mp4`. Se midió cuadro por cuadro y se pasó de 576×1024 a 1080×1920:

- Video a pantalla completa, sin pausas largas, con mejora de luz, enfoque y audio.
- Logo `IMG_4620.PNG` arriba a la derecha (aparece con un fundido de 0.9 s).
- **Imagen del tema** al centro (582×866 px). Se sube en la app, en el tema de cada evento; si no hay, no sale.
- Título = el tema, en Fraunces, color crema con sombra y efecto máquina de escribir durante los primeros 5.6 s.
- Subtítulos cortos en Open Sans, crema con sombra, palabra por palabra.
- Cierre: los primeros 4.6 s de `Cristocentricos_Virgen_de_Fatima_caminando_v9.MP4` con **su música**
  (`musica_cierre_virgen.m4a`, sacada de la referencia del segundo 51.03 al final, +11 dB para que guarde con
  la voz la misma proporción que en el video del cliente) y fundido a negro.
- Cortes suaves: en cada pausa quitada se agregan 8 cuadros intermedios (0.27 s) con «morph»; el audio de ese
  momento es el de la pausa real (ambiente), así no se oye el brinco.

Esta carpeta (salvo este archivo y `estilo.json`) no se sube a GitHub: el material del cliente es privado.
