// Flujo de trabajo de Inicio: recuadros, conexiones y pasos (basado en la guía "Cristocéntricos Automático")
// y su estado en vivo a partir de /api/estado. El avance de cada evento (hecho / omitido / pendiente)
// viene de /api/avance.
//   Estados en vivo: ok = al día · activo = trabajando · espera = te necesita · error = falló
//                    apagado = agentes sin correr · sin = todavía no existe en el sistema
// Fuera de alcance por ahora (Gonza, 2026-10-16): Comunidad, Parroquias, Bienvenida y Respuestas.
import { agendaEditorial, fechaCorta, infoEvento, proximoEvento } from './evento.js'
import { fechaDeClave, fechaHora, REDES } from './util.js'

// k: disp = disparador · agente · humano = tú decides · plata = archivo o lo subes tú · verde = sube solo · hab = se la pides a Claude
// Proceso del documento «Lo que necesito» (Gonza, 2026-10-17): cada evento tiene un tema.
export const NODOS = [
  { id: 's-ideas', x: 60, y: 130, k: 'hab', i: 'pen', t: 'Ideas', s: 'Escritas o por voz', r: 28 },
  { id: 'n-tema', x: 185, y: 130, k: 'humano', i: 'cal', t: 'Tema del día', s: 'En el calendario' },
  { id: 's-guion', x: 310, y: 130, k: 'hab', i: 'pen', t: 'Guion', s: 'Con ayuda de Claude', r: 28 },
  { id: 'n-turnos', x: 435, y: 130, k: 'humano', i: 'users', t: 'Turnos', s: 'Quién dirige y apoya' },
  { id: 's-lista', x: 560, y: 130, k: 'humano', i: 'check', t: 'Revisión técnica', s: 'Antes de transmitir', r: 28 },
  { id: 'n-vivo', x: 685, y: 130, k: 'disp', i: 'bolt', t: 'Evento en vivo', s: 'Lun y vie · 10 a 11 am' },
  { id: 'n-grab', x: 810, y: 130, k: 'plata', i: 'folder', t: 'Grabación', s: 'OBS graba solo' },
  { id: 'n-a1', x: 935, y: 130, k: 'agente', i: 'film', t: 'Agente de reels', s: '5 momentos, luz y audio' },
  { id: 'n-a3', x: 1010, y: 300, k: 'agente', i: 'img', t: 'Carrusel de escenas', s: 'Fotos y frases del video' },
  { id: 'n-cal', x: 310, y: 420, k: 'disp', i: 'cal', t: 'Calendario', s: 'Tema con anticipación' },
  { id: 'n-a2', x: 560, y: 420, k: 'agente', i: 'img', t: 'Agente de difusión', s: 'Carrusel + reel promo' },
  { id: 's-rev', x: 1140, y: 420, k: 'hab', i: 'check', t: 'Revisor', s: 'Fechas, tono, formato', r: 28 },
  { id: 'n-band', x: 1280, y: 420, k: 'humano', i: 'shield', t: 'Bandeja', s: 'Tú decides' },
  { id: 's-tit', x: 1280, y: 180, k: 'hab', i: 'pen', t: 'Títulos YouTube', s: 'Descripción y etiquetas', r: 28 },
  { id: 'n-pub', x: 1440, y: 360, k: 'agente', i: 'send', t: 'Publicación', s: 'Sube o deja listo' },
  { id: 'n-desc', x: 1440, y: 600, k: 'plata', i: 'x', t: 'Se descarta', s: 'No se publica', r: 28 },
  { id: 'n-ig', x: 1620, y: 45, k: 'plata', i: 'ig', t: 'Instagram', s: 'Sola con Meta', r: 30, red: 'instagram' },
  { id: 'n-fb', x: 1620, y: 180, k: 'plata', i: 'fb', t: 'Facebook', s: 'Sola con Meta', r: 30, red: 'facebook' },
  { id: 'n-tt', x: 1620, y: 315, k: 'plata', i: 'tt', t: 'TikTok', s: 'Subes tú', r: 30, red: 'tiktok' },
  { id: 'n-yt', x: 1620, y: 450, k: 'verde', i: 'yt', t: 'YouTube Shorts', s: 'Sube solo*', r: 30, red: 'youtube' },
  { id: 'n-tv', x: 1620, y: 585, k: 'plata', i: 'tv', t: 'Canal de TV', s: 'Subes tú', r: 30 },
  { id: 'n-res', x: 1800, y: 315, k: 'agente', i: 'pen', t: 'Resumen del vivo', s: 'Automático' },
  { id: 'n-rep', x: 1950, y: 315, k: 'agente', i: 'chart', t: 'Reporte semanal', s: 'Lunes 8 am, solo' },
  { id: 'n-reg', x: 1800, y: 740, k: 'plata', i: 'sheet', t: 'Registro', s: 'En la app · Excel', r: 30 },
]
export const LIENZO = { ancho: 2040, alto: 860 }

