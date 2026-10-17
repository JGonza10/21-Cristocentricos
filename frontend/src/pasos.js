// Flujo de trabajo de Inicio: recuadros, conexiones y pasos (basado en la guía "Cristocéntricos Automático")
// y su estado en vivo a partir de /api/estado.
//   Estados: ok = al día · activo = trabajando · espera = te necesita · error = falló · apagado = agentes sin correr
//            sin = todavía no existe en el sistema
// Fuera de alcance por ahora (Gonza, 2026-10-16): Comunidad, Parroquias, Bienvenida y Respuestas.
import { agendaEditorial, fechaCorta, infoEvento, proximoEvento } from './evento.js'
import { fechaDeClave, fechaHora, REDES } from './util.js'

// k: disp = disparador · agente · humano = tú decides · plata = archivo o lo subes tú · verde = sube solo · hab = se la pides a Claude
export const NODOS = [
  { id: 'n-turnos', x: 80, y: 130, k: 'humano', i: 'users', t: 'Turnos', s: 'Quién dirige y apoya' },
  { id: 's-int', x: 250, y: 130, k: 'hab', i: 'pen', t: 'Intenciones', s: 'Lista para leer', r: 28 },
  { id: 's-guion', x: 420, y: 130, k: 'hab', i: 'pen', t: 'Guion del vivo', s: 'Misterios del día', r: 28 },
  { id: 's-lista', x: 590, y: 130, k: 'hab', i: 'check', t: 'Lista previa', s: 'Antes de transmitir', r: 28 },
  { id: 'n-vivo', x: 760, y: 130, k: 'disp', i: 'bolt', t: 'Evento en vivo', s: 'Lun y vie · 10 a 11 am' },
  { id: 'n-grab', x: 930, y: 130, k: 'plata', i: 'folder', t: 'Grabación guardada', s: 'Carpeta del proyecto' },
  { id: 'n-a1', x: 1100, y: 130, k: 'agente', i: 'film', t: 'Agente de reels', s: '3 momentos en vertical' },
  { id: 's-sub', x: 1270, y: 130, k: 'hab', i: 'check', t: 'Subtítulos', s: 'Revisión', r: 28 },
  { id: 's-fech', x: 420, y: 380, k: 'hab', i: 'cal', t: 'Fechas litúrgicas', s: 'Fiestas del mes', r: 28 },
  { id: 'n-cal', x: 590, y: 380, k: 'disp', i: 'cal', t: 'Calendario', s: '2 días antes' },
  { id: 's-evan', x: 930, y: 380, k: 'hab', i: 'pen', t: 'Evangelio del día', s: 'Reflexión y textos', r: 28 },
  { id: 'n-a2', x: 1100, y: 380, k: 'agente', i: 'img', t: 'Agente de carrusel', s: '5 láminas' },
  { id: 's-rev', x: 1440, y: 315, k: 'hab', i: 'check', t: 'Revisor', s: 'Fechas, tono, formato', r: 28 },
  { id: 'n-band', x: 1610, y: 315, k: 'humano', i: 'shield', t: 'Bandeja de aprobación', s: 'Tú decides' },
  { id: 's-tit', x: 1610, y: 110, k: 'hab', i: 'pen', t: 'Títulos YouTube', s: 'Descripción y etiquetas', r: 28 },
  { id: 'n-pub', x: 1790, y: 315, k: 'agente', i: 'send', t: 'Agente de publicación', s: 'Sube o deja listo lo aprobado' },
  { id: 'n-desc', x: 1790, y: 520, k: 'plata', i: 'x', t: 'Se descarta', s: 'No se publica', r: 28 },
  { id: 'n-ig', x: 1990, y: 45, k: 'plata', i: 'ig', t: 'Instagram', s: 'Sola con Meta', r: 30, red: 'instagram' },
  { id: 'n-fb', x: 1990, y: 180, k: 'plata', i: 'fb', t: 'Facebook', s: 'Sola con Meta', r: 30, red: 'facebook' },
  { id: 'n-tt', x: 1990, y: 315, k: 'plata', i: 'tt', t: 'TikTok', s: 'Subes tú', r: 30, red: 'tiktok' },
  { id: 'n-yt', x: 1990, y: 450, k: 'verde', i: 'yt', t: 'YouTube Shorts', s: 'Sube solo*', r: 30, red: 'youtube' },
  { id: 'n-tv', x: 1990, y: 585, k: 'plata', i: 'tv', t: 'Canal de TV', s: 'Subes tú', r: 30 },
  { id: 's-reg', x: 1990, y: 730, k: 'hab', i: 'sheet', t: 'Registrar video', s: 'Anota la fila', r: 28 },
  { id: 'n-hoja', x: 2190, y: 730, k: 'plata', i: 'sheet', t: 'Hoja de registro', s: 'Google Sheets', r: 30 },
  { id: 's-rep', x: 2390, y: 670, k: 'hab', i: 'chart', t: 'Reporte semanal', s: 'Meta de 1,000', r: 28 },
  { id: 's-res', x: 2390, y: 790, k: 'hab', i: 'pen', t: 'Resumen del vivo', s: 'Qué mejorar', r: 28 },
]
export const LIENZO = { ancho: 2500, alto: 880 }

