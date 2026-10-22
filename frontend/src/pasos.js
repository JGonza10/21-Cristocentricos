// Flujo de trabajo de Inicio: recuadros, conexiones y pasos, y su estado en vivo a partir de /api/estado.
// El avance de cada evento (hecho / omitido / pendiente) viene de /api/avance.
//   Estados en vivo: ok = al día · activo = trabajando · espera = te necesita · error = falló
//                    apagado = agentes sin correr · sin = todavía no existe en el sistema
// Los 7 pasos de cada evento (Gonza, 2026-10-19).
import { fechaCorta, proximoEvento } from './evento.js'
import { fechaDeClave, fechaHora } from './util.js'

// k: disp = disparador · agente · humano = tú decides · plata = archivo o lo subes tú · hab = Claude te ayuda
export const NODOS = [
  { id: 'n-cal', x: 70, y: 170, k: 'humano', i: 'cal', t: 'Tema y fecha', s: 'En el calendario' },
  { id: 's-guion', x: 225, y: 170, k: 'hab', i: 'pen', t: 'Guion', s: 'Escrito o archivo', r: 30 },
  { id: 'n-dif', x: 380, y: 170, k: 'agente', i: 'img', t: 'Imágenes', s: '5 para redes' },
  { id: 's-lista', x: 535, y: 170, k: 'humano', i: 'check', t: 'Revisión técnica', s: 'Audio, cámara, celular', r: 30 },
  { id: 'n-vivo', x: 690, y: 170, k: 'disp', i: 'bolt', t: 'Evento en vivo', s: 'Lun y vie · 10 a 11 am' },
  { id: 'n-sy', x: 870, y: 60, k: 'plata', i: 'tv', t: 'StreamYard', s: 'Con cintillas: TV y redes', r: 30 },
  { id: 'n-cel', x: 870, y: 280, k: 'plata', i: 'folder', t: 'Celular', s: 'Limpio: a grabaciones/', r: 30 },
  { id: 's-estilo', x: 870, y: 440, k: 'plata', i: 'folder', t: 'Estilo del cliente', s: 'Referencia y herramientas', r: 28 },
  { id: 'n-reels', x: 1045, y: 280, k: 'agente', i: 'film', t: 'Reels con estilo', s: '5 reels editados' },
  { id: 'n-mat', x: 1205, y: 280, k: 'plata', i: 'folder', t: 'Material', s: 'Descargas y subes', r: 30 },
  { id: 's-ideas', x: 1350, y: 280, k: 'hab', i: 'pen', t: 'Ideas', s: 'Último paso', r: 28 },
]
export const LIENZO = { ancho: 1430, alto: 520 }

export const CONEXIONES = [
  { id: 'c1', a: 'n-cal', b: 's-guion' },
  { id: 'c2', a: 's-guion', b: 'n-dif' },
  { id: 'c3', a: 'n-dif', b: 's-lista' },
  { id: 'c4', a: 's-lista', b: 'n-vivo' },
  { id: 'c5', a: 'n-vivo', b: 'n-sy' },
  { id: 'c6', a: 'n-vivo', b: 'n-cel' },
  { id: 'c7', a: 'n-cel', b: 'n-reels' },
  { id: 'c8', a: 's-estilo', b: 'n-reels' },
  { id: 'c9', a: 'n-reels', b: 'n-mat', l: '5 reels' },
  { id: 'c11', a: 'n-mat', b: 's-ideas' },
]

