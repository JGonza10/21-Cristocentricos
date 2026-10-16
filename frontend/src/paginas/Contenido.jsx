import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { nombreFecha } from '../rosario.js'

const FILTROS = [
  { id: 'pendiente', nombre: 'Pendientes' },
  { id: 'aprobado', nombre: 'Aprobados' },
  { id: 'rechazado', nombre: 'Rechazados' },
]
const VACIO = {
  pendiente: 'No hay paquetes por revisar. Aquí aparecerán los carruseles y reels que preparen los agentes.',
  aprobado: 'Todavía no apruebas ningún paquete.',
  rechazado: 'No hay paquetes rechazados.',
}
const TEXTO_MAX = 2200

const PASOS = [
  { fase: 3, titulo: 'Carruseles', texto: '5 imágenes blanco y vino por rosario, listas 2 días antes.' },
  { fase: 4, titulo: 'Reels', texto: '3 videos verticales con subtítulos de cada transmisión.' },
  { fase: 5, titulo: 'Publicación', texto: 'Carpeta por red social y subida directa a YouTube.' },
]

const fechaEvento = (iso) => nombreFecha(new Date(`${iso}T00:00:00Z`))
const fechaHora = (iso) => new Date(iso).toLocaleString('es-MX', {
  timeZone: 'America/Mexico_City', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit',
})

export default function Contenido() {
  const [filtro, setFiltro] = useState('pendiente')
  const [paquetes, setPaquetes] = useState(null)
  const [conteos, setConteos] = useState({ pendiente: 0, aprobado: 0, rechazado: 0 })
  const [error, setError] = useState('')

  useEffect(() => {
    let vigente = true
    setPaquetes(null)
    setError('')
    api(`/api/bandeja?estado=${filtro}`)
      .then((d) => { if (vigente) { setPaquetes(d.paquetes); setConteos(d.conteos) } })
      .catch((e) => { if (vigente) { setError(e.message); setPaquetes([]) } })
    return () => { vigente = false }
  }, [filtro])

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

      <section className="tarjeta">
        <span className="etiqueta">Lo que viene en esta sección</span>
        <ul className="lista">
          {PASOS.map((p) => (
            <li key={p.fase} className="item">
              <div><b>{p.titulo}<span className="pill">fase {p.fase}</span></b><span className="muted">{p.texto}</span></div>
            </li>
          ))}
        </ul>
      </section>
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

  async function hacer(accion) {
    setOcupado(true)
    setError('')
    try {
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
    } catch (e) {
      setError(e.message)
      if (e.status === 409) recargar()
    } finally {
      setOcupado(false)
    }
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
        <span className="muted chico-texto">Rosario del {fechaEvento(p.fecha_evento).toLowerCase()}</span>
      </div>
      <h3 id={`paq-${p.id}`}>{p.titulo}</h3>

      {p.archivos.length > 0 && (
        <div className="previas">
          {p.archivos.map((a) => {
            const src = `/api/bandeja/${p.id}/archivo/${encodeURIComponent(a)}`
            return a.toLowerCase().endsWith('.mp4')
              ? <video key={a} src={src} controls preload="metadata" playsInline />
              : <a key={a} href={src} target="_blank" rel="noreferrer"><img src={src} alt={`Vista previa ${a}`} loading="lazy" /></a>
          })}
        </div>
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
          <button className="btn" disabled={ocupado} onClick={() => hacer('aprobar')}>
            {modificado ? 'Guardar y aprobar' : 'Aprobar'}
          </button>
          {modificado && <button className="btn suave" disabled={ocupado} onClick={() => hacer('guardar')}>Guardar texto</button>}
          <button className="btn suave" disabled={ocupado} onClick={() => setRechazando(true)}>Rechazar</button>
        </>}
        {pendiente && rechazando && <>
          <button className="btn" disabled={ocupado} onClick={() => hacer('rechazar')}>Confirmar rechazo</button>
          <button className="btn suave" disabled={ocupado} onClick={() => { setRechazando(false); setMotivo('') }}>Cancelar</button>
        </>}
        {!pendiente && <button className="btn suave" disabled={ocupado} onClick={() => hacer('reabrir')}>Regresar a pendientes</button>}
      </div>
    </article>
  )
}
