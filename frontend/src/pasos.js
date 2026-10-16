// Pasos del flujo de trabajo (diagrama y tarjetas de Inicio) y su estado en vivo a partir de /api/estado.
//   ok = al día · activo = trabajando ahora · espera = te necesita · error = falló · apagado = agentes sin correr
import { agendaEditorial, fechaCorta, infoEvento } from './evento.js'
import { fechaDeClave, fechaHora } from './util.js'

export const PASOS = [
  { id: 'turnos', titulo: 'Turnos', que: 'Quién dirige y quién apoya cada evento. Los huecos se reparten solos el domingo a las 6 pm.' },
  { id: 'carrusel', titulo: 'Carrusel', que: 'La invitación para redes se prepara sola 2 días antes de cada evento.' },
  { id: 'grabacion', titulo: 'Grabación', que: 'OBS guarda el video del evento en la carpeta de grabaciones.' },
  { id: 'reels', titulo: 'Reels', que: 'Whisper transcribe el video y se eligen 3 momentos con subtítulos.' },
  { id: 'bandeja', titulo: 'Bandeja', que: 'Tú revisas y apruebas o rechazas cada carrusel y reel.' },
  { id: 'publicacion', titulo: 'Publicación', que: 'Lo aprobado se sube a las redes o queda listo para subirlo a mano.' },
]

export const CONEXIONES = [
  ['turnos', 'grabacion'], ['grabacion', 'reels'], ['reels', 'bandeja'], ['carrusel', 'bandeja'], ['bandeja', 'publicacion'],
]

export const ESTADOS = {
  ok: 'Al día', activo: 'Trabajando', espera: 'Te necesita', error: 'Con error', apagado: 'Apagado',
}

