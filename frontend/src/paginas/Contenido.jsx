import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { nombreFecha } from '../evento.js'
import { REDES, fechaDeClave, fechaHora, segundosATexto } from '../util.js'

const FILTROS = [
  { id: 'pendiente', nombre: 'Pendientes' },
  { id: 'aprobado', nombre: 'Aprobados' },
  { id: 'rechazado', nombre: 'Rechazados' },
]
const VACIO = {
  pendiente: 'No hay paquetes por revisar. Aquí aparecen los carruseles (2 días antes de cada evento) y los reels (cuando llega la grabación).',
  aprobado: 'Todavía no apruebas ningún paquete.',
  rechazado: 'No hay paquetes rechazados.',
}
const TEXTO_MAX = 2200
const REDES_POR_TIPO = { carrusel: ['instagram', 'facebook', 'tiktok'], reel: ['instagram', 'facebook', 'tiktok', 'youtube'] }
const ESTADO_PUB = {
  listo_manual: { texto: 'Listo para subir', clase: 'warn' },
  subiendo: { texto: 'Subiendo…', clase: 'off' },
  publicado: { texto: 'Publicado', clase: 'ok' },
  error: { texto: 'Con error', clase: 'warn' },
}
const ESTADO_GRAB = { nueva: 'En espera', procesando: 'Procesando…', lista: 'Reels listos', error: 'Con error' }
const REFRESCO_MS = 30_000

