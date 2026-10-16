import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { proximoEvento } from '../evento.js'
import { nombres } from '../util.js'
import { calcularPasos, ESTADOS } from '../pasos.js'
import Flujo from '../componentes/Flujo.jsx'
import CalendarioEventos from '../componentes/CalendarioEventos.jsx'
import '../styles/inicio.css'

const REFRESCO_MS = 20_000
const CLASE_ESTADO = { ok: 'ok', activo: 'activo', espera: 'warn', error: 'err', apagado: 'off' }

// Botón de cada tarjeta: a dónde lleva resolver ese paso.
const ACCION = {
  turnos: { texto: 'Asignar en el calendario', destino: 'calendario' },
  carrusel: { texto: 'Ver en la bandeja', destino: 'contenido' },
  reels: { texto: 'Ver en la bandeja', destino: 'contenido' },
  bandeja: { texto: 'Ir a la bandeja', destino: 'contenido' },
  publicacion: { texto: 'Ver publicaciones', destino: 'contenido' },
}

function quienes(t) {
  if (!t || (!t.dirige && t.apoyan.length === 0)) return 'Sin asignar'
  const partes = []
  if (t.dirige) partes.push(`Dirige ${t.dirige.nombre}`)
  if (t.apoyan.length) partes.push(`apoya ${nombres(t.apoyan)}`)
  return partes.join(' · ')
}

function bajarA(id) {
  const el = document.getElementById(id)
  if (!el) return
  const quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  el.scrollIntoView({ behavior: quieto ? 'auto' : 'smooth', block: 'center' })
  el.classList.remove('resaltar')
  void el.offsetWidth // reinicia la animación si se pulsa dos veces
  el.classList.add('resaltar')
}

export default function Inicio({ ir }) {
  const [ahora, setAhora] = useState(() => new Date())
  const [estado, setEstado] = useState(null)
  const [turnos, setTurnos] = useState({})

  const cargar = useCallback(() => {
    api('/api/estado').then(setEstado).catch(() => setEstado(null))
    api('/api/turnos').then((d) => setTurnos(d.turnos)).catch(() => setTurnos({}))
    setAhora(new Date())
  }, [])
  useEffect(() => {
    cargar()
    const t = setInterval(cargar, REFRESCO_MS)
    return () => clearInterval(t)
  }, [cargar])

  const proximo = proximoEvento(ahora)
  const tProximo = proximo && turnos[proximo.clave]
  const pasos = calcularPasos(estado, turnos, ahora)
  const trabajando = Boolean(estado?.worker_activo)

  function accion(id) {
    const a = ACCION[id]
    if (a.destino === 'calendario') bajarA('calendario')
    else ir(a.destino)
  }

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
              <button className="enlace" onClick={() => bajarA('calendario')}>Asignar ahora</button>
            </p>
          )}
        </section>
      )}

      <section className="tarjeta">
        <div className="flujo-cabeza">
          <span className="etiqueta">Así va el trabajo</span>
          {estado && (trabajando
            ? <span className="estado activo">Agentes trabajando</span>
            : <span className="estado off">Agentes apagados · abre iniciar.bat</span>)}
        </div>
        <Flujo pasos={pasos} trabajando={trabajando} alElegir={(id) => bajarA(`paso-${id}`)} />
        <div className="flujo-leyenda" aria-hidden="true">
          {Object.entries(ESTADOS).map(([k, v]) => <span key={k} className={`ley ${k}`}><i />{v}</span>)}
        </div>
      </section>

      <section className="pasos">
        {pasos.map((p) => (
          <article key={p.id} id={`paso-${p.id}`} className={`tarjeta paso ${p.estado}`}>
            <span className="etiqueta">{p.numero} · {p.titulo}</span>
            <div className={`estado ${CLASE_ESTADO[p.estado]}`}>{ESTADOS[p.estado]}</div>
            <p className="paso-resumen">{p.resumen}</p>
            {p.detalle.map((d) => <p key={d} className="chico-texto">{d}</p>)}
            <p className="chico-texto paso-que">{p.que}</p>
            {ACCION[p.id] && (
              <div className="botones paso-accion">
                <button className="btn suave chico" onClick={() => accion(p.id)}>{ACCION[p.id].texto}</button>
              </div>
            )}
          </article>
        ))}
      </section>

      <CalendarioEventos ir={ir} alCambiar={cargar} />
    </>
  )
}
