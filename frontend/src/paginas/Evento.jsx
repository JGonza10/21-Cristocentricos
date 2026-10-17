import Turnos from '../componentes/Turnos.jsx'
import TemaEvento from '../componentes/TemaEvento.jsx'
import Revision from '../componentes/Revision.jsx'
import { ControlObs } from '../componentes/Grabacion.jsx'
import { infoEvento, proximoEvento } from '../evento.js'
import { fechaDeClave } from '../util.js'

export default function Evento({ fecha, ir }) {
  const r = fecha ? infoEvento(fechaDeClave(fecha)) : proximoEvento()
  if (!r) return <section className="tarjeta"><p className="vacio">No hay eventos próximos.</p></section>
  const yaPaso = r.estado === 'pasado' || r.estado === 'hoy-terminado'
  return (
    <>
      <section className="hero">
        <div className="etiqueta">{r.estado === 'en-vivo' ? 'En vivo ahora' : 'Evento'}</div>
        <h1>{r.nombre}</h1>
        <p className="meta" style={{ margin: 0 }}>10:00 a 11:00 am · {r.faltan}</p>
        <button className="enlace reloj-mini" onClick={abrirReloj} title="Abre el reloj en grande">Reloj</button>
      </section>
      <section className="tarjeta">
        <h2>Tema, guion e intenciones</h2>
        <TemaEvento key={r.clave} fecha={r.clave} />
      </section>
      {!yaPaso && (
        <section className="tarjeta">
          <h2>El día del evento</h2>
          <Revision key={r.clave} fecha={r.clave} />
          <ControlObs />
        </section>
      )}
      <Turnos clave={r.clave} yaPaso={yaPaso} ir={ir} />
    </>
  )
}

// Reloj de la transmisión: casi nunca se usa, así que solo es un enlace chico que lo abre en grande.
function abrirReloj() {
  window.open('/reloj', 'reloj', 'popup,width=1280,height=720')
}
