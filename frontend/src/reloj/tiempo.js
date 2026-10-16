// Reloj de la CDMX y cuenta regresiva al rosario (lo usan la pestaña Evento y el overlay).
import { ahoraCDMX, proximoRosario } from '../rosario.js'

const HORA_MS = 3_600_000
const CDMX_A_UTC_MS = 6 * HORA_MS // CDMX = UTC-6 (sin horario de verano desde 2022)

const dos = (n) => String(n).padStart(2, '0')

/** Hora de pared en la CDMX: "10:04:37" */
export function horaCDMX(ahora = new Date()) {
  const c = ahoraCDMX(ahora)
  return `${dos(c.getUTCHours())}:${dos(c.getUTCMinutes())}:${dos(c.getUTCSeconds())}`
}

/** Estado del rosario para el overlay: antes (con cuenta regresiva), en vivo o sin evento hoy. */
export function estadoReloj(ahora = new Date()) {
  const r = proximoRosario(ahora)
  if (!r) return { modo: 'nada' }
  const inicio = r.fecha.getTime() + 10 * HORA_MS + CDMX_A_UTC_MS
  const fin = inicio + HORA_MS
  const t = ahora.getTime()
  if (t >= inicio && t < fin) return { modo: 'vivo', rosario: r, restante: fin - t }
  return { modo: 'antes', rosario: r, faltan: inicio - t }
}

/** 3725000 ms → "1:02:05"; menos de una hora → "02:05"; más de un día → "2 días" */
export function cuenta(ms) {
  const s = Math.max(0, Math.ceil(ms / 1000))
  const dias = Math.floor(s / 86400)
  if (dias >= 1) return dias === 1 ? '1 día' : `${dias} días`
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return h ? `${h}:${dos(m)}:${dos(s % 60)}` : `${dos(m)}:${dos(s % 60)}`
}