// q: tu = lo haces tú · solo = se hace solo · hab = Claude te ayuda
export const PASOS = [
  { id: 'tema', n: ['n-cal'], v: [], q: 'tu', t: 'Tema y fecha',
    x: 'En el calendario se elige la fecha y se escribe el tema que se va a grabar, con la imagen del tema (la que va al centro de los reels, como el Santo Rostro). Al guardarlo se abre solo el paso del guion. Lo ideal: los próximos 2 eventos siempre con tema.' },
  { id: 'guion', n: ['s-guion'], v: ['c1'], q: 'hab', t: 'Agregar guion',
    x: 'Se abre una ventana para escribir o pegar el guion, o cargarlo desde un archivo (.docx, .pdf o .txt). Si no lo hay, «Preparar guion con Claude» copia las instrucciones para que Claude busque el tema en fuentes de la Iglesia (Biblia, Catecismo, Magisterio, santos) con sus citas, y arme el guion. Pégalo de vuelta y guarda. Si no hace falta guion, omite el paso.' },
  { id: 'difusion', n: ['n-dif'], v: ['c2'], q: 'solo', t: 'Crear imágenes',
    x: 'Las 5 imágenes de difusión del tema para redes sociales. «Crear imágenes» las hace al momento (y también salen solas al guardar el tema). Quedan en Material para descargarlas y subirlas; si cambias el tema, «Otra versión» las rehace.' },
  { id: 'revision', n: ['s-lista'], v: ['c3'], q: 'tu', t: 'Revisión técnica',
    x: 'Antes de transmitir se palomea la lista: audio, cámara y luz, internet, StreamYard, celular grabando la segunda toma, guion e intenciones a la mano y reloj.' },
  { id: 'grabacion', n: ['n-vivo', 'n-sy', 'n-cel'], v: ['c4', 'c5', 'c6', 'c7'], q: 'tu', t: 'Grabación: StreamYard y celular',
    x: 'StreamYard guarda el video como sale del stream (con cintillas): ese va al canal de TV y a la red social indicada. El celular graba la segunda toma limpia, sin cintillas: copia ese video a la carpeta grabaciones/ (o súbelo con «Subir grabación»). De ahí salen los reels.' },
  { id: 'reels', n: ['n-reels', 's-estilo', 'n-mat'], v: ['c8', 'c9'], q: 'solo', t: '5 reels con el estilo del cliente',
    x: 'Whisper escucha el video limpio, el sistema elige 5 momentos y edita cada reel igual que la referencia del cliente: sus imágenes y animaciones (carpeta estilo_cliente), mejora de luz y enfoque, sin ruido exterior y con volumen parejo. Quedan en Material.' },
  { id: 'ideas', n: ['s-ideas'], v: ['c11'], q: 'tu', t: 'Ideas del evento',
    x: 'Último paso: guarda en «Ideas» (arriba a la derecha) lo que surgió en el evento, escrito o por voz. Cualquier idea se puede volver el tema de un evento.' },
]

export const QUIEN = { tu: 'Lo haces tú', solo: 'Se hace solo', hab: 'Claude te ayuda' }
export const ESTADOS = {
  ok: 'Al día', activo: 'Trabajando', espera: 'Te necesita', error: 'Con error', apagado: 'Apagado', sin: 'Pendiente',
}
export const AVANCE = { hecho: 'Hecho', omitido: 'Omitido', pendiente: 'Pendiente' }