export const CONEXIONES = [
  { id: 'h0', a: 's-ideas', b: 'n-tema' },
  { id: 'h1', a: 'n-tema', b: 's-guion' }, { id: 'h2', a: 's-guion', b: 'n-turnos' },
  { id: 'h3', a: 'n-turnos', b: 's-lista' }, { id: 'h3b', a: 's-lista', b: 'n-vivo' },
  { id: 'p1', a: 'n-vivo', b: 'n-grab', l: '1 video' },
  { id: 'p2', a: 'n-grab', b: 'n-a1', l: '1 video' },
  { id: 'p3', a: 'n-grab', b: 'n-a3' },
  { id: 'h5', a: 'n-tema', b: 'n-cal' },
  { id: 'h6', a: 'n-cal', b: 'n-a2', l: 'Hasta 2 semanas antes' },
  { id: 'h8', a: 'n-a1', b: 's-rev', l: '5 reels' }, { id: 'h9', a: 'n-a3', b: 's-rev', l: '5 imágenes' },
  { id: 'h9b', a: 'n-a2', b: 's-rev', l: 'Difusión' },
  { id: 'h10', a: 's-rev', b: 'n-band' },
  { id: 'p6', a: 'n-band', b: 'n-pub', l: 'Aprobar', sa: -14 },
  { id: 'p8', a: 'n-band', b: 'n-desc', l: 'Rechazar', sa: 14, fija: true },
  { id: 'h11', a: 's-tit', b: 'n-pub' },
  { id: 'p7a', a: 'n-pub', b: 'n-ig' }, { id: 'p7b', a: 'n-pub', b: 'n-fb' }, { id: 'p7c', a: 'n-pub', b: 'n-tt' },
  { id: 'p7d', a: 'n-pub', b: 'n-yt' }, { id: 'p7e', a: 'n-pub', b: 'n-tv' },
  { id: 'c1', a: 'n-ig', b: 'n-res' }, { id: 'c2', a: 'n-fb', b: 'n-res' }, { id: 'c3', a: 'n-tt', b: 'n-res' },
  { id: 'c4', a: 'n-yt', b: 'n-res' }, { id: 'c5', a: 'n-tv', b: 'n-res' },
  { id: 'r1', a: 'n-res', b: 'n-rep', l: 'Cada lunes' },
  { id: 'h15', a: 'n-pub', b: 'n-reg', l: '1 fila' },
]

