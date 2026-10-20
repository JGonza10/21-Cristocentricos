import { useEffect, useState } from 'react'
import { api, olvidarCsrf } from './api.js'
import { aplicarTema, temaActual } from './tema.js'
import { Luna, Sol } from './iconos.jsx'
import { ahoraCDMX, claveFecha, proximoRosario } from './rosario.js'
import Login from './paginas/Login.jsx'
import Inicio from './paginas/Inicio.jsx'
import Contenido from './paginas/Contenido.jsx'
import Evento from './paginas/Evento.jsx'
import Calendario from './paginas/Calendario.jsx'
import Prompter from './paginas/Prompter.jsx'
import Configuracion from './paginas/Configuracion.jsx'

const PESTANAS = [
  { id: 'inicio', nombre: 'Inicio' },
  { id: 'contenido', nombre: 'Contenido' },
  { id: 'evento', nombre: 'Evento' },
  { id: 'calendario', nombre: 'Calendario' },
  { id: 'configuracion', nombre: 'Configuración', corto: 'Ajustes' },
]

// La dirección es #pestana o #pestana/AAAA-MM-DD (evento y prompter recuerdan su fecha al recargar).
function leerUrl() {
  const [id, fecha] = window.location.hash.replace('#', '').split('/')
  const valida = /^\d{4}-\d{2}-\d{2}$/.test(fecha || '') ? fecha : null
  if (id === 'prompter' && valida) return { id, fecha: valida }
  return { id: PESTANAS.some((p) => p.id === id) ? id : 'inicio', fecha: valida }
}

const fechaPorOmision = () => proximoRosario()?.clave || claveFecha(ahoraCDMX())

export default function App() {
  const [usuario, setUsuario] = useState(undefined) // undefined = revisando sesión
  const [pestana, setPestana] = useState(() => leerUrl().id)
  const [fechaEvento, setFechaEvento] = useState(() => leerUrl().fecha || fechaPorOmision())
  const [tema, setTema] = useState(temaActual)

  useEffect(() => {
    api('/api/auth/yo').then((d) => setUsuario(d.usuario)).catch(() => setUsuario(null))
    const alCambiar = () => {
      const u = leerUrl()
      setPestana(u.id)
      if (u.fecha) setFechaEvento(u.fecha)
    }
    window.addEventListener('hashchange', alCambiar)
    return () => window.removeEventListener('hashchange', alCambiar)
  }, [])

  function ir(id, fecha = null) {
    if (fecha) setFechaEvento(fecha)
    const conFecha = id === 'evento' || id === 'prompter'
    window.location.hash = conFecha ? `${id}/${fecha || fechaEvento}` : id
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
  if (pestana === 'prompter') return <Prompter fecha={fechaEvento} salir={() => ir('evento', fechaEvento)} />

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
        {pestana === 'calendario' && <Calendario ir={ir} />}
        {pestana === 'configuracion' && <Configuracion usuario={usuario} />}
      </main>
    </>
  )
}