const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`

/** Devuelve los 6 pasos con { estado, corto, resumen, detalle[], accion }. */
export function calcularPasos(estado, turnos, ahora = new Date()) {
  const e = estado ?? {}
  const agente = (n) => e.agentes?.find((a) => a.nombre === n) ?? {}
  const ultimaVez = (n) => (agente(n).ultimo_ok ? `Última vez: ${fechaHora(agente(n).ultimo_ok)}` : null)
  const pendTipo = e.pendientes_por_tipo ?? {}
  const pubs = e.publicaciones_conteo ?? {}
  const agenda = agendaEditorial(ahora)
  const proximo = (tipo) => agenda.find((a) => a.tipo === tipo)

  const huecos = Object.entries(turnos ?? {})
    .map(([clave, t]) => ({ info: infoEvento(fechaDeClave(clave), ahora), t }))
    .filter(({ info, t }) => info.dias <= 14 && ['futuro', 'hoy', 'en-vivo'].includes(info.estado) && !t.dirige)

  const g0 = e.grabaciones?.[0]
  const grabando = g0 && (g0.estado === 'nueva' || g0.estado === 'procesando')

  const p = {
    turnos: agente('turnos').error
      ? { estado: 'error', corto: 'Falló el reparto', resumen: agente('turnos').mensaje }
      : huecos.length
        ? { estado: 'espera', corto: plural(huecos.length, 'sin asignar', 'sin asignar'),
          resumen: `${plural(huecos.length, 'evento', 'eventos')} de las próximas 2 semanas sin quién dirija.` }
        : { estado: 'ok', corto: 'Asignados', resumen: 'Los próximos eventos ya tienen quién dirija.' },
    carrusel: agente('carrusel').error
      ? { estado: 'error', corto: 'Falló', resumen: agente('carrusel').mensaje }
      : { estado: 'ok', corto: pendTipo.carrusel ? `${pendTipo.carrusel} en bandeja` : 'Al día',
        resumen: agente('carrusel').mensaje || 'Esperando al próximo evento.' },
    grabacion: grabando
      ? { estado: 'activo', corto: 'Procesando', resumen: `Procesando ${g0.nombre}.` }
      : g0?.estado === 'error'
        ? { estado: 'error', corto: 'Falló', resumen: g0.error || `No se pudo procesar ${g0.nombre}.` }
        : { estado: 'ok', corto: g0 ? 'Lista' : 'Esperando',
          resumen: g0 ? `Última grabación: ${g0.nombre}.` : 'Esperando la grabación del evento.' },
    reels: agente('reels').error
      ? { estado: 'error', corto: 'Falló', resumen: agente('reels').mensaje }
      : grabando
        ? { estado: 'activo', corto: 'Haciendo reels', resumen: 'Transcribiendo y eligiendo los momentos.' }
        : { estado: 'ok', corto: pendTipo.reel ? `${pendTipo.reel} en bandeja` : 'Al día',
          resumen: agente('reels').mensaje || 'Esperando grabaciones.' },
    bandeja: e.bandeja?.pendiente
      ? { estado: 'espera', corto: `${e.bandeja.pendiente} por revisar`,
        resumen: `${plural(e.bandeja.pendiente, 'paquete espera', 'paquetes esperan')} tu aprobación.` }
      : { estado: 'ok', corto: 'Vacía', resumen: 'No hay nada por revisar.' },
    publicacion: pubs.subiendo
      ? { estado: 'activo', corto: 'Subiendo', resumen: `Subiendo ${plural(pubs.subiendo, 'publicación', 'publicaciones')}.` }
      : pubs.error || agente('publicacion').error
        ? { estado: 'error', corto: pubs.error ? `${pubs.error} con error` : 'Falló',
          resumen: pubs.error ? `${plural(pubs.error, 'publicación falló', 'publicaciones fallaron')}. Revísalas en Contenido.` : agente('publicacion').mensaje }
        : pubs.listo_manual
          ? { estado: 'espera', corto: `${pubs.listo_manual} a mano`, resumen: `${plural(pubs.listo_manual, 'publicación lista', 'publicaciones listas')} para subir a mano.` }
          : { estado: 'ok', corto: pubs.publicado ? `${pubs.publicado} publicadas` : 'Al día',
            resumen: pubs.publicado ? `${plural(pubs.publicado, 'publicación', 'publicaciones')} en redes.` : 'Aún no hay nada aprobado para publicar.' },
  }

  // Detalle extra por paso
  p.turnos.detalle = [e.google ? 'Las invitaciones llegan por Google Calendar.' : 'Google Calendar sin conectar: no se envían invitaciones.', ultimaVez('turnos')]
  p.carrusel.detalle = [proximo('Carrusel') && `Próximo: ${fechaCorta(proximo('Carrusel').fecha)} · ${proximo('Carrusel').texto}`, ultimaVez('carrusel')]
  p.grabacion.detalle = [`${plural(Object.values(e.grabaciones_conteo ?? {}).reduce((a, b) => a + b, 0), 'grabación recibida', 'grabaciones recibidas')} en total.`]
  p.reels.detalle = [proximo('Reels') && `Próximos: ${fechaCorta(proximo('Reels').fecha)}, después de las 11 am.`, ultimaVez('reels')]
  p.bandeja.detalle = [`${plural(e.bandeja?.aprobado ?? 0, 'aprobado', 'aprobados')} · ${plural(e.bandeja?.rechazado ?? 0, 'rechazado', 'rechazados')}`]
  p.publicacion.detalle = [e.meta ? 'Facebook e Instagram conectados.' : 'Meta sin conectar: se prepara la carpeta para subir a mano.', ultimaVez('publicacion')]

  // Sin agentes corriendo, lo automático no avanza (los turnos se pueden seguir asignando a mano).
  if (estado && !e.worker_activo) {
    for (const id of ['carrusel', 'grabacion', 'reels', 'publicacion']) {
      if (p[id].estado === 'ok' || p[id].estado === 'activo') Object.assign(p[id], { estado: 'apagado', corto: 'Apagado' })
    }
  }
  return PASOS.map((paso, i) => ({ ...paso, numero: i + 1, ...p[paso.id], detalle: p[paso.id].detalle.filter(Boolean) }))
}
