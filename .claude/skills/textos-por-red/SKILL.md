---
name: textos-por-red
description: Reglas para adaptar el texto aprobado de cada reel o carrusel a Instagram, Facebook, TikTok, YouTube y TV — límites de caracteres, hashtags por misterio (gozosos/dolorosos), llamado a la acción y limpieza. Úsala al generar `texto.txt` de los paquetes, al validar textos editados en la bandeja o al escribir plantillas de texto y hashtags.
---

# Textos por red social

Un solo texto aprobado → 5 versiones. La función vive en `agentes/textos.py` como
`adaptar(texto, red, tipo_misterio) -> dict` y es **pura** (sin BD ni archivos) para probarla fácil.

## Límites (validar SIEMPRE antes de escribir `texto.txt`)
| Red | Campo | Límite | Notas |
|---|---|---|---|
| Instagram | pie | 2 200 caracteres | Máx. **5 hashtags** (lo que Instagram recomienda hoy); los primeros ~125 caracteres se ven sin "más" |
| Facebook | texto | Sin límite práctico | Mantener < 500; 2–3 hashtags |
| TikTok | descripción | 4 000 caracteres | 3–5 hashtags; frase corta arriba |
| YouTube | título | **100** caracteres | Sin `<` ni `>` (la API lo rechaza) |
| YouTube | descripción | 5 000 bytes | `#Shorts` al final |
| YouTube | etiquetas | 500 caracteres en total | Sin `#` |
| TV | texto | 1 línea | Solo título + fecha, para StreamYard |
Si algo excede, **recortar en el último espacio** y agregar "…"; nunca cortar a media palabra
ni a mitad de un emoji (contar con `len()` sobre el `str`, recortar por grafemas simples).

## Estructura del texto
```
<gancho de 1 línea: frase del misterio o de la oración>

<2–3 líneas de contexto: qué misterio, invitación a rezar>

🙏 Únete en vivo lunes y viernes, 10 am (hora CDMX).
<enlace o "Link en el perfil">

<hashtags>
```

## Hashtags por tipo (plantillas)
- Base (siempre): `#SantoRosario #Cristocentricos #RosarioEnVivo`
- Gozosos (lunes): `#MisteriosGozosos #VirgenMaria`
- Dolorosos (viernes): `#MisteriosDolorosos #Cuaresma` *(solo en Cuaresma)* o `#Pasion`
- Elegir los más relevantes hasta el límite de la red; sin duplicados (comparar en minúsculas
  y sin acentos).

## Limpieza (seguridad y calidad)
- Normalizar a NFC (`unicodedata.normalize("NFC", t)`), quitar caracteres de control
  (excepto `\n`), colapsar más de 2 saltos de línea.
- Quitar `<` `>` en YouTube; quitar URLs que no sean de la lista blanca del canal.
- El texto viene de la bandeja (lo escribe un humano): validarlo, nunca ejecutarlo ni usarlo
  en rutas de archivo o comandos de ffmpeg.
- Tono: respetuoso, cálido, sin promesas ni pedir dinero. Revisar ortografía de "María", "Señor", "misterio".

## Pruebas (`tests/test_textos.py`)
- Cada red respeta su límite con un texto de 10 000 caracteres.
- Instagram nunca pasa de 5 hashtags.
- Título de YouTube sin `<>` y ≤ 100.
- Lunes → gozosos, viernes → dolorosos.
- Acentos y emojis sobreviven intactos (comparar NFC).
