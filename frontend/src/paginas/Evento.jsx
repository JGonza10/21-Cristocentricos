import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { infoRosario, proximoRosario } from '../rosario.js'
import { cuenta, estadoReloj, horaCDMX } from '../reloj/tiempo.js'
import { fechaDeClave, nombres } from '../util.js'

const TEMAS = [
  { id: 'oscuro', nombre: 'Oscuro' },
  { id: 'perla', nombre: 'Perla' },
  { id: 'chroma', nombre: 'Verde chroma' },
]
const MAX_APOYOS = 3

export default function Evento({ fecha, ir }) {
  const r = fecha ? infoRosario(fechaDeClave(fecha)) : proximoRosario()
  if (!r) return <section className="tarjeta"><p className="vacio">No hay eventos próximos.</p></section>
  const yaPaso = r.estado === 'pasado' || r.estado === 'hoy-terminado'
  return (
    <>
      <section className="hero">
        <div className="etiqueta">{r.estado === 'en-vivo' ? 'En vivo ahora' : 'Evento'}</div>
        <h1>{r.nombre}</h1>
        <p className="meta" style={{ margin: 0 }}>10:00 a 11:00 am · {r.misterios} · {r.faltan}</p>
      </section>
      <Turnos clave={r.clave} yaPaso={yaPaso} ir={ir} />
      <Reloj />
    </>
  )
}

function Turnos({ clave, yaPaso, ir }) {
  const [turno, setTurno] = useState(null)
  const [equipo, setEquipo] = useState(null)
  const [editando, setEditando] = useState(false)
  const [dirige, setDirige] = useState('')
  const [apoyan, setApoyan] = useState([])
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    setTurno(null)
    setEditando(false)
    setError('')
    setAviso('')
    Promise.all([api(`/api/turnos?desde=${clave}&hasta=${clave}`), api('/api/equipo')])
      .then(([t, e]) => { setTurno(t.turnos[clave]); setEquipo(e.integrantes.filter((i) => i.activo)) })
      .catch((e) => setError(e.message))
  }, [clave])

  function empezar() {
    setDirige(turno?.dirige ? String(turno.dirige.id) : '')
    setApoyan(turno?.apoyan.map((i) => i.id) ?? [])
    setEditando(true)
    setAviso('')
  }

  function alternarApoyo(id) {
    setApoyan((lista) => (lista.includes(id) ? lista.filter((x) => x !== id) : [...lista, id]))
  }

  async function guardar() {
    setOcupado(true)
    setError('')
    try {
      const d = await api(`/api/turnos/${clave}`, {
        metodo: 'PUT', datos: { dirige: dirige ? Number(dirige) : null, apoyan: apoyan.filter((x) => String(x) !== dirige) },
      })
      setTurno(d.turno)
      setEditando(false)
      setAviso('Turnos guardados.')
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
    }
  }

  if (turno === null && !error) return <section className="tarjeta"><p className="vacio">Cargando turnos…</p></section>
  const inv = turno?.invitacion

  return (
    <section className="tarjeta">
      <span className="etiqueta">Turnos</span>
      {!editando ? (
        <>
          <div className="dos">
            <div>
              <h3>Dirige</h3>
              {turno?.dirige ? <div className="estado ok">{turno.dirige.nombre}</div> : <div className="estado warn">Sin asignar</div>}
            </div>
            <div>
              <h3>Apoya</h3>
              {turno?.apoyan.length ? <div className="estado ok">{nombres(turno.apoyan)}</div> : <div className="estado warn">Sin asignar</div>}
            </div>
          </div>
          <p className="chico-texto" style={{ marginTop: 10 }}>
            {turno?.automatico ? 'Asignado automáticamente el domingo. ' : ''}
            {inv?.estado === 'enviada' && 'Invitación enviada a su calendario.'}
            {inv?.estado === 'error' && inv.error}
            {!inv && (turno?.dirige || turno?.apoyan.length) ? 'La invitación se envía cuando Google Calendar esté conectado.' : ''}
          </p>
          {aviso && <p className="chico-texto" role="status">{aviso}</p>}
          {!yaPaso && (
            <div className="botones" style={{ marginTop: 12 }}>
              <button className="btn" onClick={empezar} disabled={!equipo}>{turno?.dirige ? 'Cambiar turnos' : 'Asignar turnos'}</button>
            </div>
          )}
        </>
      ) : equipo.length === 0 ? (
        <p className="vacio">
          Primero agrega a los integrantes del equipo en{' '}
          <button className="enlace" onClick={() => ir('configuracion')}>Ajustes</button>.
        </p>
      ) : (
        <div className="formulario">
          <div className="campo">
            <label htmlFor="dirige">¿Quién dirige?</label>
            <select id="dirige" value={dirige} onChange={(e) => setDirige(e.target.value)} disabled={ocupado}>
              <option value="">Sin asignar</option>
              {equipo.filter((i) => i.puede_dirigir).map((i) => <option key={i.id} value={i.id}>{i.nombre}</option>)}
            </select>
          </div>
          <fieldset className="campo">
            <legend>¿Quién apoya? (hasta {MAX_APOYOS})</legend>
            {equipo.filter((i) => String(i.id) !== dirige).map((i) => (
              <label key={i.id} className="casilla">
                <input type="checkbox" checked={apoyan.includes(i.id)} disabled={ocupado || (!apoyan.includes(i.id) && apoyan.length >= MAX_APOYOS)}
                  onChange={() => alternarApoyo(i.id)} />
                {i.nombre}
              </label>
            ))}
          </fieldset>
          {error && <p className="error" role="alert">{error}</p>}
          <div className="botones">
            <button className="btn" onClick={guardar} disabled={ocupado}>Guardar turnos</button>
            <button className="btn suave" onClick={() => setEditando(false)} disabled={ocupado}>Cancelar</button>
          </div>
        </div>
      )}
      {!editando && error && <p className="error" role="alert">{error}</p>}
    </section>
  )
}

