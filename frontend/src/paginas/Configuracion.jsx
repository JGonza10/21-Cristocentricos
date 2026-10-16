import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { fechaHora } from '../util.js'

export default function Configuracion({ usuario }) {
  const [estado, setEstado] = useState(null)
  useEffect(() => { api('/api/estado').then(setEstado).catch(() => setEstado(null)) }, [])
  const canal = estado?.canal || 'Cristocéntricos'

  return (
    <>
      <Equipo canal={canal} />
      <Conexiones estado={estado} />
      <section className="tarjeta">
        <span className="etiqueta">Tu cuenta</span>
        <dl className="dl">
          <dt>Nombre</dt><dd>{usuario.nombre}</dd>
          <dt>Usuario</dt><dd>{usuario.usuario}</dd>
        </dl>
        <p className="chico-texto" style={{ marginTop: 14 }}>
          Para cambiar tu contraseña, en la PC del sistema ejecuta: <code>flask --app app cambiar-password {usuario.usuario}</code>
        </p>
      </section>
      <section className="tarjeta">
        <span className="etiqueta">Seguridad</span>
        <ul className="lista">
          <li className="item"><div><b>Sesión cifrada</b><span className="muted">Se cierra sola a las 8 horas.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Bloqueo por intentos</b><span className="muted">15 minutos tras 5 intentos fallidos.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Nada se publica sin aprobación</b><span className="muted">El agente de publicación solo toca lo aprobado.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Acceso remoto por Tailscale</b><span className="muted">Solo la PC del aprobador puede entrar desde fuera.</span></div><span className="pill gris">según .env</span></li>
        </ul>
      </section>
    </>
  )
}

function AvisoPrivacidad({ canal }) {
  return (
    <details className="aviso-privacidad">
      <summary>Leer el aviso de privacidad</summary>
      <p>
        <b>Aviso de privacidad simplificado.</b> {canal} usa tu nombre y tu correo electrónico únicamente para
        asignarte turnos en el Santo Rosario y enviarte la invitación a tu calendario (Google Calendar). No se
        venden, no se comparten con nadie más y no se usan para otros fines. Se guardan en la computadora del
        equipo. Puedes pedir en cualquier momento que se corrijan o se borren (derechos ARCO) con la persona que
        coordina el equipo.
      </p>
    </details>
  )
}

function Equipo({ canal }) {
  const [gente, setGente] = useState(null)
  const [nombre, setNombre] = useState('')
  const [correo, setCorreo] = useState('')
  const [dirige, setDirige] = useState(true)
  const [aviso, setAviso] = useState(false)
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
      const d = await api('/api/equipo', { metodo: 'POST', datos: { nombre, correo, puede_dirigir: dirige, aviso } })
      setGente((g) => [...g, d.integrante].sort((a, b) => b.activo - a.activo || a.nombre.localeCompare(b.nombre)))
      setNombre(''); setCorreo(''); setDirige(true); setAviso(false)
    }, 'Integrante agregado.')
  }

  function cambiar(i, datos) {
    accion(async () => {
      const d = await api(`/api/equipo/${i.id}`, { metodo: 'PATCH', datos })
      setGente((g) => g.map((x) => (x.id === i.id ? d.integrante : x)))
    })
  }

  function baja(i) {
    if (!window.confirm(`¿Dar de baja a ${i.nombre}? Se borran su nombre, su correo y sus turnos futuros.`)) return
    accion(async () => {
      await api(`/api/equipo/${i.id}`, { metodo: 'DELETE' })
      setGente((g) => g.filter((x) => x.id !== i.id))
    }, 'Dado de baja. Sus datos personales se borraron.')
  }

  function repartir() {
    accion(async () => {
      const d = await api('/api/turnos/repartir', { metodo: 'POST' })
      setMensaje(d.asignados ? `Listo: ${d.asignados} turnos asignados en las próximas 2 semanas.` : 'Las próximas 2 semanas ya tienen a todos asignados.')
    })
  }

  return (
    <section className="tarjeta">
      <span className="etiqueta">Equipo</span>
      <p className="chico-texto" style={{ marginBottom: 12 }}>
        Los integrantes no tienen cuenta: solo su nombre y correo para mandarles la invitación. Cada domingo a las
        6 pm se reparten solos los turnos de la semana, a quien lleva menos turnos.
      </p>
      {gente === null && !error && <p className="vacio">Cargando…</p>}
      {gente?.length === 0 && <p className="vacio">Todavía no hay integrantes.</p>}
      {gente?.length > 0 && (
        <ul className="lista">
          {gente.map((i) => (
            <li key={i.id} className={`item envuelve ${i.activo ? '' : 'pasado'}`}>
              <div>
                <b>{i.nombre}{!i.activo && <span className="pill gris">inactivo</span>}</b>
                <span className="muted partir">{i.correo} · {i.puede_dirigir ? 'dirige y apoya' : 'solo apoya'}</span>
              </div>
              <div className="botones-fila">
                <button className="btn suave chico" disabled={ocupado} onClick={() => cambiar(i, { puede_dirigir: !i.puede_dirigir })}>
                  {i.puede_dirigir ? 'Solo apoya' : 'Puede dirigir'}
                </button>
                <button className="btn suave chico" disabled={ocupado} onClick={() => cambiar(i, { activo: !i.activo })}>
                  {i.activo ? 'Pausar' : 'Activar'}
                </button>
                <button className="btn suave chico" disabled={ocupado} onClick={() => baja(i)}>Dar de baja</button>
              </div>
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
        <label className="casilla"><input type="checkbox" checked={dirige} onChange={(e) => setDirige(e.target.checked)} /> Puede dirigir el rosario</label>
        <label className="casilla"><input type="checkbox" checked={aviso} onChange={(e) => setAviso(e.target.checked)} required /> Le informé el aviso de privacidad y está de acuerdo</label>
        <AvisoPrivacidad canal={canal} />
        {error && <p className="error" role="alert">{error}</p>}
        {mensaje && <p className="chico-texto" role="status">{mensaje}</p>}
        <div className="botones">
          <button className="btn" type="submit" disabled={ocupado}>Agregar</button>
          <button className="btn suave" type="button" disabled={ocupado || !gente?.length} onClick={repartir}>Repartir turnos ahora</button>
        </div>
      </form>
    </section>
  )
}

function Conexiones({ estado }) {
  const agentes = estado?.agentes ?? []
  return (
    <section className="tarjeta">
      <span className="etiqueta">Agentes y conexiones</span>
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
    </section>
  )
}
