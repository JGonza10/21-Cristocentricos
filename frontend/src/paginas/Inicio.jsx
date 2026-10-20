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
            Prepara el evento: fecha, tema y guion.{' '}
            <button className="enlace" onClick={() => ir('evento', proximo.clave)}>Ir al paso 1</button>
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
          <div className="estado ok">Imágenes de difusión listas</div>
          <p className="chico-texto">Las imágenes se generan en el paso 2 de cada evento. Los reels y la publicación llegan en las fases 4 y 5.</p>
        </article>
        <article className="tarjeta">
          <span className="etiqueta">Calendario</span>
          <div className="estado ok">Equipo y temas</div>
          <p className="chico-texto" style={{ marginBottom: 12 }}>Nombres del equipo y tema de cada fecha.</p>
          <button className="btn suave chico" onClick={() => ir('calendario')}>Abrir calendario</button>
        </article>
      </section>

      <section className="tarjeta">
        <span className="etiqueta">Esta semana y la que sigue</span>
        <ul className="lista">
          {semana.map((r) => (
            <li key={r.clave} className={`item ${r.estado === 'pasado' || r.estado === 'hoy-terminado' ? 'pasado' : ''} ${r.estado === 'hoy' || r.estado === 'en-vivo' ? 'hoy' : ''}`}>
              <div>
                <b>{r.nombre}{ETIQUETA_ESTADO[r.estado] && <span className={`pill ${r.estado.startsWith('hoy') || r.estado === 'en-vivo' ? '' : 'gris'}`}>{ETIQUETA_ESTADO[r.estado]}</span>}</b>
                <span className="muted">{r.misterios}</span>
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
