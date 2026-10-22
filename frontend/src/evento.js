// Fechas de los eventos, 10 a 11 am, hora CDMX (UTC-6, sin horario de verano).
// Lunes y viernes son los días fijos; cualquier otro día es evento si tiene tema (Gonza, 2026-10-21).
const DESFASE_CDMX_MS = -6 * 60 * 60 * 1000
const DIA_MS = 24 * 60 * 60 * 1000
export const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado']
const DIAS_CORTOS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'septiembre', 'octubre', 'noviembre', 'diciembre']
// Misterios de cada día (getUTCDay: domingo = 0).
const MISTERIOS = {
  0: 'Misterios gloriosos', 1: 'Misterios gozosos', 2: 'Misterios dolorosos', 3: 'Misterios gloriosos',
  4: 'Misterios luminosos', 5: 'Misterios dolorosos', 6: 'Misterios gozosos',
}
const DIAS_FIJOS = new Set([1, 5])
// Días con tema que no son lunes ni viernes (AAAA-MM-DD). Los llena /api/estado y el calendario.
const extras = new Set()

/** Agrega los días con tema que vienen del servidor (los que no son fijos se vuelven evento). */
export function registrarEventos(claves) {
  for (const c of claves ?? []) extras.add(c)
}


const mayus = (t) => t[0].toUpperCase() + t.slice(1)

/** Fecha y hora "de pared" en CDMX (leer siempre con getUTC*). */
export function ahoraCDMX(ahora = new Date()) {
  return new Date(ahora.getTime() + DESFASE_CDMX_MS)
}

function medianoche(d) {
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()))
}

export function nombreFecha(d) {
  return `${mayus(DIAS[d.getUTCDay()])} ${d.getUTCDate()} de ${MESES[d.getUTCMonth()]}`
}

export function fechaCorta(d) {
  return `${DIAS_CORTOS[d.getUTCDay()]} ${d.getUTCDate()}`
}

export function claveFecha(d) {
  return d.toISOString().slice(0, 10)
}

/** Describe un día de evento respecto a "ahora". */
export function infoEvento(fecha, ahora = new Date()) {
  const cdmx = ahoraCDMX(ahora)
  const hoy = medianoche(cdmx)
  const dias = Math.round((fecha - hoy) / DIA_MS)
  const hora = cdmx.getUTCHours()
  let estado = 'futuro'
  if (dias < 0 || (dias === 0 && hora >= 11)) estado = dias === 0 ? 'hoy-terminado' : 'pasado'
  else if (dias === 0) estado = hora === 10 ? 'en-vivo' : 'hoy'
  return {
    fecha, clave: claveFecha(fecha), nombre: nombreFecha(fecha),
    misterios: MISTERIOS[fecha.getUTCDay()], dias, estado,
    faltan: dias === 0 ? 'hoy' : dias === 1 ? 'mañana' : dias > 1 ? `en ${dias} días` : `hace ${-dias} días`,
  }
}

export function esDiaFijo(fecha) {
  return DIAS_FIJOS.has(fecha.getUTCDay())
}

export function esDiaDeEvento(fecha) {
  return esDiaFijo(fecha) || extras.has(claveFecha(fecha))
}

export function proximoEvento(ahora = new Date()) {
  const hoy = medianoche(ahoraCDMX(ahora))
  for (let i = 0; i < 8; i++) {
    const d = new Date(hoy.getTime() + i * DIA_MS)
    if (!esDiaDeEvento(d)) continue
    const info = infoEvento(d, ahora)
    if (info.estado !== 'hoy-terminado') return info
  }
  return null
}

/** Lunes y viernes de esta semana y la siguiente (los días fijos). */
export function semanaYSiguiente(ahora = new Date()) {
  const hoy = medianoche(ahoraCDMX(ahora))
  const lunes = new Date(hoy.getTime() - ((hoy.getUTCDay() + 6) % 7) * DIA_MS)
  return [0, 4, 7, 11].map((n) => infoEvento(new Date(lunes.getTime() + n * DIA_MS), ahora))
}

/** Qué contenido toca preparar: difusión antes del evento y reels el mismo día. */
export function agendaEditorial(ahora = new Date()) {
  const hoy = medianoche(ahoraCDMX(ahora))
  const items = []
  for (const r of semanaYSiguiente(ahora)) {
    const carrusel = new Date(r.fecha.getTime() - 2 * DIA_MS)
    if (carrusel >= hoy) items.push({ fecha: carrusel, tipo: 'Carrusel', texto: `Difusión del ${r.nombre.toLowerCase()}` })
    if (r.estado === 'futuro' || r.estado === 'hoy' || r.estado === 'en-vivo')
      items.push({ fecha: r.fecha, tipo: 'Reels', texto: `5 reels y carrusel del evento, después de las 11 am` })
  }
  return items.sort((a, b) => a.fecha - b.fecha).slice(0, 5)
}