// q: tu = lo haces tú · solo = se hace solo · hab = Claude te ayuda
export const PASOS = [
  { id: 'tema', n: ['s-ideas', 'n-tema', 's-guion'], v: ['h0', 'h1'], q: 'hab', t: 'Tema y guion del evento',
    x: 'Esbeidy o Juan ponen el tema en el calendario con anticipación (lo ideal: los próximos 2 eventos siempre con tema). Al guardarlo, al equipo le llega un aviso por correo y por Google Calendar. El guion lo escribe Esbeidy o lo prepara con Claude con el botón «Preparar guion con Claude». Las ideas que vayan surgiendo se guardan en «Ideas», escritas o por voz.' },
  { id: 'turnos', n: ['n-turnos'], v: ['h2'], q: 'tu', t: 'Asignas quién dirige y quién apoya',
    x: 'Eliges en el calendario quién dirige y quién apoya el evento. Los huecos se reparten solos cada domingo a las 6 pm y a cada quien le llega la invitación a su calendario.' },
  { id: 'difusion', n: ['n-cal', 'n-a2'], v: ['h5', 'h6'], q: 'solo', t: 'Difusión del evento',
    x: 'En cuanto el evento tiene tema (hasta 2 semanas antes), el agente arma un carrusel de 5 imágenes con el tema y un reel promocional de 15 segundos para atraer seguidores. Llegan a la bandeja; al subir el reel, ponle un audio de moda en cada red. También puedes generarla a mano.' },
  { id: 'revision', n: ['s-lista'], v: ['h3'], q: 'tu', t: 'Revisión técnica del día',
    x: 'Antes de transmitir, Juan palomea la lista: audio, cámara y luz, internet, StreamYard, OBS, guion e intenciones a la mano y reloj. Así no hay fallas durante la transmisión.' },
  { id: 'vivo', n: ['n-vivo'], v: ['h3b'], q: 'tu', t: 'Se transmite el evento',
    x: 'Es el disparador del flujo. Transmites en vivo de 10 a 11 de la mañana por StreamYard, como siempre. La app abre OBS y graba sola desde las 9:55; también puedes grabar o detener con un botón.' },
  { id: 'grabacion', n: ['n-grab'], v: ['p1'], q: 'solo', t: 'La grabación se guarda',
    x: 'OBS deja el video en la carpeta grabaciones al terminar. Si se grabó en otra computadora, súbelo con «Subir grabación» (se reanuda si se corta el internet).' },
  { id: 'reels', n: ['n-a1'], v: ['p2'], q: 'solo', t: 'El agente de reels trabaja',
    x: 'Whisper escucha el video en esta PC, el agente elige 5 momentos de menos de un minuto, los pone en vertical, mejora luz, color y volumen, y les quema subtítulos.' },
  { id: 'carrusel', n: ['n-a3'], v: ['p3'], q: 'solo', t: 'Carrusel con escenas del video',
    x: 'Con los mismos momentos, el agente toma fotos del video y las frases que se dijeron, y arma un carrusel de 5 imágenes: portada, 3 escenas con su frase y la invitación al próximo evento.' },
  { id: 'bandeja', n: ['s-rev', 'n-band', 'n-desc'], v: ['h8', 'h9', 'h9b', 'h10', 'p8'], q: 'tu', t: 'Revisas y decides',
    x: 'Reels y carruseles llegan a la bandeja y eliges Aprobar o Rechazar. Antes puedes pedirle a Claude que revise ortografía y tono. Sin tu visto bueno no se publica nada; lo rechazado se descarta.' },
  { id: 'publicacion', n: ['n-pub', 's-tit'], v: ['p6', 'h11'], q: 'solo', t: 'El agente de publicación prepara las redes',
    x: 'Solo se activa por la salida Aprobar. Sube a YouTube y, si Meta está conectado, a Facebook e Instagram. Para lo demás deja una carpeta por red con los archivos y el texto listos.' },
  { id: 'redes', n: ['n-ig', 'n-fb', 'n-tt', 'n-yt', 'n-tv'], v: ['p7a', 'p7b', 'p7c', 'p7d', 'p7e'], q: 'tu', t: 'Llega a las cinco redes',
    x: 'YouTube sube solo (en privado hasta que Google verifique la aplicación). Instagram y Facebook suben solos con Meta conectado. TikTok y el Canal de TV los subes tú desde su carpeta, en unos 2 minutos.' },
  { id: 'registro', n: ['n-reg'], v: ['h15'], q: 'solo', t: 'Queda en el registro',
    x: 'Ya no hay hoja de Google Sheets: la app guarda sola cada evento con su tema, video, minutos, reels, carrusel y lo publicado en cada red. Descárgalo para Excel desde el reporte.' },
  { id: 'mides', n: ['n-res', 'n-rep'], v: ['c1', 'c2', 'c3', 'c4', 'c5', 'r1'], q: 'solo', t: 'El sistema arma el reporte semanal',
    x: 'Cada lunes a las 8 am el sistema arma solo, sin Claude, el reporte de la semana: resumen de cada evento, quién dirigió y apoyó, qué se aprobó, cómo quedó cada red, seguidores contra la meta de 1,000 y qué mejorar.' },
]

