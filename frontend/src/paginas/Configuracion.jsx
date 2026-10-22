import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { fechaHora } from '../util.js'
import CambiarPassword from '../componentes/CambiarPassword.jsx'

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
        <h3 style={{ marginTop: 18 }}>Cambiar contraseña</h3>
        <CambiarPassword />
      </Desplegable>
      <Desplegable titulo="Seguridad">
        <ul className="lista">
          <li className="item"><div><b>Sesión cifrada</b><span className="muted">Se cierra sola a las 8 horas.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Bloqueo por intentos</b><span className="muted">15 minutos tras 5 intentos fallidos.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Nada se publica solo</b><span className="muted">El material se descarga y se sube a mano a cada red.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Cuentas nuevas con contraseña temporal</b><span className="muted">Se cambia la primera vez que se entra.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Acceso remoto por Tailscale</b><span className="muted">Solo las computadoras invitadas pueden entrar desde fuera.</span></div><span className="pill gris">según .env</span></li>
        </ul>
      </Desplegable>
    </>
  )
}

function Equipo() {
  const [gente, setGente] = useState(null)
  const [nombre, setNombre] = useState('')
  const [correo, setCorreo] = useState('')
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
      const d = await api('/api/equipo', { metodo: 'POST', datos: { nombre, correo } })
      setGente((g) => [...g, d.integrante].sort((a, b) => b.activo - a.activo || a.nombre.localeCompare(b.nombre)))
      setNombre(''); setCorreo('')
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
      ? `${i.nombre} quedó en pausa: no recibe el aviso del tema.`
      : `${i.nombre} vuelve a recibir el aviso del tema.`)
  }

  function baja(i) {
    if (!window.confirm(`¿Borrar a ${i.nombre}? Se borran su nombre y su correo. Si solo quieres que no reciba correos por un tiempo, usa Pausar.`)) return
    accion(async () => {
      await api(`/api/equipo/${i.id}`, { metodo: 'DELETE' })
      setGente((g) => g.filter((x) => x.id !== i.id))
    }, 'Borrado. Sus datos personales se eliminaron.')
  }

  return (
    <Desplegable titulo="Equipo">
      <p className="chico-texto" style={{ marginBottom: 12 }}>
        Los integrantes no tienen cuenta: solo su nombre y correo para mandarles por correo el tema de cada evento en
        cuanto se guarda. Quien está en pausa no recibe correos: úsalo para hacer pruebas sin molestar a nadie.
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
                    <span className="muted partir">{i.correo}{!i.activo && ' · no recibe correos'}</span>
                  </div>
                  <div className="botones-fila">
                    <button className="btn suave chico" disabled={ocupado} onClick={() => setEditando({ id: i.id, nombre: i.nombre, correo: i.correo })}>Modificar</button>
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
          <label htmlFor="eq-correo">Correo</label>
          <input id="eq-correo" type="email" value={correo} maxLength={120} required autoComplete="off" inputMode="email"
            onChange={(e) => setCorreo(e.target.value)} />
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        {mensaje && <p className="chico-texto" role="status">{mensaje}</p>}
        <div className="botones">
          <button className="btn" type="submit" disabled={ocupado}>Agregar</button>
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
            <b>Gmail (aviso del tema al equipo)</b>
            <span className="muted">{estado?.google ? 'Autorizado: al guardar un tema, al equipo le llega un correo.' : <>Sin autorizar: no se mandan correos. En la PC del sistema: <code>flask --app app google-autorizar</code> (ver README).</>}</span>
          </div>
          <span className={`pill ${estado?.google ? 'verde' : 'ambar'}`}>{estado?.google ? 'conectado' : 'pendiente'}</span>
        </li>
      </ul>
    </Desplegable>
  )
}
