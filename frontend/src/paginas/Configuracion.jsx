import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { fechaHora } from '../util.js'

/** Sección plegable (Gonza, 2026-10-20): solo se ve su título; al pulsarlo se despliega su contenido. */
function Desplegable({ titulo, children }) {
  const [abierto, setAbierto] = useState(false)
  const id = `conf-${titulo.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`
  return (
    <section className={`tarjeta desplegable ${abierto ? 'abierto' : ''}`}>
      <button type="button" className="desplegable-cabeza" aria-expanded={abierto} aria-controls={id} onClick={() => setAbierto((a) => !a)}>
        <span>{titulo}</span><span className="paso-flecha" aria-hidden="true">{abierto ? '▴' : '▾'}</span>
      </button>
      {abierto && <div className="desplegable-cuerpo" id={id}>{children}</div>}
    </section>
  )
}

export default function Configuracion({ usuario }) {
  const [estado, setEstado] = useState(null)
  useEffect(() => { api('/api/estado').then(setEstado).catch(() => setEstado(null)) }, [])

  return (
    <>
      <Equipo />
      <Conexiones estado={estado} />
      <Desplegable titulo="Tu cuenta">
        <dl className="dl">
          <dt>Nombre</dt><dd>{usuario.nombre}</dd>
          <dt>Usuario</dt><dd>{usuario.usuario}</dd>
        </dl>
        <p className="chico-texto" style={{ marginTop: 14 }}>
          Para cambiar tu contraseña, en la PC del sistema ejecuta: <code>flask --app app cambiar-password {usuario.usuario}</code>
        </p>
      </Desplegable>
      <Desplegable titulo="Seguridad">
        <ul className="lista">
          <li className="item"><div><b>Sesión cifrada</b><span className="muted">Se cierra sola a las 8 horas.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Bloqueo por intentos</b><span className="muted">15 minutos tras 5 intentos fallidos.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Nada se publica sin aprobación</b><span className="muted">El agente de publicación solo toca lo aprobado.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Acceso remoto por Tailscale</b><span className="muted">Solo la PC del aprobador puede entrar desde fuera.</span></div><span className="pill gris">según .env</span></li>
        </ul>
      </Desplegable>
    </>
  )
}

