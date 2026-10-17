// Reporte semanal: lo arma solo el sistema cada lunes a las 8 am (agentes/reporte.py). Aquí se ve,
// se puede generar o actualizar al momento y se capturan los seguidores de cada red.
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { fechaHora, REDES } from '../util.js'

const ESTADO_PUB = { publicado: 'publicadas', listo_manual: 'por subir a mano', error: 'con error', subiendo: 'subiendo', sin_configurar: 'sin configurar' }

export default function ReporteSemanal({ alCambiar }) {
  const [lista, setLista] = useState(null)
  const [semana, setSemana] = useState('')
  const [datos, setDatos] = useState(null)
  const [creado, setCreado] = useState(null)
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)

  function cargarLista(elegir) {
    return api('/api/reportes').then((d) => {
      setLista(d.reportes)
      if (elegir ?? !semana) setSemana(elegir ?? d.reportes[0]?.semana ?? '')
    }).catch((e) => setError(e.message))
  }
  useEffect(() => { cargarLista() }, [])

  useEffect(() => {
    if (!semana) { setDatos(null); return }
    api(`/api/reportes/${semana}`).then((d) => { setDatos(d.reporte); setCreado(d.creado); setError('') })
      .catch((e) => setError(e.message))
  }, [semana])

  async function generar(sem) {
    setOcupado(true)
    setError('')
    try {
      const d = await api('/api/reportes/generar', { metodo: 'POST', datos: sem ? { semana: sem } : {} })
      setDatos(d.reporte)
      setCreado(d.creado)
      await cargarLista(d.reporte.semana)
      alCambiar?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <div className="reporte">
      <div className="reporte-barra">
        {lista?.length > 0 && (
          <label className="campo-linea">
            <span>Semana</span>
            <select value={semana} onChange={(e) => setSemana(e.target.value)}>
              {lista.map((r) => <option key={r.semana} value={r.semana}>{r.titulo}</option>)}
            </select>
          </label>
        )}
        <div className="botones-fila">
          {datos && <button className="btn suave chico" onClick={() => generar(datos.semana)} disabled={ocupado}>Actualizar esta semana</button>}
          <button className="btn chico" onClick={() => generar()} disabled={ocupado}>Generar la semana actual</button>
          <a className="btn suave chico" href="/api/registro.csv" download>Descargar registro (Excel)</a>
          <a className="btn suave chico" href="/api/bitacora.csv" download title="Cómo terminó cada evento pasado, para estadísticas">Bitácora de eventos (Excel)</a>
        </div>
      </div>
      <p className="chico-texto">Se arma solo cada lunes a las 8 am con lo que registró el sistema; no hace falta pedírselo a nadie.
        {creado && ` Este reporte se generó el ${fechaHora(creado).replace(/\.$/, '')}.`}</p>
      {error && <p className="error" role="alert">{error}</p>}
      {lista?.length === 0 && !datos && <p className="vacio">Todavía no hay reportes. El primero se arma solo el lunes, o genéralo ahora.</p>}

      {datos && (
        <>
          <h3 className="reporte-titulo">{datos.titulo}</h3>
          <div className="reporte-kpis">
            <Kpi n={datos.totales.eventos} t="eventos" />
            <Kpi n={datos.totales.con_grabacion} t="con grabación" />
            <Kpi n={datos.totales.reels} t="reels" />
            <Kpi n={datos.totales.aprobados} t="aprobados" />
            <Kpi n={datos.totales.publicadas} t="publicadas" />
            <Kpi n={datos.totales.por_subir} t="por subir" tono={datos.totales.por_subir ? 'warn' : ''} />
            <Kpi n={datos.totales.con_error} t="con error" tono={datos.totales.con_error ? 'err' : ''} />
          </div>

          <section className="reporte-sec">
            <h4>Qué mejorar</h4>
            <ul className="reporte-mejorar">{datos.mejorar.map((m) => <li key={m}>{m}</li>)}</ul>
          </section>

          <Seguidores datos={datos.seguidores} alGuardar={() => generar(datos.semana)} />

          <section className="reporte-sec">
            <h4>Resumen de cada evento</h4>
            <div className="reporte-eventos">
              {datos.eventos.map((e) => (
                <article key={e.fecha} className="reporte-evento">
                  <b>{e.nombre}</b> <span className="muted">· {e.tema ?? e.misterios}</span>
                  <p>Dirigió: <b>{e.dirige ?? 'nadie asignado'}</b>{e.apoyan.length > 0 && <> · Apoyó: {e.apoyan.join(', ')}</>}</p>
                  <p>Grabación: {e.grabacion ? `${e.grabacion.nombre}${e.grabacion.minutos ? ` (${e.grabacion.minutos} min)` : ''}` : e.ya_paso ? 'no llegó' : 'aún no es el evento'}</p>
                  <p>{e.reels} reels · carrusel {e.carrusel ? 'sí' : 'no'} · {e.bandeja.aprobado} aprobados, {e.bandeja.rechazado} rechazados{e.bandeja.pendiente ? `, ${e.bandeja.pendiente} por revisar` : ''}</p>
                  {Object.keys(e.publicaciones).length > 0 && (
                    <p>{Object.entries(e.publicaciones).map(([red, c]) => `${REDES[red] ?? red}: ${Object.entries(c).map(([est, n]) => `${n} ${ESTADO_PUB[est] ?? est}`).join(', ')}`).join(' · ')}</p>
                  )}
                </article>
              ))}
            </div>
          </section>

          <div className="reporte-dos">
            <section className="reporte-sec">
              <h4>Equipo</h4>
              {Object.keys(datos.equipo).length === 0 ? <p className="chico-texto">Nadie tuvo turno esta semana.</p> : (
                <ul className="reporte-lista">
                  {Object.entries(datos.equipo).map(([n, c]) => <li key={n}><b>{n}</b>: dirigió {c.dirige}, apoyó {c.apoya}</li>)}
                </ul>
              )}
            </section>
            <section className="reporte-sec">
              <h4>Redes</h4>
              <ul className="reporte-lista">
                {Object.entries(datos.redes).map(([red, c]) => (
                  <li key={red}><b>{REDES[red] ?? red}</b>: {Object.keys(c).length ? Object.entries(c).map(([est, n]) => `${n} ${ESTADO_PUB[est] ?? est}`).join(', ') : 'sin publicaciones'}</li>
                ))}
              </ul>
            </section>
          </div>
        </>
      )}
    </div>
  )
}

