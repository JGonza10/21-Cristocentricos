import { fijarModo } from './modo.js'
import { useCallback, useEffect, useState } from 'react'
import { api, olvidarCsrf } from './api.js'
import { aplicarTema, temaActual } from './tema.js'
import { Luna, Sol } from './iconos.jsx'
import Login from './paginas/Login.jsx'
import Inicio from './paginas/Inicio.jsx'
import Contenido from './paginas/Contenido.jsx'
import Configuracion from './paginas/Configuracion.jsx'
import Modal from './componentes/Modal.jsx'
import Ideas from './componentes/Ideas.jsx'
import CambiarPassword from './componentes/CambiarPassword.jsx'

const PESTANAS = [
  { id: 'inicio', nombre: 'Inicio' },
  { id: 'contenido', nombre: 'Material' },
  { id: 'configuracion', nombre: 'Configuración', corto: 'Ajustes' },
]

function pestanaDeUrl() {
  const id = window.location.hash.replace('#', '')
  return PESTANAS.some((p) => p.id === id) ? id : 'inicio'
}

export default function App() {
  const [usuario, setUsuario] = useState(undefined) // undefined = revisando sesión
  const [pestana, setPestana] = useState(pestanaDeUrl)
  const [tema, setTema] = useState(temaActual)
  const [ideas, setIdeas] = useState(false)
  const [diagrama, setDiagrama] = useState(false)

  useEffect(() => {
    api('/api/auth/yo').then((d) => { fijarModo(d.modo); setUsuario(d.usuario) }).catch(() => setUsuario(null))
    const alCambiar = () => setPestana(pestanaDeUrl())
    window.addEventListener('hashchange', alCambiar)
    return () => window.removeEventListener('hashchange', alCambiar)
  }, [])

  function ir(id) {
    window.location.hash = id
    setPestana(id)
    window.scrollTo({ top: 0 })
  }

  const cerrarAvisoDiagrama = useCallback(() => setDiagrama(false), [])

  function elegirTema(t) {
    aplicarTema(t)
    setTema(t)
  }

  async function salir() {
    try { await api('/api/auth/logout', { metodo: 'POST' }) } catch { /* igual cerramos */ } finally {
      olvidarCsrf()
      setUsuario(null)
    }
  }

  if (usuario === undefined) return <div className="cargando">Cargando…</div>
  if (!usuario) return <Login alEntrar={setUsuario} />
  if (usuario.cambiar_password) {
    // Cuenta nueva con contraseña temporal: antes de usar la app tiene que poner la suya.
    return (
      <main className="login">
        <div className="login-caja">
          <div className="etiqueta">Bienvenida, {usuario.nombre.split(' ')[0]}</div>
          <h1 style={{ marginTop: 6 }}>Pon tu contraseña</h1>
          <p className="muted" style={{ marginTop: 8 }}>Entraste con una contraseña temporal. Escribe una tuya para seguir.</p>
          <div className="tarjeta" style={{ marginTop: 22 }}>
            <CambiarPassword alCambiar={setUsuario} />
          </div>
          <p style={{ marginTop: 14 }}><button className="enlace" onClick={salir}>Salir</button></p>
        </div>
      </main>
    )
  }

  return (
    <>
      <header className="cabecera">
        <div className="cab-fila">
          <div className="marca">
            <img src="/marca/logo-cristocentricos.png" alt="Cristocéntricos" width="119" height="44" />
            <small>sistema del equipo</small>
          </div>
          <div className="acciones">
            <div className="tema" role="group" aria-label="Tema">
              <button aria-pressed={tema === 'light'} onClick={() => elegirTema('light')}><Sol /><span>Claro</span></button>
              <button aria-pressed={tema === 'dark'} onClick={() => elegirTema('dark')} title="Tema oscuro con oro"><Luna /><span>Oro</span></button>
            </div>
            <button className="btn suave chico" onClick={() => { ir('inicio'); setDiagrama(true) }}
              title="Muestra en grande cómo funciona el proceso del evento">Diagrama</button>
            <button className="btn suave chico" onClick={salir}>Salir</button>
          </div>
        </div>
        <nav className="pestanas" role="tablist" aria-label="Secciones">
          {PESTANAS.map((p) => (
            <button key={p.id} role="tab" aria-selected={pestana === p.id} aria-label={p.nombre} onClick={() => ir(p.id)}>
              {p.corto ? <><span className="largo">{p.nombre}</span><span className="corto">{p.corto}</span></> : p.nombre}
            </button>
          ))}
        </nav>
      </header>

      <main className="envoltura" role="tabpanel">
        {pestana === 'inicio' && <Inicio ir={ir} verDiagrama={diagrama} alVerDiagrama={cerrarAvisoDiagrama} abrirIdeas={() => setIdeas(true)} />}
        {pestana === 'contenido' && <Contenido />}
        {pestana === 'configuracion' && <Configuracion usuario={usuario} />}
      </main>

      <footer className="pie">
        © <a className="kestrel-link" href="https://kestrel-ia.up.railway.app/" target="_blank" rel="noopener noreferrer">Kestrel</a> {new Date().getFullYear()}
      </footer>

      <Modal abierto={ideas} titulo="Ideas del equipo" alCerrar={() => setIdeas(false)}>
        <Ideas />
      </Modal>
    </>
  )
}
