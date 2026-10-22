// Utilidades compartidas entre pantallas.

export const fechaHora = (iso) => (iso ? new Date(iso).toLocaleString('es-MX', {
  timeZone: 'America/Mexico_City', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
}) : '')

export const fechaDeClave = (clave) => new Date(`${clave}T00:00:00Z`)

export function segundosATexto(s) {
  const t = Math.max(0, Math.round(s))
  const h = Math.floor(t / 3600)
  const m = Math.floor((t % 3600) / 60)
  const seg = t % 60
  return h ? `${h}:${String(m).padStart(2, '0')}:${String(seg).padStart(2, '0')}` : `${m}:${String(seg).padStart(2, '0')}`
}