export default function Contenido() {
  const [filtro, setFiltro] = useState('pendiente')
  const [paquetes, setPaquetes] = useState(null)
  const [conteos, setConteos] = useState({ pendiente: 0, aprobado: 0, rechazado: 0 })
  const [grabaciones, setGrabaciones] = useState([])
  const [error, setError] = useState('')

  const cargar = useCallback((silencioso = false) => {
    if (!silencioso) { setPaquetes(null); setError('') }
    return api(`/api/bandeja?estado=${filtro}`)
      .then((d) => { setPaquetes(d.paquetes); setConteos(d.conteos) })
      .catch((e) => { if (!silencioso) { setError(e.message); setPaquetes([]) } })
  }, [filtro])

  useEffect(() => { cargar() }, [cargar])
  useEffect(() => {
    // Los agentes trabajan en segundo plano: se refresca solo cada 30 s.
    const t = setInterval(() => { if (!document.hidden) cargar(true) }, REFRESCO_MS)
    return () => clearInterval(t)
  }, [cargar])
  useEffect(() => { api('/api/estado').then((d) => setGrabaciones(d.grabaciones)).catch(() => {}) }, [])

  function actualizar(nuevo, nuevosConteos) {
    setPaquetes((lista) => (nuevo.estado === filtro
      ? lista.map((p) => (p.id === nuevo.id ? nuevo : p))
      : lista.filter((p) => p.id !== nuevo.id)))
    if (nuevosConteos) setConteos(nuevosConteos)
  }

  return (
    <>
      <section className="tarjeta">
        <span className="etiqueta">Bandeja de aprobación</span>
        <p className="chico-texto" style={{ marginBottom: 14 }}>
          Nada se publica sin el visto bueno de alguno de los dos. Revisa, corrige el texto si hace falta y aprueba.
        </p>
        <div className="filtros" role="group" aria-label="Filtrar por estado">
          {FILTROS.map((f) => (
            <button key={f.id} aria-pressed={filtro === f.id} onClick={() => setFiltro(f.id)}>
              {f.nombre} <span className="cuenta">{conteos[f.id]}</span>
            </button>
          ))}
        </div>
      </section>

      {error && <p className="error" role="alert">{error}</p>}
      {paquetes === null && <p className="vacio">Cargando…</p>}
      {paquetes?.length === 0 && !error && <section className="tarjeta"><p className="vacio">{VACIO[filtro]}</p></section>}
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

function TarjetaPaquete({ paquete: p, alCambiar }) {
  const [texto, setTexto] = useState(p.texto)
  const [rechazando, setRechazando] = useState(false)
  const [motivo, setMotivo] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const pendiente = p.estado === 'pendiente'
  const modificado = texto !== p.texto

  // Si llega una versión nueva del servidor (p. ej. la cambió el otro aprobador), se muestra esa.
  useEffect(() => { setTexto(p.texto) }, [p.texto, p.version])

  async function llamar(fn) {
    setOcupado(true)
    setError('')
    try {
      await fn()
    } catch (e) {
      setError(e.message)
      if (e.status === 409) recargar()
    } finally {
      setOcupado(false)
    }
  }

  function hacer(accion) {
    return llamar(async () => {
      let actual = p
      if (accion !== 'reabrir' && modificado) {
        actual = (await api(`/api/bandeja/${p.id}`, { metodo: 'PATCH', datos: { version: p.version, texto } })).paquete
        alCambiar(actual)
        if (accion === 'guardar') return
      }
      const d = await api(`/api/bandeja/${p.id}/${accion}`, {
        metodo: 'POST', datos: { version: actual.version, ...(accion === 'rechazar' ? { motivo } : {}) },
      })
      alCambiar(d.paquete, d.conteos)
    })
  }

  async function recargar() {
    try {
      const d = await api(`/api/bandeja/${p.id}`)
      alCambiar(d.paquete, (await api('/api/bandeja/conteos')).conteos)
    } catch { /* el mensaje de error ya está en pantalla */ }
  }

  return (
    <article className="tarjeta paquete" aria-labelledby={`paq-${p.id}`}>
      <div className="paq-cabeza">
        <span className="pill">{p.tipo}</span>
        <span className="muted chico-texto">Evento del {nombreFecha(fechaDeClave(p.fecha_evento)).toLowerCase()}</span>
      </div>
      <h3 id={`paq-${p.id}`}>{p.titulo}</h3>

      {p.archivos.length > 0 && (
        <div className="previas">
          {p.archivos.map((a) => {
            const src = `/api/bandeja/${p.id}/archivo/${encodeURIComponent(a)}?v=${p.version}`
            return a.toLowerCase().endsWith('.mp4')
              ? <video key={`${a}-${p.version}`} src={src} controls preload="metadata" playsInline />
              : <a key={a} href={src} target="_blank" rel="noreferrer"><img src={src} alt={`Imagen ${a.replace('.png', '')} del carrusel`} loading="lazy" /></a>
          })}
        </div>
      )}

      {pendiente && p.tipo === 'reel' && p.datos.grabacion_id && (
        <Recorte paquete={p} ocupado={ocupado} llamar={llamar} alCambiar={alCambiar} />
      )}

      {pendiente ? (
        <div className="campo">
          <label htmlFor={`txt-${p.id}`}>Texto para publicar</label>
          <textarea id={`txt-${p.id}`} value={texto} maxLength={TEXTO_MAX} rows={6} disabled={ocupado}
            onChange={(e) => setTexto(e.target.value)} />
          <span className="chico-texto contador">{texto.length} / {TEXTO_MAX}</span>
        </div>
      ) : (
        <>
          <p className="texto-final">{p.texto || <span className="muted">Sin texto.</span>}</p>
          <div className={`estado ${p.estado === 'aprobado' ? 'ok' : 'off'}`}>
            {p.estado === 'aprobado' ? 'Aprobado' : 'Rechazado'} por {p.revisado_por} · {fechaHora(p.revisado_en)}
          </div>
          {p.motivo_rechazo && <p className="chico-texto">Motivo: {p.motivo_rechazo}</p>}
        </>
      )}

      {p.estado === 'aprobado' && <Publicaciones paquete={p} ocupado={ocupado} llamar={llamar} alCambiar={alCambiar} />}

      {pendiente && rechazando && (
        <div className="campo">
          <label htmlFor={`mot-${p.id}`}>¿Por qué lo rechazas? (opcional)</label>
          <input id={`mot-${p.id}`} value={motivo} maxLength={300} disabled={ocupado} autoFocus
            onChange={(e) => setMotivo(e.target.value)} placeholder="Ej. el recorte corta la oración" />
        </div>
      )}

      {error && <p className="error" role="alert">{error}</p>}

      <div className="botones">
        {pendiente && !rechazando && <>
          <button className="btn" disabled={ocupado || !!p.datos.recortar} onClick={() => hacer('aprobar')}>
            {modificado ? 'Guardar y aprobar' : 'Aprobar'}
          </button>
          {modificado && <button className="btn suave" disabled={ocupado} onClick={() => hacer('guardar')}>Guardar texto</button>}
          <button className="btn suave" disabled={ocupado} onClick={() => setRechazando(true)}>Rechazar</button>
        </>}
        {pendiente && rechazando && <>
          <button className="btn" disabled={ocupado} onClick={() => hacer('rechazar')}>Confirmar rechazo</button>
          <button className="btn suave" disabled={ocupado} onClick={() => { setRechazando(false); setMotivo('') }}>Cancelar</button>
        </>}
        {!pendiente && !p.publicaciones.some((x) => x.estado === 'publicado' || x.estado === 'subiendo') &&
          <button className="btn suave" disabled={ocupado} onClick={() => hacer('reabrir')}>Regresar a pendientes</button>}
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

function Publicaciones({ paquete: p, ocupado, llamar, alCambiar }) {
  const porRed = Object.fromEntries(p.publicaciones.map((x) => [x.red, x]))
  const redes = REDES_POR_TIPO[p.tipo]

  function marcar(red, accion) {
    return llamar(async () => {
      const d = await api(`/api/bandeja/${p.id}/publicaciones/${red}`, { metodo: 'POST', datos: { accion } })
      alCambiar(d.paquete)
    })
  }

  return (
    <div>
      <span className="etiqueta">Publicación</span>
      {p.publicaciones.length === 0 && (
        <p className="chico-texto" style={{ marginTop: 6 }}>El agente de publicación lo prepara en unos minutos (la ventana de agentes debe estar abierta).</p>
      )}
      <ul className="lista" style={{ marginTop: 8 }}>
        {redes.filter((r) => porRed[r]).map((red) => {
          const pub = porRed[red]
          const e = ESTADO_PUB[pub.estado]
          return (
            <li key={red} className="item pub">
              <div>
                <b>{REDES[red]}</b>
                <span className={`estado ${e.clase}`}>{e.texto}</span>
                {pub.error && <span className="muted">{pub.error}</span>}
                {pub.estado === 'listo_manual' && pub.ruta && <code className="ruta">paquetes/{pub.ruta}</code>}
              </div>
              {pub.estado === 'listo_manual' && <button className="btn suave chico" disabled={ocupado} onClick={() => marcar(red, 'subido')}>Ya lo subí</button>}
              {pub.estado === 'error' && <button className="btn suave chico" disabled={ocupado} onClick={() => marcar(red, 'reintentar')}>Reintentar</button>}
              {pub.estado === 'publicado' && pub.url && <a className="btn suave chico" href={pub.url} target="_blank" rel="noreferrer">Ver</a>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}
