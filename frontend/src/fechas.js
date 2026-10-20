// Fechas en hora de la Ciudad de México (UTC-6, sin horario de verano). Leer siempre con getUTC*.
const DESFASE_CDMX_MS = -6 * 60 * 60 * 1000
const DIAS = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado']
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'septiembre', 'octubre', 'noviembre', 'diciembre']

export function ahoraCDMX(ahora = new Date()) {
  return new Date(ahora.getTime() + DESFASE_CDMX_MS)
}

/** Date → '2026-10-22' */
export function claveFecha(d) {
  return d.toISOString().slice(0, 10)
}

/** '2026-10-22' o Date → 'Jueves 22 de octubre' */
export function nombreFecha(f) {
  const d = typeof f === 'string' ? new Date(`${f}T00:00:00Z`) : f
  const dia = DIAS[d.getUTCDay()]
  return `${dia[0].toUpperCase()}${dia.slice(1)} ${d.getUTCDate()} de ${MESES[d.getUTCMonth()]}`
}
