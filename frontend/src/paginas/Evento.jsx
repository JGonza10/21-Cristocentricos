import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { nombreFecha } from '../fechas.js'

const PASOS = [
  { id: 'datos', titulo: 'Fecha, tema y guion' },
  { id: 'imagenes', titulo: 'Imágenes de difusión' },
  { id: 'revision', titulo: 'Revisión técnica del día' },
]

export default function Evento({ fecha, ir }) {
  const [ev, setEv] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setEv(null)
    setError('')
    api(`/api/eventos/${fecha}`).then((d) => setEv(d.evento)).catch((e) => setError(e.message))
  }, [fecha])

  if (error && !ev) return <section className="tarjeta"><p className="error">{error}</p></section>
  if (!ev) return <section className="tarjeta"><p className="vacio">Cargando evento…</p></section>

  const listos = PASOS.filter((p) => ev.pasos[p.id]).length
  const abierto = PASOS.find((p) => !ev.pasos[p.id])?.id ?? 'listo'

  return (
    <>
      <section className="hero">
        <div className="etiqueta">Evento · paso {Math.min(listos + 1, 3)} de 3</div>
        <h1>{ev.tema || 'Sin tema todavía'}</h1>
        <p className="meta">{nombreFecha(ev.fecha)} · {ev.hora} hrs</p>
        <ol className="avance" aria-label="Avance de los pasos">
          {PASOS.map((p, i) => (
            <li key={p.id} className={ev.pasos[p.id] ? 'hecho' : abierto === p.id ? 'actual' : ''}>
              <span>{i + 1}</span>{p.titulo}
            </li>
          ))}
        </ol>
      </section>

      <PasoDatos ev={ev} setEv={setEv} ir={ir} abierto={abierto === 'datos'} />
      <PasoImagenes ev={ev} setEv={setEv} bloqueado={!ev.pasos.datos} />
      <PasoRevision ev={ev} setEv={setEv} bloqueado={!ev.pasos.imagenes} ir={ir} />

      {ev.pasos.revision && (
        <section className="tarjeta paso">
          <p className="estado ok">Todo listo para transmitir</p>
          <p className="chico-texto">Al terminar, descarga la grabación de StreamYard y guárdala para los reels.</p>
        </section>
      )}
    </>
  )
}

function Encabezado({ numero, titulo, hecho }) {
  return (
    <div className="paso-cab">
      <span className={`paso-num ${hecho ? 'hecho' : ''}`}>{hecho ? '✓' : numero}</span>
      <h2>{titulo}</h2>
      {hecho && <span className="pill verde">listo</span>}
    </div>
  )
}

function Bloqueo({ texto }) {
  return <p className="estado off">{texto}</p>
}

