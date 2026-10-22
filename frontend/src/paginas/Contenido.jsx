// Material (Gonza, 2026-10-19): las 5 imágenes de difusión y los 5 reels editados de cada evento.
// Se revisan, se ajusta el texto, se descargan y se suben a mano a cada red. Nada se publica solo.
import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { nombreFecha } from '../evento.js'
import { fechaDeClave, segundosATexto } from '../util.js'
import Modal from '../componentes/Modal.jsx'
import Prompter from '../componentes/Prompter.jsx'
import { enNube } from '../modo.js'

const VACIO = 'Todavía no hay material. Las 5 imágenes salen al guardar el tema y los 5 reels cuando llega el video del celular a grabaciones/.'
const TEXTO_MAX = 2200
const ESTADO_GRAB = { nueva: 'En espera', procesando: 'Editando…', lista: 'Reels listos', error: 'Con error' }
const REFRESCO_MS = 30_000

export default function Contenido() {
  const [paquetes, setPaquetes] = useState(null)
  const [grabaciones, setGrabaciones] = useState([])
  const [error, setError] = useState('')

  const cargar = useCallback((silencioso = false) => {
    if (!silencioso) { setPaquetes(null); setError('') }
    return api('/api/bandeja')
      .then((d) => setPaquetes(d.paquetes))
      .catch((e) => { if (!silencioso) { setError(e.message); setPaquetes([]) } })
  }, [])
  const cargarGrabaciones = useCallback(() => {
    api('/api/estado').then((d) => setGrabaciones(d.grabaciones)).catch(() => {})
  }, [])

  useEffect(() => { cargar(); cargarGrabaciones() }, [cargar, cargarGrabaciones])
  useEffect(() => {
    // Los agentes trabajan en segundo plano: se refresca solo cada 30 s.
    const t = setInterval(() => { if (!document.hidden) { cargar(true); cargarGrabaciones() } }, REFRESCO_MS)
    return () => clearInterval(t)
  }, [cargar, cargarGrabaciones])

  function actualizar(nuevo) {
    setPaquetes((lista) => lista.map((p) => (p.id === nuevo.id ? nuevo : p)))
  }

  return (
    <>
      <TarjetaPrompter />
      <section className="tarjeta">
        <span className="etiqueta">Material del evento</span>
        <p className="chico-texto" style={{ marginBottom: 0 }}>
          Aquí llegan las 5 imágenes de difusión y los 5 reels editados con el estilo del cliente. Revísalos, ajusta el
          texto si hace falta, descárgalos y súbelos a cada red.
        </p>
        {!enNube() && <Vaciar hayAlgo={!!paquetes?.length || grabaciones.length > 0} alTerminar={() => { cargar(); cargarGrabaciones() }} />}
      </section>

      {error && <p className="error" role="alert">{error}</p>}
      {paquetes === null && <p className="vacio">Cargando…</p>}
      {paquetes?.length === 0 && !error && <section className="tarjeta"><p className="vacio">{VACIO}</p></section>}
      {paquetes?.map((p) => <TarjetaPaquete key={p.id} paquete={p} alCambiar={actualizar} />)}

      {grabaciones.length > 0 && (
        <section className="tarjeta">
          <span className="etiqueta">Grabaciones recientes</span>
          <ul className="lista">
            {grabaciones.map((g) => (
              <li key={g.id} className="item">
                <div>
                  <b className="partir">{g.nombre}</b>
                  <span className="muted">{g.error || (g.duracion ? `Duración ${segundosATexto(g.duracion)}` : 'Esperando a que termine de copiarse')}</span>
                </div>
                <span className={`pill ${g.estado === 'lista' ? 'verde' : g.estado === 'error' ? 'ambar' : 'gris'}`}>{ESTADO_GRAB[g.estado]}</span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  )
}

/** Borra todo lo de Material para empezar de cero (pide escribir BORRAR). */
function Vaciar({ hayAlgo, alTerminar }) {
  const [abierto, setAbierto] = useState(false)
  const [texto, setTexto] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [mensaje, setMensaje] = useState('')
  const [error, setError] = useState('')
  const listo = texto.trim().toUpperCase() === 'BORRAR'

  async function vaciar() {
    setOcupado(true)
    setError('')
    try {
      const d = await api('/api/bandeja/vaciar', { metodo: 'POST', datos: { confirmar: texto } })
      setMensaje(`Material vacío: se borraron ${d.paquetes} piezas${d.grabaciones ? ` y ${d.grabaciones} grabaciones que ya no estaban en la carpeta` : ''}.`)
      setAbierto(false)
      setTexto('')
      alTerminar?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div className="vaciar">
      {mensaje && <p className="tema-aviso" role="status">{mensaje}</p>}
      {!abierto && hayAlgo && (
        <button className="enlace" onClick={() => { setAbierto(true); setMensaje('') }}>Vaciar Material (empezar de cero)</button>
      )}
      {abierto && (
        <div className="campo">
          <label htmlFor="vaciar-confirmar">Se borran todas las imágenes de difusión y los reels, con sus archivos. No se
            puede deshacer. Escribe BORRAR para confirmar.</label>
          <input id="vaciar-confirmar" value={texto} autoFocus autoComplete="off" disabled={ocupado} onChange={(e) => setTexto(e.target.value)} />
          <div className="botones">
            <button className="btn" disabled={ocupado || !listo} onClick={vaciar}>Borrar todo</button>
            <button className="btn suave" disabled={ocupado} onClick={() => { setAbierto(false); setTexto(''); setError('') }}>Cancelar</button>
          </div>
          {error && <p className="error" role="alert">{error}</p>}
        </div>
      )}
    </div>
  )
}

function nombreDescarga(p, archivo) {
  const titulo = p.titulo.replace(/[^\wáéíóúñü ]+/gi, '').trim().replace(/ +/g, '_')
  return `${p.fecha_evento}_${titulo}_${archivo}`
}

function TarjetaPaquete({ paquete: p, alCambiar }) {
  const [texto, setTexto] = useState(p.texto)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const modificado = texto !== p.texto

  // Si llega una versión nueva del servidor (p. ej. la cambió otra persona), se muestra esa.
  useEffect(() => { setTexto(p.texto) }, [p.texto, p.version])

  async function llamar(fn) {
    setOcupado(true)
    setError('')
    try {
      await fn()
    } catch (e) {
      setError(e.message)
      if (e.status === 409) {
        try { alCambiar((await api(`/api/bandeja/${p.id}`)).paquete) } catch { /* el error ya está en pantalla */ }
      }
    } finally {
      setOcupado(false)
    }
  }

  function guardar() {
    return llamar(async () => {
      alCambiar((await api(`/api/bandeja/${p.id}`, { metodo: 'PATCH', datos: { version: p.version, texto } })).paquete)
    })
  }

  return (
    <article className="tarjeta paquete" aria-labelledby={`paq-${p.id}`}>
      <div className="paq-cabeza">
        <span className={`pill ${p.tipo === 'reel' ? 'verde' : 'ambar'}`}>{p.tipo === 'reel' ? 'Reel' : 'Imágenes de difusión'}</span>
        <span className="muted chico-texto">Evento del {nombreFecha(fechaDeClave(p.fecha_evento)).toLowerCase()}</span>
      </div>
      <h3 id={`paq-${p.id}`}>{p.titulo}</h3>

      {enNube() && p.archivos.length > 0 && (
        <p className="tema-aviso">{p.archivos.length === 1 ? 'El archivo está' : `Los ${p.archivos.length} archivos están`} en la laptop: descárgalos desde ahí.</p>
      )}
      {!enNube() && p.archivos.length > 0 && (
        <div className="previas">
          {p.archivos.map((a) => {
            const src = `/api/bandeja/${p.id}/archivo/${encodeURIComponent(a)}?v=${p.version}`
            return a.toLowerCase().endsWith('.mp4')
              ? <video key={`${a}-${p.version}`} src={src} controls preload="metadata" playsInline />
              : <a key={a} href={src} target="_blank" rel="noreferrer"><img src={src} alt={`Imagen ${a.replace('.png', '')} de la difusión`} loading="lazy" /></a>
          })}
        </div>
      )}

      {p.tipo === 'reel' && p.datos.grabacion_id && (
        <Recorte paquete={p} ocupado={ocupado} llamar={llamar} alCambiar={alCambiar} />
      )}

      <div className="campo">
        <label htmlFor={`txt-${p.id}`}>Texto para publicar</label>
        <textarea id={`txt-${p.id}`} value={texto} maxLength={TEXTO_MAX} rows={6} disabled={ocupado}
          onChange={(e) => setTexto(e.target.value)} />
        <span className="chico-texto contador">{texto.length} / {TEXTO_MAX}</span>
      </div>

      {error && <p className="error" role="alert">{error}</p>}

      <div className="botones">
        {modificado && <button className="btn" disabled={ocupado} onClick={guardar}>Guardar texto</button>}
        {!enNube() && p.archivos.map((a) => (
          <a key={a} className="btn suave chico" download={nombreDescarga(p, a)}
            href={`/api/bandeja/${p.id}/archivo/${encodeURIComponent(a)}?v=${p.version}`}>Descargar {a}</a>
        ))}
      </div>
    </article>
  )
}

function Recorte({ paquete: p, ocupado, llamar, alCambiar }) {
  const [abierto, setAbierto] = useState(false)
  const [inicio, setInicio] = useState(String(p.datos.inicio))
  const [fin, setFin] = useState(String(p.datos.fin))
  const pidio = p.datos.recortar
  const duracion = Number(fin) - Number(inicio)

  function regenerar() {
    return llamar(async () => {
      const d = await api(`/api/bandeja/${p.id}/recortar`, {
        metodo: 'POST', datos: { version: p.version, inicio: Number(inicio), fin: Number(fin) },
      })
      alCambiar(d.paquete)
      setAbierto(false)
    })
  }

  return (
    <div className="recorte">
      <p className="chico-texto">
        Tomado de la grabación: del {segundosATexto(p.datos.inicio)} al {segundosATexto(p.datos.fin)}
        {' '}({Math.round(p.datos.fin - p.datos.inicio)} s).{' '}
        {!pidio && !abierto && <button className="enlace" onClick={() => setAbierto(true)}>Ajustar recorte</button>}
      </p>
      {pidio && <div className="estado off">Regenerando el video ({segundosATexto(pidio.inicio)} a {segundosATexto(pidio.fin)})… tarda 1 a 2 minutos.</div>}
      {p.datos.error_recorte && <p className="error">{p.datos.error_recorte}</p>}
      {abierto && !pidio && (
        <div className="recorte-campos">
          <div className="campo">
            <label htmlFor={`ini-${p.id}`}>Inicio (segundos)</label>
            <input id={`ini-${p.id}`} type="number" inputMode="decimal" step="0.5" min="0" value={inicio}
              onChange={(e) => setInicio(e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor={`fin-${p.id}`}>Fin (segundos)</label>
            <input id={`fin-${p.id}`} type="number" inputMode="decimal" step="0.5" min="0" value={fin}
              onChange={(e) => setFin(e.target.value)} />
          </div>
          <p className="chico-texto">Duración: {Number.isFinite(duracion) ? Math.round(duracion) : '–'} s (de 5 a 59 s).</p>
          <div className="botones">
            <button className="btn" disabled={ocupado} onClick={regenerar}>Regenerar video</button>
            <button className="btn suave" disabled={ocupado} onClick={() => setAbierto(false)}>Cancelar</button>
          </div>
        </div>
      )}
    </div>
  )
}


/** Primera tarjeta de Material (Gonza, 2026-10-20): el guion del evento que toca, en el Prompter. */
function TarjetaPrompter() {
  const [evento, setEvento] = useState(undefined) // undefined = cargando
  const [guion, setGuion] = useState('')
  const [abierto, setAbierto] = useState(false)

  useEffect(() => {
    api('/api/avance/activo')
      .then((a) => api(`/api/temas/${a.fecha}`).then((d) => { setEvento(a); setGuion(d.tema?.guion ?? '') }))
      .catch(() => setEvento(null))
  }, [])

  return (
    <section className="tarjeta prompter-tarjeta">
      <span className="etiqueta">Ver guion en Prompter</span>
      {evento === undefined && <p className="chico-texto">Cargando…</p>}
      {evento && (
        <>
          <p className="chico-texto">
            {evento.nombre}{evento.tema ? <> · <b>{evento.tema}</b></> : ''}.{' '}
            {guion.trim() ? 'El guion a pantalla completa, con letra grande que sube sola a la velocidad que elijas.'
              : 'Este evento todavía no tiene guion: agrégalo en Inicio, paso 2.'}
          </p>
          <div className="botones">
            <button className="btn" disabled={!guion.trim()} onClick={() => setAbierto(true)}>Abrir Prompter</button>
          </div>
        </>
      )}
      {evento === null && <p className="chico-texto">No se pudo cargar el evento.</p>}
      <Modal abierto={abierto} titulo={evento ? `Prompter · ${evento.tema || evento.nombre}` : 'Prompter'} ancho="completo" alCerrar={() => setAbierto(false)}>
        <Prompter texto={guion} />
      </Modal>
    </section>
  )
}