export const CONEXIONES = [
  { id: 'h0', a: 'n-turnos', b: 's-int' },
  { id: 'h1', a: 's-int', b: 's-guion' }, { id: 'h2', a: 's-guion', b: 's-lista' }, { id: 'h3', a: 's-lista', b: 'n-vivo' },
  { id: 'p1', a: 'n-vivo', b: 'n-grab', l: '1 video' },
  { id: 'p2', a: 'n-grab', b: 'n-a1', l: '1 video' },
  { id: 'h4', a: 'n-a1', b: 's-sub' },
  { id: 'h5', a: 's-fech', b: 'n-cal' }, { id: 'h6', a: 'n-cal', b: 's-evan', l: 'Lunes y viernes' }, { id: 'h7', a: 's-evan', b: 'n-a2' },
  { id: 'h8', a: 's-sub', b: 's-rev', l: '3 reels' }, { id: 'h9', a: 'n-a2', b: 's-rev', l: '5 imágenes' },
  { id: 'h10', a: 's-rev', b: 'n-band' },
  { id: 'p6', a: 'n-band', b: 'n-pub', l: 'Aprobar', sa: -14 },
  { id: 'p8', a: 'n-band', b: 'n-desc', l: 'Rechazar', sa: 14, fija: true },
  { id: 'h11', a: 's-tit', b: 'n-pub' },
  { id: 'p7a', a: 'n-pub', b: 'n-ig' }, { id: 'p7b', a: 'n-pub', b: 'n-fb' }, { id: 'p7c', a: 'n-pub', b: 'n-tt' },
  { id: 'p7d', a: 'n-pub', b: 'n-yt' }, { id: 'p7e', a: 'n-pub', b: 'n-tv' },
  { id: 'h15', a: 'n-pub', b: 's-reg', l: '1 fila' }, { id: 'h16', a: 's-reg', b: 'n-hoja' },
  { id: 'h17', a: 'n-hoja', b: 's-rep' }, { id: 'h18', a: 'n-hoja', b: 's-res' },
]

// q: tu = lo haces tú · solo = se hace solo · hab = Claude te ayuda
export const PASOS = [
  { id: 'turnos', n: ['n-turnos'], v: [], q: 'tu', t: 'Asignas quién dirige y quién apoya',
    x: 'En el calendario de abajo eliges quién dirige y quién apoya cada evento. Los huecos se reparten solos cada domingo a las 6 pm y a cada quien le llega la invitación a su calendario.' },
  { id: 'prepara', n: ['s-int', 's-guion', 's-lista'], v: ['h0', 'h1', 'h2', 'h3'], q: 'hab', t: 'Preparas el evento con ayuda de Claude',
    x: 'Antes del vivo le pides a Claude tres cosas: ordenar las intenciones (sin nombres si no hay permiso), armar el guion del día con los misterios que tocan y repasar la lista de audio, StreamYard, grabación y reloj.' },
  { id: 'vivo', n: ['n-vivo'], v: [], q: 'tu', t: 'Se transmite el evento',
    x: 'Es el disparador del flujo. Transmites en vivo de 10 a 11 de la mañana y tu forma de transmitir no cambia.' },
  { id: 'grabacion', n: ['n-grab'], v: ['p1'], q: 'solo', t: 'La grabación se guarda',
    x: 'OBS o StreamYard guardan el video completo en la carpeta grabaciones. Se configura una sola vez.' },
  { id: 'reels', n: ['n-a1', 's-sub'], v: ['p2', 'h4'], q: 'solo', t: 'El agente de reels trabaja y se revisan los subtítulos',
    x: 'Whisper escucha el video, el agente elige 3 momentos de menos de un minuto, los pone en vertical y les quema subtítulos. Si quieres, Claude revisa palabras mal escuchadas y cortes de línea.' },
  { id: 'carrusel', n: ['s-fech', 'n-cal', 's-evan', 'n-a2'], v: ['h5', 'h6', 'h7'], q: 'solo', t: 'El agente de carrusel trabaja',
    x: 'El calendario lo despierta 2 días antes de cada lunes y viernes y prepara 5 imágenes: invitación con fecha y hora, misterios del día, transmisión en vivo, intenciones y cierre. Claude te puede ayudar con las fechas litúrgicas y la reflexión del Evangelio.' },
  { id: 'bandeja', n: ['s-rev', 'n-band', 'n-desc'], v: ['h8', 'h9', 'h10', 'p8'], q: 'tu', t: 'Revisas y decides',
    x: 'Reels y carruseles llegan a la bandeja y eliges Aprobar o Rechazar. Antes puedes pedirle a Claude que revise fechas, misterios, ortografía y tono. Sin tu visto bueno no se publica nada; lo rechazado se descarta.' },
  { id: 'publicacion', n: ['n-pub', 's-tit'], v: ['p6', 'h11'], q: 'solo', t: 'El agente de publicación prepara las redes',
    x: 'Solo se activa por la salida Aprobar. Sube a YouTube y, si Meta está conectado, a Facebook e Instagram. Para lo demás deja una carpeta por red con los archivos y el texto listos. Claude te puede dejar el título y las etiquetas de YouTube.' },
  { id: 'redes', n: ['n-ig', 'n-fb', 'n-tt', 'n-yt', 'n-tv'], v: ['p7a', 'p7b', 'p7c', 'p7d', 'p7e'], q: 'tu', t: 'Llega a las cinco redes',
    x: 'YouTube sube solo (en privado hasta que Google verifique la aplicación). Instagram y Facebook suben solos con Meta conectado. TikTok y el Canal de TV los subes tú desde su carpeta, en unos 2 minutos.' },
  { id: 'registro', n: ['s-reg', 'n-hoja'], v: ['h15', 'h16'], q: 'tu', t: 'Anotas el video en la hoja de registro',
    x: 'Claude arma la fila con nombre, fecha, duración, reels, carrusel y redes y la escribe en la hoja de Google Sheets. La hoja todavía no está conectada al sistema.' },
  { id: 'mides', n: ['s-rep', 's-res'], v: ['h17', 'h18'], q: 'hab', t: 'Mides y mejoras',
    x: 'Con la hoja, Claude te prepara el reporte semanal contra la meta de 1,000 seguidores y el resumen de cada transmisión: qué funcionó y qué mejorar.' },
]