export const QUIEN = { tu: 'Lo haces tú', solo: 'Se hace solo', hab: 'Claude te ayuda' }
export const ESTADOS = {
  ok: 'Al día', activo: 'Trabajando', espera: 'Te necesita', error: 'Con error', apagado: 'Apagado', sin: 'Pendiente',
}
export const AVANCE = { hecho: 'Hecho', omitido: 'Omitido', pendiente: 'Pendiente' }

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

  const temas = e.temas ?? []
  const sinTema = temas.slice(0, 2).filter((t) => !t.tema)
  const sinGuion = temas.slice(0, 2).filter((t) => t.tema && !t.guion)
  const nombreCorto = (clave) => fechaCorta(fechaDeClave(clave))
  const obs = e.obs ?? {}

  const p = {
    tema: sinTema.length
      ? { estado: 'espera', corto: `${sinTema.length} sin tema`,
        resumen: `Falta tema: ${sinTema.map((t) => nombreCorto(t.fecha)).join(' y ')}. Lo ideal es tener los próximos 2 eventos con tema.` }
      : sinGuion.length
        ? { estado: 'espera', corto: 'Falta guion', resumen: `Falta el guion de: ${sinGuion.map((t) => `${nombreCorto(t.fecha)} (${t.tema})`).join(', ')}.` }
        : { estado: 'ok', corto: 'Con tema', resumen: temas[0] ? `Próximo tema: ${temas[0].tema}.` : 'Sin eventos próximos.' },
    difusion: agente('carrusel').error
      ? { estado: 'error', corto: 'Falló', resumen: agente('carrusel').mensaje }
      : { estado: 'ok', corto: pendTipo.carrusel ? `${pendTipo.carrusel} en bandeja` : 'Al día',
        resumen: agente('carrusel').mensaje || 'Se arma sola en cuanto el evento tiene tema.' },
    revision: { resumen: 'Palomea la lista el día del evento, antes de transmitir.' },
    turnos: agente('turnos').error
      ? { estado: 'error', corto: 'Falló el reparto', resumen: agente('turnos').mensaje }
      : huecos.length
        ? { estado: 'espera', corto: `${huecos.length} sin asignar`,
          resumen: `${plural(huecos.length, 'evento', 'eventos')} de las próximas 2 semanas sin quién dirija.` }
        : { estado: 'ok', corto: 'Asignados', resumen: 'Los próximos eventos ya tienen quién dirija.' },
    vivo: evento?.estado === 'en-vivo'
      ? { estado: 'activo', corto: 'En vivo ahora', resumen: `${evento.nombre}: en vivo ahora.` }
      : { estado: 'ok', corto: evento ? evento.faltan : 'Sin fecha', resumen: evento ? `Próximo: ${evento.nombre}, ${evento.faltan}.` : 'No hay eventos próximos.' },
    grabacion: obs.grabando
      ? { estado: 'activo', corto: 'Grabando', resumen: `OBS está grabando${obs.duracion ? ` (${obs.duracion.slice(0, 8)})` : ''}.` }
      : grabando
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
    carrusel: grabando
      ? { estado: 'activo', corto: 'En cola', resumen: 'Se arma en cuanto terminen los reels.' }
      : { estado: 'ok', corto: 'Al día', resumen: 'Sale solo junto con los reels de cada grabación.' },
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
    registro: { estado: 'ok', corto: 'Automático', resumen: 'La app guarda el registro de cada evento; descárgalo desde el reporte.' },
    mides: e.ultimo_reporte
      ? { estado: agente('reporte').error ? 'error' : 'ok', corto: 'Reporte listo', resumen: `Último reporte: ${e.ultimo_reporte.titulo}.` }
      : { estado: 'sin', corto: 'Primero el lunes', resumen: 'El primer reporte se arma solo el lunes a las 8 am. También puedes generarlo ahora.' },
  }

  p.turnos.detalle = [e.google ? 'Las invitaciones llegan por Google Calendar.' : 'Google Calendar sin conectar: no se envían invitaciones.', ultimaVez('turnos')]
  p.tema.detalle = [temas.slice(0, 4).map((t) => `${nombreCorto(t.fecha)}: ${t.tema ?? 'sin tema'}`).join(' · ') || null,
    e.ideas_nuevas ? `${plural(e.ideas_nuevas, 'idea guardada', 'ideas guardadas')} sin usar.` : null]
  p.difusion.detalle = [ultimaVez('carrusel')]
  p.grabacion.detalle = [obs.instalado === false ? 'OBS no está instalado en esta computadora.'
    : obs.conectado ? 'OBS conectado: graba solo de 9:55 a 11:05 los días de evento.' : (obs.mensaje || null)]
  p.grabacion.detalle.push(`${plural(Object.values(e.grabaciones_conteo ?? {}).reduce((a, b) => a + b, 0), 'grabación recibida', 'grabaciones recibidas')} en total.`)
  p.reels.detalle = [proximo('Reels') && `Próximos: ${fechaCorta(proximo('Reels').fecha)}, después de las 11 am.`, ultimaVez('reels')]
  p.bandeja.detalle = [`${plural(e.bandeja?.aprobado ?? 0, 'aprobado', 'aprobados')} · ${plural(e.bandeja?.rechazado ?? 0, 'rechazado', 'rechazados')}`]
  p.publicacion.detalle = [e.meta ? 'Facebook e Instagram conectados.' : 'Meta sin conectar: Facebook e Instagram quedan en su carpeta.', ultimaVez('publicacion')]
  p.mides.detalle = [e.ultimo_reporte?.mejorar ? `${plural(e.ultimo_reporte.mejorar, 'punto', 'puntos')} en «Qué mejorar».` : null, ultimaVez('reporte')]

  // Sin agentes corriendo, lo automático no avanza.
  if (estado && !e.worker_activo) {
    for (const id of ['difusion', 'grabacion', 'reels', 'carrusel', 'publicacion']) {
      if (p[id].estado === 'ok' || p[id].estado === 'activo') Object.assign(p[id], { estado: 'apagado', corto: 'Apagado' })
    }
  }

  const nodos = {
    'n-tema': p.tema, 'n-turnos': p.turnos, 'n-vivo': p.vivo, 'n-grab': p.grabacion, 'n-a1': p.reels,
    'n-a2': p.difusion, 'n-a3': p.carrusel, 'n-band': p.bandeja, 'n-pub': p.publicacion, 'n-reg': p.registro, 'n-rep': p.mides,
  }
  for (const n of NODOS) if (n.red) nodos[n.id] = porRed(n.red)
  if (!e.meta) for (const id of ['n-ig', 'n-fb']) nodos[id] ??= { estado: null, corto: 'En carpeta' }

  const pasos = PASOS.map((paso, i) => ({ ...paso, numero: i + 1, ...p[paso.id], detalle: (p[paso.id].detalle ?? []).filter(Boolean) }))
  return { pasos, nodos }
}
