// Fechas de los eventos: lunes (gozosos) y viernes (dolorosos), 10 a 11 am, hora CDMX (UTC-6, sin horario de verano).
const DESFASE_CDMX_MS = -6 * 60 * 60 * 1000
const DIA_MS = 24 * 60 * 60 * 1000
export const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado']
const DIAS_CORTOS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'septiembre', 'octubre', 'noviembre', 'diciembre']
const MISTERIOS = { 1: 'Misterios gozosos', 5: 'Misterios dolorosos' }

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

export function esDiaDeEvento(fecha) {
  return fecha.getUTCDay() in MISTERIOS
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

/** Lunes y viernes de esta semana y la siguiente. */
export function semanaYSiguiente(ahora = new Date()) {
  const hoy = medianoche(ahoraCDMX(ahora))
  const lunes = new Date(hoy.getTime() - ((hoy.getUTCDay() + 6) % 7) * DIA_MS)
  return [0, 4, 7, 11].map((n) => infoEvento(new Date(lunes.getTime() + n * DIA_MS), ahora))
}

/** Qué contenido toca preparar: carrusel 2 días antes y reels el mismo día del evento. */
export function agendaEditorial(ahora = new Date()) {
  const hoy = medianoche(ahoraCDMX(ahora))
  const items = []
  for (const r of semanaYSiguiente(ahora)) {
    const carrusel = new Date(r.fecha.getTime() - 2 * DIA_MS)
    if (carrusel >= hoy) items.push({ fecha: carrusel, tipo: 'Carrusel', texto: `Invitación del ${r.nombre.toLowerCase()} · ${r.misterios.toLowerCase()}` })
    if (r.estado === 'futuro' || r.estado === 'hoy' || r.estado === 'en-vivo')
      items.push({ fecha: r.fecha, tipo: 'Reels', texto: `3 reels del evento, después de las 11 am` })
  }
  return items.sort((a, b) => a.fecha - b.fecha).slice(0, 5)
}