function Equipo() {
  const [gente, setGente] = useState(null)
  const [nombre, setNombre] = useState('')
  const [correo, setCorreo] = useState('')
  const [dirige, setDirige] = useState(true)
  const [editando, setEditando] = useState(null)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const [mensaje, setMensaje] = useState('')

  useEffect(() => { api('/api/equipo').then((d) => setGente(d.integrantes)).catch((e) => setError(e.message)) }, [])

  async function accion(fn, exito) {
    setOcupado(true)
    setError('')
    setMensaje('')
    try {
      await fn()
      if (exito) setMensaje(exito)
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
    }
  }

  function agregar(ev) {
    ev.preventDefault()
    accion(async () => {
      const d = await api('/api/equipo', { metodo: 'POST', datos: { nombre, correo, puede_dirigir: dirige } })
      setGente((g) => [...g, d.integrante].sort((a, b) => b.activo - a.activo || a.nombre.localeCompare(b.nombre)))
      setNombre(''); setCorreo(''); setDirige(true)
    }, 'Integrante agregado.')
  }

  function cambiar(i, datos, exito) {
    accion(async () => {
      const d = await api(`/api/equipo/${i.id}`, { metodo: 'PATCH', datos })
      setGente((g) => g.map((x) => (x.id === i.id ? d.integrante : x)))
      setEditando(null)
    }, exito)
  }

  function pausar(i) {
    cambiar(i, { activo: !i.activo }, i.activo
      ? `${i.nombre} quedó en pausa: no recibe turnos, invitaciones ni correos.`
      : `${i.nombre} vuelve a recibir turnos e invitaciones.`)
  }

  function baja(i) {
    if (!window.confirm(`¿Borrar a ${i.nombre}? Se borran su nombre, su correo y sus turnos futuros. Si solo quieres que no reciba correos por un tiempo, usa Pausar.`)) return
    accion(async () => {
      await api(`/api/equipo/${i.id}`, { metodo: 'DELETE' })
      setGente((g) => g.filter((x) => x.id !== i.id))
    }, 'Borrado. Sus datos personales se eliminaron.')
  }

  function repartir() {
    accion(async () => {
      const d = await api('/api/turnos/repartir', { metodo: 'POST' })
      setMensaje(d.asignados ? `Listo: ${d.asignados} turnos asignados en las próximas 2 semanas.` : 'Las próximas 2 semanas ya tienen a todos asignados.')
    })
  }

  return (
    <Desplegable titulo="Equipo">
      <p className="chico-texto" style={{ marginBottom: 12 }}>
        Los integrantes no tienen cuenta: solo su nombre y correo para mandarles la invitación. Cada domingo a las
        6 pm se reparten solos los turnos de la semana, a quien lleva menos turnos. Quien está en pausa no recibe
        turnos, invitaciones ni correos: úsalo para hacer pruebas sin molestar a nadie.
      </p>
      {gente === null && !error && <p className="vacio">Cargando…</p>}
      {gente?.length === 0 && <p className="vacio">Todavía no hay integrantes.</p>}
      {gente?.length > 0 && (
        <ul className="lista">
          {gente.map((i) => (
            <li key={i.id} className={`item envuelve ${i.activo ? '' : 'pasado'}`}>
              {editando?.id === i.id ? (
                <form className="eq-editar" onSubmit={(e) => { e.preventDefault(); cambiar(i, { nombre: editando.nombre, correo: editando.correo }, 'Datos guardados.') }}>
                  <input aria-label="Nombre" value={editando.nombre} maxLength={80} required autoComplete="off"
                    onChange={(e) => setEditando({ ...editando, nombre: e.target.value })} />
                  <input aria-label="Correo" type="email" value={editando.correo} maxLength={120} required autoComplete="off" inputMode="email"
                    onChange={(e) => setEditando({ ...editando, correo: e.target.value })} />
                  <div className="botones-fila">
                    <button className="btn chico" type="submit" disabled={ocupado}>Guardar</button>
                    <button className="btn suave chico" type="button" disabled={ocupado} onClick={() => setEditando(null)}>Cancelar</button>
                  </div>
                </form>
              ) : (
                <>
                  <div>
                    <b>{i.nombre}{!i.activo && <span className="pill gris">en pausa</span>}</b>
                    <span className="muted partir">{i.correo} · {i.puede_dirigir ? 'dirige y apoya' : 'solo apoya'}{!i.activo && ' · sin turnos ni correos'}</span>
                  </div>
                  <div className="botones-fila">
                    <button className="btn suave chico" disabled={ocupado} onClick={() => setEditando({ id: i.id, nombre: i.nombre, correo: i.correo })}>Modificar</button>
                    <button className="btn suave chico" disabled={ocupado} onClick={() => cambiar(i, { puede_dirigir: !i.puede_dirigir })}>
                      {i.puede_dirigir ? 'Solo apoya' : 'Puede dirigir'}
                    </button>
                    <button className="btn suave chico" disabled={ocupado} onClick={() => pausar(i)}>
                      {i.activo ? 'Pausar' : 'Reactivar'}
                    </button>
                    <button className="btn suave chico" disabled={ocupado} onClick={() => baja(i)}>Borrar</button>
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      <form className="formulario" onSubmit={agregar} style={{ marginTop: 18 }}>
        <h3>Agregar integrante</h3>
        <div className="campo">
          <label htmlFor="eq-nombre">Nombre</label>
          <input id="eq-nombre" value={nombre} maxLength={80} required autoComplete="off" onChange={(e) => setNombre(e.target.value)} />
        </div>
        <div className="campo">
          <label htmlFor="eq-correo">Correo (de preferencia Gmail, para Google Calendar)</label>
          <input id="eq-correo" type="email" value={correo} maxLength={120} required autoComplete="off" inputMode="email"
            onChange={(e) => setCorreo(e.target.value)} />
        </div>
        <label className="casilla"><input type="checkbox" checked={dirige} onChange={(e) => setDirige(e.target.checked)} /> Puede dirigir el evento</label>
        {error && <p className="error" role="alert">{error}</p>}
        {mensaje && <p className="chico-texto" role="status">{mensaje}</p>}
        <div className="botones">
          <button className="btn" type="submit" disabled={ocupado}>Agregar</button>
          <button className="btn suave" type="button" disabled={ocupado || !gente?.length} onClick={repartir}>Repartir turnos ahora</button>
        </div>
      </form>
    </Desplegable>
  )
}

function Conexiones({ estado }) {
  const agentes = estado?.agentes ?? []
  return (
    <Desplegable titulo="Agentes y conexiones">
      <ul className="lista">
        <li className="item">
          <div><b>Ventana de agentes</b><span className="muted">{estado?.worker_activo ? 'Trabajando en la PC del sistema.' : 'Apagada: abre iniciar.bat en la PC del sistema.'}</span></div>
          <span className={`pill ${estado?.worker_activo ? 'verde' : 'ambar'}`}>{estado?.worker_activo ? 'activo' : 'apagado'}</span>
        </li>
        {agentes.map((a) => (
          <li key={a.nombre} className="item">
            <div>
              <b>{a.titulo}</b>
              <span className="muted">{a.mensaje || 'Todavía no ha corrido.'}{a.ultimo_ok ? ` · ${fechaHora(a.ultimo_ok)}` : ''}</span>
            </div>
            <span className={`pill ${a.error ? 'ambar' : a.ultimo_ok ? 'verde' : 'gris'}`}>{a.error ? 'revisar' : a.ultimo_ok ? 'bien' : 'sin datos'}</span>
          </li>
        ))}
        <li className="item">
          <div>
            <b>Google (YouTube y Calendar)</b>
            <span className="muted">{estado?.google ? 'Autorizado: los reels suben en privado a YouTube y se mandan las invitaciones.' : <>Sin autorizar. En la PC del sistema: <code>flask --app app google-autorizar</code> (ver README).</>}</span>
          </div>
          <span className={`pill ${estado?.google ? 'verde' : 'ambar'}`}>{estado?.google ? 'conectado' : 'pendiente'}</span>
        </li>
        <li className="item">
          <div>
            <b>Meta (Facebook e Instagram)</b>
            <span className="muted">{estado?.meta ? 'Publicación automática activa para Facebook y reels de Instagram.' : 'Manual: se preparan carpetas en subir_manual/. Se activa con META_AUTO=1 en el .env.'}</span>
          </div>
          <span className={`pill ${estado?.meta ? 'verde' : 'gris'}`}>{estado?.meta ? 'automático' : 'manual'}</span>
        </li>
      </ul>
    </Desplegable>
  )
}