function PasoDatos({ ev, setEv, ir, abierto }) {
  const [tema, setTema] = useState(ev.tema)
  const [hora, setHora] = useState(ev.hora)
  const [guion, setGuion] = useState(ev.guion_md)
  const [frases, setFrases] = useState(ev.frases)
  const [verGuion, setVerGuion] = useState(abierto)
  const [msg, setMsg] = useState({ texto: '', error: false })
  const [ocupado, setOcupado] = useState(false)

  // Al subir el guion o sugerir frases solo cambian guion y frases: lo que escribiste sin guardar se queda.
  function cargar(e, todo = true) {
    if (todo) { setTema(e.tema); setHora(e.hora) }
    setGuion(e.guion_md); setFrases(e.frases); setEv(e)
  }

  async function correr(accion, exito, todo = false) {
    setOcupado(true)
    setMsg({ texto: '', error: false })
    try {
      const d = await accion()
      cargar(d.evento, todo)
      setMsg({ texto: exito, error: false })
    } catch (e) {
      setMsg({ texto: e.message, error: true })
    } finally {
      setOcupado(false)
    }
  }

  const guardar = (e) => {
    e.preventDefault()
    correr(() => api(`/api/eventos/${ev.fecha}`, { metodo: 'PUT', datos: { tema, hora, guion_md: guion, frases: frases.filter((f) => f.trim()) } }),
      'Guardado.', true)
  }

  const subir = (e) => {
    const archivo = e.target.files[0]
    e.target.value = ''
    if (archivo) correr(() => api(`/api/eventos/${ev.fecha}/guion`, { metodo: 'POST', archivo }),
      'Guion cargado y convertido. Revisa el texto y las frases.')
  }

  const sugerir = () => correr(() => api(`/api/eventos/${ev.fecha}/frases`, { metodo: 'POST' }), 'Frases sugeridas desde el guion.')

  return (
    <section className="tarjeta paso">
      <Encabezado numero={1} titulo="Fecha, tema y guion" hecho={ev.pasos.datos} />
      <form className="formulario" onSubmit={guardar}>
        <div className="fila-2">
          <div className="campo">
            <label htmlFor="ev-fecha">Fecha del evento</label>
            <input id="ev-fecha" type="date" value={ev.fecha} required
              onChange={(e) => e.target.value && ir('evento', e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor="ev-hora">Hora</label>
            <input id="ev-hora" type="time" value={hora} required onChange={(e) => setHora(e.target.value)} />
          </div>
        </div>
        <div className="campo">
          <label htmlFor="ev-tema">Tema</label>
          <input id="ev-tema" maxLength={120} value={tema} placeholder="Ej. No tengas miedo" required onChange={(e) => setTema(e.target.value)} />
        </div>

        <div className="campo">
          <span className="label">Guion</span>
          <div className="acciones-fila">
            <label className="btn suave chico archivo">
              Subir PDF o .md
              <input type="file" accept=".pdf,.md,.txt,application/pdf,text/markdown,text/plain" onChange={subir} disabled={ocupado} />
            </label>
            <button type="button" className="btn suave chico" onClick={() => setVerGuion(!verGuion)}>
              {verGuion ? 'Ocultar texto' : guion ? 'Ver y editar texto' : 'Pegar texto'}
            </button>
          </div>
          <p className="chico-texto">
            {guion ? `${guion.split(/\s+/).length} palabras.` : 'Sin guion todavía.'} Las líneas con «&gt;» son indicaciones:
            el prompter las muestra en otro color y no las sigue. Se quitan solas «intenciones recibidas» y «cita bíblica».
          </p>
          {verGuion && (
            <textarea aria-label="Texto del guion" rows={14} value={guion} onChange={(e) => setGuion(e.target.value)}
              placeholder={'## Saludo\n\n¡Hola, qué tal! Buenos días…\n\n> Indicación que no se lee'} />
          )}
        </div>

        <div className="campo">
          <span className="label">Frases para difusión</span>
          <ul className="frases">
            {frases.map((f, i) => (
              <li key={i}>
                <input aria-label={`Frase ${i + 1}`} maxLength={200} value={f}
                  onChange={(e) => setFrases(frases.map((x, j) => (j === i ? e.target.value : x)))} />
                <button type="button" className="btn suave chico" aria-label={`Quitar frase ${i + 1}`}
                  onClick={() => setFrases(frases.filter((_, j) => j !== i))}>✕</button>
              </li>
            ))}
          </ul>
          <div className="acciones-fila">
            <button type="button" className="btn suave chico" disabled={frases.length >= 20} onClick={() => setFrases([...frases, ''])}>Agregar frase</button>
            <button type="button" className="btn suave chico" disabled={ocupado || !ev.guion_md} onClick={sugerir}>Sugerir del guion</button>
          </div>
          <p className="chico-texto">Las 2 primeras salen en las imágenes de difusión.</p>
        </div>

        <div className="acciones-fila">
          <button className="btn" disabled={ocupado}>{ocupado ? 'Guardando…' : 'Guardar paso 1'}</button>
          <p className={msg.error ? 'error' : 'chico-texto'} role="status">{msg.texto}</p>
        </div>
      </form>
    </section>
  )
}

function PasoImagenes({ ev, setEv, bloqueado }) {
  const [ocupado, setOcupado] = useState(false)
  const [msg, setMsg] = useState('')
  const [version, setVersion] = useState(() => Date.now())

  async function generar() {
    setOcupado(true)
    setMsg('')
    try {
      const d = await api(`/api/eventos/${ev.fecha}/imagenes`, { metodo: 'POST' })
      setEv(d.evento)
      setVersion(Date.now())
    } catch (e) {
      setMsg(e.message)
    } finally {
      setOcupado(false)
    }
  }

  const desactualizadas = ev.imagenes.length > 0 && !ev.pasos.imagenes
  return (
    <section className={`tarjeta paso ${bloqueado ? 'bloqueado' : ''}`}>
      <Encabezado numero={2} titulo="Imágenes de difusión" hecho={ev.pasos.imagenes} />
      {bloqueado ? <Bloqueo texto="Completa el paso 1 para generarlas." /> : (
        <>
          <p className="chico-texto">5 imágenes en blanco y vino con el tema, la fecha y la hora: invitación, 2 frases, en vivo y cierre.</p>
          {desactualizadas && <p className="estado warn">Cambiaste el tema, la fecha o las frases: vuelve a generarlas.</p>}
          {ev.imagenes.length > 0 && (
            <div className="galeria">
              {ev.imagenes.map((src, i) => (
                <a key={src} href={`${src}?v=${version}`} target="_blank" rel="noreferrer">
                  <img src={`${src}?v=${version}`} alt={`Imagen ${i + 1} de 5`} loading="lazy" />
                </a>
              ))}
            </div>
          )}
          <div className="acciones-fila">
            <button className="btn" onClick={generar} disabled={ocupado}>
              {ocupado ? 'Generando…' : ev.imagenes.length ? 'Volver a generar' : 'Generar imágenes'}
            </button>
            {msg && <p className="error">{msg}</p>}
          </div>
        </>
      )}
    </section>
  )
}

function PasoRevision({ ev, setEv, bloqueado, ir }) {
  const [msg, setMsg] = useState('')

  async function marcar(id, valor) {
    setMsg('')
    const antes = ev
    setEv({ ...ev, revision: { ...ev.revision, [id]: valor } }) // la palomita se ve al instante
    try {
      const d = await api(`/api/eventos/${ev.fecha}/revision`, { metodo: 'PUT', datos: { [id]: valor } })
      setEv(d.evento)
    } catch (e) {
      setEv(antes)
      setMsg(e.message)
    }
  }

  return (
    <section className={`tarjeta paso ${bloqueado ? 'bloqueado' : ''}`}>
      <Encabezado numero={3} titulo="Revisión técnica del día" hecho={ev.pasos.revision} />
      {bloqueado ? <Bloqueo texto="Completa el paso 2 para empezar la revisión." /> : (
        <>
          <ul className="lista">
            {ev.revision_items.map((r) => (
              <li key={r.id} className="item check">
                <label>
                  <input type="checkbox" checked={!!ev.revision[r.id]} onChange={(e) => marcar(r.id, e.target.checked)} />
                  <span>{r.texto}</span>
                </label>
                {r.id === 'prompter' && (
                  <button className="btn chico" onClick={() => ir('prompter', ev.fecha)}>Abrir prompter</button>
                )}
              </li>
            ))}
          </ul>
          <p className="chico-texto">El prompter avanza solo al escuchar la lectura y se puede pausar. En la tableta usa Chrome o Safari y entra por la dirección de Tailscale (https) para que funcione el micrófono.</p>
          {msg && <p className="error">{msg}</p>}
        </>
      )}
    </section>
  )
}