function Kpi({ n, t, tono = '' }) {
  return <div className={`kpi ${tono}`}><b>{n}</b><span>{t}</span></div>
}

function Seguidores({ datos, alGuardar }) {
  const [valores, setValores] = useState(() => Object.fromEntries(Object.keys(REDES).map((r) => [r, datos.por_red[r]?.cantidad ?? ''])))
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)

  async function guardar(e) {
    e.preventDefault()
    const cuerpo = Object.fromEntries(Object.entries(valores).filter(([, v]) => v !== '').map(([r, v]) => [r, Number(v)]))
    if (Object.values(cuerpo).some((v) => !Number.isInteger(v) || v < 0)) { setError('Escribe números enteros.'); return }
    setOcupado(true)
    setError('')
    try {
      await api('/api/seguidores', { metodo: 'PUT', datos: cuerpo })
      alGuardar()
    } catch (err) {
      setError(err.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <section className="reporte-sec">
      <h4>Seguidores contra la meta de {datos.meta.toLocaleString('es-MX')}</h4>
      {datos.total !== null ? (
        <div className="meta-barra" role="img" aria-label={`${datos.total} de ${datos.meta} seguidores, ${datos.avance_pct}%`}>
          <div className="meta-pista"><span style={{ width: `${datos.avance_pct}%` }} /></div>
          <b>{datos.total.toLocaleString('es-MX')} · {datos.avance_pct}%</b>
        </div>
      ) : <p className="chico-texto">Aún no hay seguidores capturados.</p>}
      <form className="seg-form" onSubmit={guardar}>
        {Object.entries(REDES).map(([r, nombre]) => (
          <label key={r} className="campo">
            <span>{nombre}{datos.por_red[r]?.cambio != null && <small className="muted"> ({datos.por_red[r].cambio >= 0 ? '+' : ''}{datos.por_red[r].cambio} en la semana)</small>}</span>
            <input type="number" min="0" inputMode="numeric" value={valores[r]} onChange={(e) => setValores((v) => ({ ...v, [r]: e.target.value }))} />
          </label>
        ))}
        <button className="btn suave chico" type="submit" disabled={ocupado}>Guardar seguidores de hoy</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  )
}