export const QUIEN = { tu: 'Lo haces tú', solo: 'Se hace solo', hab: 'Claude te ayuda' }
export const ESTADOS = {
  ok: 'Al día', activo: 'Trabajando', espera: 'Te necesita', error: 'Con error', apagado: 'Apagado', sin: 'Pendiente',
}

const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`

/** Estado en vivo: { pasos: [paso + {estado, corto, resumen, detalle}], nodos: {idNodo: {estado, corto}} } */
export function calcularVivo(estado, turnos, ahora = new Date()) {
  const e = estado ?? {}
  const agente = (n) => e.agentes?.find((a) => a.nombre === n) ?? {}
  const ultimaVez = (n) => (agente(n).ultimo_ok ? `Última vez: ${fechaHora(agente(n).ultimo_ok)}` : null)
  const pendTipo = e.pendientes_por_tipo ?? {}
  const pubs = e.publicaciones_conteo ?? {}
  const agenda = agendaEditorial(ahora)
  const proximo = (tipo) => agenda.find((a) => a.tipo === tipo)
  const evento = proximoEvento(ahora)

  const huecos = Object.entries(turnos ?? {})
    .map(([clave, t]) => ({ info: infoEvento(fechaDeClave(clave), ahora), t }))
    .filter(({ info, t }) => info.dias <= 14 && ['futuro', 'hoy', 'en-vivo'].includes(info.estado) && !t.dirige)

  const g0 = e.grabaciones?.[0]
  const grabando = g0 && (g0.estado === 'nueva' || g0.estado === 'procesando')

  const porRed = (red) => {
    const c = e.publicaciones_por_red?.[red] ?? {}
    if (c.error) return { estado: 'error', corto: `${c.error} con error` }
    if (c.subiendo) return { estado: 'activo', corto: 'Subiendo' }
    if (c.listo_manual) return { estado: 'espera', corto: `${c.listo_manual} por subir` }
    if (c.publicado) return { estado: 'ok', corto: `${c.publicado} publicadas` }
    return null
  }
  const redes = Object.keys(REDES).map((r) => ({ red: r, v: porRed(r) })).filter((x) => x.v)
  const peor = ['error', 'espera', 'activo', 'ok'].find((s) => redes.some((x) => x.v.estado === s))

  const p = {
    turnos: agente('turnos').error
      ? { estado: 'error', corto: 'Falló el reparto', resumen: agente('turnos').mensaje }
      : huecos.length
        ? { estado: 'espera', corto: `${huecos.length} sin asignar`,
          resumen: `${plural(huecos.length, 'evento', 'eventos')} de las próximas 2 semanas sin quién dirija.` }
        : { estado: 'ok', corto: 'Asignados', resumen: 'Los próximos eventos ya tienen quién dirija.' },
    prepara: { resumen: 'Pídeselo a Claude antes de cada evento.' },
    vivo: evento?.estado === 'en-vivo'
      ? { estado: 'activo', corto: 'En vivo ahora', resumen: `${evento.nombre}: en vivo ahora.` }
      : { estado: 'ok', corto: evento ? evento.faltan : 'Sin fecha', resumen: evento ? `Próximo: ${evento.nombre}, ${evento.faltan}.` : 'No hay eventos próximos.' },
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
    carrusel: agente('carrusel').error
      ? { estado: 'error', corto: 'Falló', resumen: agente('carrusel').mensaje }
      : { estado: 'ok', corto: pendTipo.carrusel ? `${pendTipo.carrusel} en bandeja` : 'Al día',
        resumen: agente('carrusel').mensaje || 'Esperando al próximo evento.' },
    bandeja: e.bandeja?.pendiente
      ? { estado: 'espera', corto: `${e.bandeja.pendiente} por revisar`,
        resumen: `${plural(e.bandeja.pendiente, 'paquete espera', 'paquetes esperan')} tu aprobación.` }
      : { estado: 'ok', corto: 'Vacía', resumen: 'No hay nada por revisar.' },
    publicacion: pubs.subiendo
      ? { estado: 'activo', corto: 'Subiendo', resumen: `Subiendo ${plural(pubs.subiendo, 'publicación', 'publicaciones')}.` }
      : pubs.error || agente('publicacion').error
        ? { estado: 'error', corto: pubs.error ? `${pubs.error} con error` : 'Falló',
          resumen: pubs.error ? `${plural(pubs.error, 'publicación falló', 'publicaciones fallaron')}. Revísalas en Contenido.` : agente('publicacion').mensaje }
        : { estado: 'ok', corto: pubs.publicado ? `${pubs.publicado} publicadas` : 'Al día',
          resumen: pubs.publicado ? `${plural(pubs.publicado, 'publicación', 'publicaciones')} en redes.` : 'Aún no hay nada aprobado para publicar.' },
    redes: peor
      ? { estado: peor, corto: redes.find((x) => x.v.estado === peor).v.corto,
        resumen: redes.map((x) => `${REDES[x.red]}: ${x.v.corto}`).join(' · ') + '.' }
      : { estado: 'ok', corto: 'Sin publicaciones', resumen: 'Todavía no se ha publicado nada.' },
    registro: { estado: 'sin', corto: 'Sin conectar', resumen: 'La hoja de Google Sheets aún no está conectada al sistema.' },
    mides: { resumen: 'Pídeselo a Claude cada semana.' },
  }

  p.turnos.detalle = [e.google ? 'Las invitaciones llegan por Google Calendar.' : 'Google Calendar sin conectar: no se envían invitaciones.', ultimaVez('turnos')]
  p.carrusel.detalle = [proximo('Carrusel') && `Próximo: ${fechaCorta(proximo('Carrusel').fecha)} · ${proximo('Carrusel').texto}`, ultimaVez('carrusel')]
  p.grabacion.detalle = [`${plural(Object.values(e.grabaciones_conteo ?? {}).reduce((a, b) => a + b, 0), 'grabación recibida', 'grabaciones recibidas')} en total.`]
  p.reels.detalle = [proximo('Reels') && `Próximos: ${fechaCorta(proximo('Reels').fecha)}, después de las 11 am.`, ultimaVez('reels')]
  p.bandeja.detalle = [`${plural(e.bandeja?.aprobado ?? 0, 'aprobado', 'aprobados')} · ${plural(e.bandeja?.rechazado ?? 0, 'rechazado', 'rechazados')}`]
  p.publicacion.detalle = [e.meta ? 'Facebook e Instagram conectados.' : 'Meta sin conectar: Facebook e Instagram quedan en su carpeta.', ultimaVez('publicacion')]

  // Sin agentes corriendo, lo automático no avanza.
  if (estado && !e.worker_activo) {
    for (const id of ['grabacion', 'reels', 'carrusel', 'publicacion']) {
      if (p[id].estado === 'ok' || p[id].estado === 'activo') Object.assign(p[id], { estado: 'apagado', corto: 'Apagado' })
    }
  }

  const nodos = {
    'n-turnos': p.turnos, 'n-vivo': p.vivo, 'n-grab': p.grabacion, 'n-a1': p.reels, 'n-a2': p.carrusel,
    'n-band': p.bandeja, 'n-pub': p.publicacion, 'n-hoja': p.registro,
  }
  for (const n of NODOS) if (n.red) nodos[n.id] = porRed(n.red)
  if (!e.meta) for (const id of ['n-ig', 'n-fb']) nodos[id] ??= { estado: null, corto: 'En carpeta' }

  const pasos = PASOS.map((paso, i) => ({ ...paso, numero: i + 1, ...p[paso.id], detalle: (p[paso.id].detalle ?? []).filter(Boolean) }))
  return { pasos, nodos }
}
