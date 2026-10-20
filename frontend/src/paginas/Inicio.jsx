import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { nombreFecha } from '../fechas.js'

const PASOS = ['datos', 'imagenes', 'revision']

function siguientePaso(pasos) {
  const i = PASOS.findIndex((p) => !pasos[p])
  return i === -1 ? null : i + 1
}

export default function Inicio({ ir }) {
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api('/api/eventos/proximos').then(setDatos).catch((e) => setError(e.message))
  }, [])

  if (error) return <section className="tarjeta"><p className="error">{error}</p></section>
  if (!datos) return <section className="tarjeta"><p className="vacio">Cargando…</p></section>

  const [proximo, ...despues] = datos.eventos
  if (!proximo) {
    return (
      <section className="hero">
        <div className="etiqueta">Bienvenido</div>
        <h1>Prepara tu primer evento</h1>
        <p className="meta">Elige la fecha, escribe el tema y sube el guion. Después se generan las imágenes y haces la revisión técnica con el prompter.</p>
        <button className="btn" onClick={() => ir('evento', datos.hoy)}>Crear evento</button>
      </section>
    )
  }

  const paso = siguientePaso(proximo.pasos)
  return (
    <>
      <section className="hero">
        <div className="etiqueta">{proximo.fecha === datos.hoy ? 'Hoy' : 'Próximo evento'}</div>
        <h1>{proximo.tema || 'Sin tema todavía'}</h1>
        <p className="meta">{nombreFecha(proximo.fecha)} · {proximo.hora} hrs</p>
        <div className="acciones-fila">
          <button className="btn" onClick={() => ir('evento', proximo.fecha)}>
            {paso ? `Continuar: paso ${paso} de 3` : 'Ver evento'}
          </button>
          {!paso && <button className="btn suave" onClick={() => ir('prompter', proximo.fecha)}>Abrir prompter</button>}
        </div>
        {!paso && <p className="estado ok" style={{ marginTop: 12 }}>Todo listo para transmitir</p>}
      </section>

      <section className="tarjeta">
        <span className="etiqueta">Siguientes eventos</span>
        {despues.length === 0 ? <p className="chico-texto">No hay más eventos. Agrégalos desde el calendario.</p> : (
          <ul className="lista">
            {despues.map((e) => {
              const p = siguientePaso(e.pasos)
              return (
                <li key={e.fecha} className="item">
                  <div>
                    <b>{e.tema || 'Sin tema'}</b>
                    <span className="muted">{nombreFecha(e.fecha)} · {p ? `falta el paso ${p}` : 'listo'}</span>
                  </div>
                  <button className="btn suave chico" onClick={() => ir('evento', e.fecha)}>Ver</button>
                </li>
              )
            })}
          </ul>
        )}
        <button className="btn suave" style={{ marginTop: 14 }} onClick={() => ir('calendario')}>Abrir calendario</button>
      </section>
    </>
  )
}