function Reloj() {
  const [ahora, setAhora] = useState(() => new Date())
  const [copiado, setCopiado] = useState('')
  useEffect(() => {
    const t = setInterval(() => setAhora(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  const e = estadoReloj(ahora)
  const base = `${window.location.origin}/reloj`

  async function copiar(url, tema) {
    try {
      await navigator.clipboard.writeText(url)
      setCopiado(tema)
    } catch {
      setCopiado('')
    }
  }

  return (
    <section className="tarjeta">
      <span className="etiqueta">Reloj en vivo</span>
      <div className="reloj-grande" aria-live="off">{horaCDMX(ahora)}</div>
      <p className="chico-texto">Hora de la Ciudad de México</p>
      <div className={`estado ${e.modo === 'vivo' ? 'ok' : 'off'}`} style={{ marginTop: 10 }}>
        {e.modo === 'vivo' && `En vivo · faltan ${cuenta(e.restante)} para terminar`}
        {e.modo === 'antes' && `${e.rosario.nombre}: comienza en ${cuenta(e.faltan)}`}
        {e.modo === 'nada' && 'Sin rosarios próximos'}
      </div>
      <h3 style={{ marginTop: 18 }}>Overlay para la transmisión</h3>
      <p className="chico-texto" style={{ marginBottom: 10 }}>
        En OBS: Fuente → Navegador → pega la dirección (1920×1080). Con StreamYard: abre el overlay en una ventana
        y compártela; con «Verde chroma» puedes quitar el fondo verde.
      </p>
      <ul className="lista">
        {TEMAS.map((t) => {
          const url = `${base}?tema=${t.id}`
          return (
            <li key={t.id} className="item envuelve">
              <div><b>{t.nombre}</b><code className="ruta">{url}</code></div>
              <div className="botones-fila">
                <a className="btn suave chico" href={url} target="_blank" rel="noreferrer">Abrir</a>
                <button className="btn suave chico" onClick={() => copiar(url, t.id)}>{copiado === t.id ? '¡Copiado!' : 'Copiar'}</button>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
