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

## Colores — oscuro
```css
--bg:#15111c; --surface:#1e1828; --surface-2:#241d30;
--ink:#f1ecf8; --ink-2:#d2c7e0; --muted:#b3a8c2; --muted-2:#9d92ac; --line:#3a3048;
--accent:#b48cf0; --accent-strong:#c9a8f5; --accent-soft:#2e2442; --on-accent:#1a1225;
--grad-tab:linear-gradient(90deg,#8b55d0,#b45cc4);
--grad-hero:linear-gradient(135deg,#221a31,#211c38 55%,#1f2140);
--ok:#78c995; --ok-soft:#1b3326; --warn:#e6b84e; --warn-soft:#3a2f12; --off:#6e6479;
```
Se aplica con `@media (prefers-color-scheme:dark){:root:not([data-theme="light"])}` y `:root[data-theme="dark"]`.

## Imágenes para redes
Blanco y vino: `#ffffff`, `#fbf9f7`, vino `#7a1c2e`, vino suave `#f3e4e7`, texto `#3a1420`, oro `#8f6b10`. Títulos en **Spectral** 700, texto Public Sans (TTF en `assets/fuentes/`). Carrusel 1080×1350.

## Significado
Morado = acciones · degradado = pestaña activa y sello del login · verde = funcionando · ámbar = falta algo · gris = inactivo.
En gráficas: paleta viva con degradados, nada de café o mostaza oscura.

## Componentes
- Botón primario `--accent`, radio 12 px, alto ≥ 44 px; botón suave `--accent-soft`.
- Tarjeta `--surface`, borde `--line`, radio 20 px, padding 22 px (18 en celular).
- Fila: `--surface-2`, radio 14 px; la de hoy con barra morada a la izquierda.
- Ancho máximo 940 px, margen 16 px, cuerpo 16 px/1.55.

## Pantallas
Cabecera fija (selector Claro/Oscuro, Diagrama, Salir) · pestañas Inicio · Contenido · Evento · Estadísticas · Configuración. Inicio muestra solo el evento de hoy o los próximos. Ventanas con `<dialog>` (`componentes/Modal.jsx`).
