import { infoRosario, proximoRosario } from '../rosario.js'

export default function Evento({ fecha }) {
  const r = fecha ? infoRosario(new Date(`${fecha}T00:00:00Z`)) : proximoRosario()
  if (!r) return <section className="tarjeta"><p className="vacio">No hay eventos próximos.</p></section>
  return (
    <>
      <section className="hero">
        <div className="etiqueta">Evento</div>
        <h1>{r.nombre}</h1>
        <p className="meta">10:00 a 11:00 am · {r.misterios} · {r.faltan}</p>
      </section>
      <section className="tres">
        <article className="tarjeta">
          <span className="etiqueta">Dirige</span>
          <div className="estado warn">Sin asignar</div>
          <p className="chico-texto">La asignación de turnos llega en la fase 6.</p>
        </article>
        <article className="tarjeta">
          <span className="etiqueta">Apoya</span>
          <div className="estado warn">Sin asignar</div>
          <p className="chico-texto">Recibirá la invitación en su calendario.</p>
        </article>
        <article className="tarjeta">
          <span className="etiqueta">Reloj en vivo</span>
          <div className="estado off">Fase 7</div>
          <p className="chico-texto">Hora de la CDMX y cuenta regresiva para la transmisión.</p>
        </article>
      </section>
    </>
  )
}
