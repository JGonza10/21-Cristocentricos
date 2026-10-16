import { useEffect, useState } from 'react'
import { agendaEditorial, fechaCorta, proximoRosario, semanaYSiguiente } from '../rosario.js'

const ETIQUETA_ESTADO = { pasado: 'ya pasó', 'hoy-terminado': 'hoy, ya pasó', hoy: 'hoy', 'en-vivo': 'en vivo' }

export default function Inicio({ ir }) {
  const [ahora, setAhora] = useState(() => new Date())
  useEffect(() => {
    const t = setInterval(() => setAhora(new Date()), 60_000)
    return () => clearInterval(t)
  }, [])

  const proximo = proximoRosario(ahora)
  const semana = semanaYSiguiente(ahora)
  const agenda = agendaEditorial(ahora)

  return (
    <>
      {proximo && (
        <section className="hero">
          <div className="etiqueta">{proximo.estado === 'en-vivo' ? 'En vivo ahora' : 'Próximo evento'}</div>
          <h1>{proximo.nombre}</h1>
          <p className="meta">10:00 a 11:00 am · {proximo.misterios} · {proximo.faltan}</p>
          <p className="aviso">
            Todavía no se asigna quién dirige.{' '}
            <button className="enlace" onClick={() => ir('evento', proximo.clave)}>Asignar ahora</button>
          </p>
        </section>
      )}

      <section className="tres">
        <article className="tarjeta">
          <span className="etiqueta">Bandeja</span>
          <div className="numero">0</div>
          <p className="chico-texto" style={{ marginBottom: 12 }}>paquetes por revisar</p>
          <button className="btn suave chico" onClick={() => ir('contenido')}>Ir a la bandeja</button>
        </article>
        <article className="tarjeta">
          <span className="etiqueta">Agentes</span>
          <div className="estado off">Aún no activos</div>
          <p className="chico-texto">Vigilarán las grabaciones, prepararán el carrusel 2 días antes y repartirán los turnos los domingos a las 6 pm. Se activan en las fases 3 a 6.</p>
        </article>
        <article className="tarjeta">
          <span className="etiqueta">Invitaciones</span>
          <div className="estado warn">Correo sin configurar</div>
          <p className="chico-texto">Se conecta con Google Calendar en la fase 6.</p>
        </article>
      </section>

      <section className="tarjeta">
        <span className="etiqueta">Esta semana y la que sigue</span>
        <ul className="lista">
          {semana.map((r) => (
            <li key={r.clave} className={`item ${r.estado === 'pasado' || r.estado === 'hoy-terminado' ? 'pasado' : ''} ${r.estado === 'hoy' || r.estado === 'en-vivo' ? 'hoy' : ''}`}>
              <div>
                <b>{r.nombre}{ETIQUETA_ESTADO[r.estado] && <span className={`pill ${r.estado.startsWith('hoy') || r.estado === 'en-vivo' ? '' : 'gris'}`}>{ETIQUETA_ESTADO[r.estado]}</span>}</b>
                <span className="muted">Sin asignar · {r.misterios.toLowerCase()}</span>
              </div>
              <button className="btn suave chico" onClick={() => ir('evento', r.clave)}>Ver</button>
            </li>
          ))}
        </ul>
      </section>

      <section className="tarjeta agenda">
        <span className="etiqueta">Agenda editorial</span>
        {agenda.length === 0 ? <p className="vacio">Nada pendiente.</p> : (
          <ul className="lista">
            {agenda.map((a, i) => (
              <li key={i} className="item">
                <span className="cuando">{fechaCorta(a.fecha)}</span>
                <div>
                  <b>{a.tipo}<span className="pill gris">automático</span></b>
                  <span className="muted">{a.texto}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}
