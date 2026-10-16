import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { infoEvento, proximoEvento } from '../evento.js'
import { fechaDeClave, nombres } from '../util.js'

const MAX_APOYOS = 3

export default function Evento({ fecha, ir }) {
  const r = fecha ? infoEvento(fechaDeClave(fecha)) : proximoEvento()
  if (!r) return <section className="tarjeta"><p className="vacio">No hay eventos próximos.</p></section>
  const yaPaso = r.estado === 'pasado' || r.estado === 'hoy-terminado'
  return (
    <>
      <section className="hero">
        <div className="etiqueta">{r.estado === 'en-vivo' ? 'En vivo ahora' : 'Evento'}</div>
        <h1>{r.nombre}</h1>
        <p className="meta" style={{ margin: 0 }}>10:00 a 11:00 am · {r.misterios} · {r.faltan}</p>
        <button className="enlace reloj-mini" onClick={abrirReloj} title="Abre el reloj en grande">Reloj</button>
      </section>
      <Turnos clave={r.clave} yaPaso={yaPaso} ir={ir} />
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

// Reloj de la transmisión: casi nunca se usa, así que solo es un enlace chico que lo abre en grande.
function abrirReloj() {
  window.open('/reloj', 'reloj', 'popup,width=1280,height=720')
}
