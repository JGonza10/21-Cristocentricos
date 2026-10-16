import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { agendaEditorial, fechaCorta, proximoEvento, semanaYSiguiente } from '../evento.js'
import { nombres } from '../util.js'

const ETIQUETA_ESTADO = { pasado: 'ya pasó', 'hoy-terminado': 'hoy, ya pasó', hoy: 'hoy', 'en-vivo': 'en vivo' }

function quienes(t) {
  if (!t || (!t.dirige && t.apoyan.length === 0)) return 'Sin asignar'
  const partes = []
  if (t.dirige) partes.push(`Dirige ${t.dirige.nombre}`)
  if (t.apoyan.length) partes.push(`apoya ${nombres(t.apoyan)}`)
  return partes.join(' · ')
}

export default function Inicio({ ir }) {
  const [ahora, setAhora] = useState(() => new Date())
  const [estado, setEstado] = useState(null)
  const [turnos, setTurnos] = useState({})
  useEffect(() => {
    api('/api/estado').then(setEstado).catch(() => setEstado(null))
    api('/api/turnos').then((d) => setTurnos(d.turnos)).catch(() => setTurnos({}))
  }, [])
  useEffect(() => {
    const t = setInterval(() => setAhora(new Date()), 60_000)
    return () => clearInterval(t)
  }, [])

  const proximo = proximoEvento(ahora)
  const semana = semanaYSiguiente(ahora)
  const agenda = agendaEditorial(ahora)
  const tProximo = proximo && turnos[proximo.clave]
  const pendientes = estado?.bandeja.pendiente

  return (
    <>
      {proximo && (
        <section className="hero">
          <div className="etiqueta">{proximo.estado === 'en-vivo' ? 'En vivo ahora' : 'Próximo evento'}</div>
          <h1>{proximo.nombre}</h1>
          <p className="meta">10:00 a 11:00 am · {proximo.misterios} · {proximo.faltan}</p>
          {tProximo?.dirige ? (
            <p className="meta" style={{ margin: 0 }}>
              <b>{quienes(tProximo)}</b>{' '}
              <button className="enlace" onClick={() => ir('evento', proximo.clave)}>Ver evento</button>
            </p>
          ) : (
            <p className="aviso">
              Todavía no se asigna quién dirige.{' '}
              <button className="enlace" onClick={() => ir('evento', proximo.clave)}>Asignar ahora</button>
            </p>
          )}
        </section>
      )}

      <section className="tres">
        <article className="tarjeta">
          <span className="etiqueta">Bandeja</span>
          <div className="numero">{pendientes ?? '–'}</div>
          <p className="chico-texto" style={{ marginBottom: 12 }}>{pendientes === 1 ? 'paquete por revisar' : 'paquetes por revisar'}</p>
          <button className="btn suave chico" onClick={() => ir('contenido')}>Ir a la bandeja</button>
        </article>
        <article className="tarjeta">
          <span className="etiqueta">Agentes</span>
          {estado?.worker_activo
            ? <div className="estado ok">Trabajando</div>
            : <div className="estado warn">Apagados</div>}
          <p className="chico-texto">
            {estado?.worker_activo
              ? 'Vigilan las grabaciones, preparan el carrusel 2 días antes y reparten turnos los domingos a las 6 pm.'
              : 'Abre iniciar.bat en la PC del sistema para que trabajen los agentes.'}
          </p>
        </article>
        <article className="tarjeta">
          <span className="etiqueta">Invitaciones</span>
          {estado?.google
            ? <div className="estado ok">Google Calendar conectado</div>
            : <div className="estado warn">Google sin autorizar</div>}
          <p className="chico-texto">
            {estado?.google
              ? 'Cada quien recibe en su calendario los eventos que le tocan.'
              : <>Ve a <button className="enlace" onClick={() => ir('configuracion')}>Ajustes</button> para ver cómo conectarlo.</>}
          </p>
        </article>
      </section>

      <section className="tarjeta">
        <span className="etiqueta">Esta semana y la que sigue</span>
        <ul className="lista">
          {semana.map((r) => (
            <li key={r.clave} className={`item ${r.estado === 'pasado' || r.estado === 'hoy-terminado' ? 'pasado' : ''} ${r.estado === 'hoy' || r.estado === 'en-vivo' ? 'hoy' : ''}`}>
              <div>
                <b>{r.nombre}{ETIQUETA_ESTADO[r.estado] && <span className={`pill ${r.estado.startsWith('hoy') || r.estado === 'en-vivo' ? '' : 'gris'}`}>{ETIQUETA_ESTADO[r.estado]}</span>}</b>
                <span className="muted">{quienes(turnos[r.clave])} · {r.misterios.toLowerCase()}</span>
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
