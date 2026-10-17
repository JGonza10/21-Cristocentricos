import { useEffect, useState } from 'react'
import { api, olvidarCsrf } from './api.js'
import { aplicarTema, temaActual } from './tema.js'
import { Luna, Sol } from './iconos.jsx'
import Login from './paginas/Login.jsx'
import Inicio from './paginas/Inicio.jsx'
import Contenido from './paginas/Contenido.jsx'
import Evento from './paginas/Evento.jsx'
import Configuracion from './paginas/Configuracion.jsx'
import Modal from './componentes/Modal.jsx'
import Ideas from './componentes/Ideas.jsx'

const PESTANAS = [
  { id: 'inicio', nombre: 'Inicio' },
  { id: 'contenido', nombre: 'Contenido' },
  { id: 'evento', nombre: 'Evento' },
  { id: 'configuracion', nombre: 'Configuración', corto: 'Ajustes' },
]

function pestanaDeUrl() {
  const id = window.location.hash.replace('#', '')
  return PESTANAS.some((p) => p.id === id) ? id : 'inicio'
}

export default function App() {
  const [usuario, setUsuario] = useState(undefined) // undefined = revisando sesión
  const [pestana, setPestana] = useState(pestanaDeUrl)
  const [fechaEvento, setFechaEvento] = useState(null)
  const [tema, setTema] = useState(temaActual)
  const [ideas, setIdeas] = useState(false)

  useEffect(() => {
    api('/api/auth/yo').then((d) => setUsuario(d.usuario)).catch(() => setUsuario(null))
    const alCambiar = () => setPestana(pestanaDeUrl())
    window.addEventListener('hashchange', alCambiar)
    return () => window.removeEventListener('hashchange', alCambiar)
  }, [])

  function ir(id, fecha = null) {
    if (fecha) setFechaEvento(fecha)
    window.location.hash = id
    setPestana(id)
    window.scrollTo({ top: 0 })
  }

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

  return (
    <>
      <header className="cabecera">
        <div className="cab-fila">
          <div className="marca">† Cristocéntricos<small>· sistema del equipo</small></div>
          <div className="acciones">
            <div className="tema" role="group" aria-label="Tema">
              <button aria-pressed={tema === 'light'} onClick={() => elegirTema('light')}><Sol /><span>Claro</span></button>
              <button aria-pressed={tema === 'dark'} onClick={() => elegirTema('dark')}><Luna /><span>Oscuro</span></button>
            </div>
            <button className="btn suave chico" onClick={() => setIdeas(true)} title="Guarda una idea escrita o por voz">Ideas</button>
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
        {pestana === 'inicio' && <Inicio ir={ir} />}
        {pestana === 'contenido' && <Contenido />}
        {pestana === 'evento' && <Evento fecha={fechaEvento} ir={ir} />}
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