const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios}`

/** Estado en vivo: { pasos: [paso + {estado, corto, resumen, detalle}], nodos: {idNodo: {estado, corto}} } */
export function calcularVivo(estado, ahora = new Date()) {
  const e = estado ?? {}
  const agente = (n) => e.agentes?.find((a) => a.nombre === n) ?? {}
  const ultimaVez = (n) => (agente(n).ultimo_ok ? `Última vez: ${fechaHora(agente(n).ultimo_ok)}` : null)
  const evento = proximoEvento(ahora)
  const g0 = e.grabaciones?.[0]
  const trabajando = g0 && (g0.estado === 'nueva' || g0.estado === 'procesando')
  const temas = e.temas ?? []
  const sinTema = temas.slice(0, 2).filter((t) => !t.tema)
  const sinGuion = temas.slice(0, 2).filter((t) => t.tema && !t.guion)
  const nombreCorto = (clave) => fechaCorta(fechaDeClave(clave))
  const est = e.estilo ?? {}

  const p = {
    tema: sinTema.length
      ? { estado: 'espera', corto: `${sinTema.length} sin tema`,
        resumen: `Falta tema: ${sinTema.map((t) => nombreCorto(t.fecha)).join(' y ')}. Lo ideal es tener los próximos 2 eventos con tema.` }
      : { estado: 'ok', corto: 'Con tema', resumen: temas[0] ? `Próximo tema: ${temas[0].tema}.` : 'Sin eventos próximos.' },
    guion: sinGuion.length
      ? { estado: 'espera', corto: 'Sin guion', resumen: `Sin guion: ${sinGuion.map((t) => `${nombreCorto(t.fecha)} (${t.tema})`).join(', ')}. Si no lo hay, pídele ayuda a Claude.` }
      : { estado: 'ok', corto: 'Al día', resumen: 'Los próximos eventos con tema ya tienen guion.' },
    difusion: agente('carrusel').error
      ? { estado: 'error', corto: 'Falló', resumen: agente('carrusel').mensaje }
      : { estado: 'ok', corto: 'Al día', resumen: 'Las 5 imágenes salen solas en cuanto se guarda el tema.' },
    revision: { resumen: 'Palomea la lista el día del evento, antes de transmitir.' },
    grabacion: trabajando
      ? { estado: 'activo', corto: 'Recibida', resumen: `Llegó ${g0.nombre}; se están editando los reels.` }
      : g0?.estado === 'error'
        ? { estado: 'error', corto: 'Falló', resumen: g0.error || `No se pudo procesar ${g0.nombre}.` }
        : { estado: 'ok', corto: g0 ? 'Lista' : 'Esperando',
          resumen: g0 ? `Última grabación: ${g0.nombre}.` : 'Esperando el video limpio del celular en grabaciones/.' },
    reels: agente('reels').error
      ? { estado: 'error', corto: 'Falló', resumen: agente('reels').mensaje }
      : trabajando
        ? { estado: 'activo', corto: 'Editando', resumen: 'Transcribiendo, eligiendo los 5 momentos y editando con el estilo del cliente.' }
        : { estado: 'ok', corto: 'Al día', resumen: agente('reels').mensaje || 'Esperando grabaciones.' },
    ideas: { estado: 'ok', corto: e.ideas_nuevas ? `${e.ideas_nuevas} sin usar` : 'Al día',
      resumen: e.ideas_nuevas ? `${plural(e.ideas_nuevas, 'idea guardada', 'ideas guardadas')} sin usar.` : 'Guarda las ideas del evento en «Ideas».' },
  }

  p.tema.detalle = [temas.slice(0, 4).map((t) => `${nombreCorto(t.fecha)}: ${t.tema ?? 'sin tema'}`).join(' · ') || null]
  p.difusion.detalle = [ultimaVez('carrusel')]
  p.grabacion.detalle = [evento ? `Próximo evento: ${evento.nombre}, ${evento.faltan}.` : null,
    `${plural(Object.values(e.grabaciones_conteo ?? {}).reduce((a, b) => a + b, 0), 'grabación recibida', 'grabaciones recibidas')} en total.`]
  p.reels.detalle = [
    est.referencia ? `Estilo del cliente: ${plural(est.referencia, 'video de referencia', 'videos de referencia')} y ${plural(est.herramientas ?? 0, 'herramienta', 'herramientas')}.`
      : 'Aún no está el video de referencia del cliente en estilo_cliente/referencia.',
    est.error ? `estilo.json: ${est.error}` : null,
    ultimaVez('reels')]
  if (est.error) Object.assign(p.reels, { estado: 'error', corto: 'Revisa estilo.json' })

  // Sin agentes corriendo, lo automático no avanza.
  if (estado && !e.worker_activo) {
    for (const id of ['difusion', 'reels']) {
      if (p[id].estado === 'ok' || p[id].estado === 'activo') Object.assign(p[id], { estado: 'apagado', corto: 'Apagado' })
    }
  }

  const nodos = {
    'n-cal': p.tema, 's-guion': p.guion, 'n-dif': p.difusion, 'n-cel': p.grabacion, 'n-reels': p.reels,
    's-ideas': p.ideas,
  }
  const pasos = PASOS.map((paso, i) => ({ ...paso, numero: i + 1, ...p[paso.id], detalle: (p[paso.id].detalle ?? []).filter(Boolean) }))
  return { pasos, nodos }
}
