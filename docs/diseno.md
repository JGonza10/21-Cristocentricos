# Diseño

Fuente única: `frontend/src/styles/tokens.css`. Nunca colores sueltos en componentes.
Concepto: panel lavanda claro; el morado es el único color de acción; la pestaña activa lleva el degradado lila → rosa.

## Tipografía
- Todo: **Public Sans** 400/600/700/800 (`--f-body`); títulos en 800.
- Números y reloj: **JetBrains Mono** 500/700 (`--f-mono`).

## Colores — claro
```css
--bg:#f9f7fc; --surface:#ffffff; --surface-2:#faf8fd;
--ink:#241b31; --ink-2:#554767; --muted:#72677e; --muted-2:#81778b; --line:#e7e0ef;
--accent:#7d45cb; --accent-strong:#65409a; --accent-soft:#f0e8fc; --on-accent:#ffffff;
--grad-tab:linear-gradient(90deg,#a56be5,#cd76dd);
--grad-hero:linear-gradient(135deg,#faf7ff,#efeafe 55%,#e9e9ff);
--ok:#2b7a4b; --ok-soft:#e1f1e7; --warn:#8a5d00; --warn-soft:#fbf0d3; --off:#a39bab;
```

## Colores — Oro (antes "Oscuro", 2026-10-20)
Colores de Kestrel (azul noche) con el oro del logo en lugar del naranja. Fuente única: `frontend/src/styles/tokens.css`.
```css
--bg:#05080e; --surface:#0c1420; --surface-2:#111b29; --line:#1f2b3c;
--ink:#e6edf6; --muted:#8c9db2;
--accent:#e2b25c; --accent-strong:#f2cd85; --on-accent:#05080e;   /* oro */
--grad-tab: oro #9c6b24 → #e9c27a → #a8772b (la pestaña activa lleva letra oscura)
--grad-titulo: degradado dorado en el título del anuncio, con Cormorant Garamond (la serif del logo)
--filete: línea dorada bajo el menú · --brillo: halo dorado en lo activo
```
Se aplica con `@media (prefers-color-scheme:dark){:root:not([data-theme="light"])}` y `:root[data-theme="dark"]`.
Colores de los 7 pasos en el diagrama y las tarjetas: `--p1` … `--p7` (cada paso su contorno).

## Imágenes para redes
Blanco y vino: `#ffffff`, `#fbf9f7`, vino `#7a1c2e`, vino suave `#f3e4e7`, texto `#3a1420`, oro `#8f6b10`. Títulos en **Spectral** 700, texto Public Sans (TTF en `assets/fuentes/`). Carrusel 1080×1350.

## Significado
Morado = acciones · degradado = pestaña activa y sello del login · verde = funcionando · ámbar = falta algo · gris = inactivo.
En gráficas: paleta viva con degradados, nada de café o mostaza oscura.

## Componentes
- Botones de color **solo de contorno** (regla de Gonza): primario con borde `--accent`, suave con borde `--line`; radio 12 px, alto ≥ 44 px.
- Tarjeta `--surface`, borde `--line`, radio 20 px, padding 22 px (18 en celular).
- Fila: `--surface-2`, radio 14 px; la de hoy con barra morada a la izquierda.
- Ancho máximo 940 px, margen 16 px, cuerpo 16 px/1.55.

## Pantallas
Cabecera fija con el logo (selector Claro/Oro, Diagrama, Salir) · pestañas Inicio · Material · Configuración (versión corta). Inicio: anuncio del evento con la Virgen, pasos en **tarjetas o lista** (cada quien elige), al cumplirse un paso se abre solo el siguiente (Guion y Crear imágenes en su ventana). Diagrama a pantalla completa. Material empieza con «Ver guion en Prompter». Configuración: secciones plegables. Imágenes de marca en `frontend/public/marca/`. Inicio muestra solo el evento de hoy o los próximos. Ventanas con `<dialog>` (`componentes/Modal.jsx`).
