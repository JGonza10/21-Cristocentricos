// Dashboard de estadísticas: tú eliges el periodo y las gráficas se recalculan. Pasa el mouse (o toca)
// para ver el detalle, prende y apaga series en la leyenda y haz clic en un evento para ver su ficha.
import { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'
import { ahoraCDMX, claveFecha, fechaCorta, nombreFecha } from '../evento.js'
import { REDES, fechaDeClave } from '../util.js'
import { Barras, Dona, Lineas, Porcentajes } from '../componentes/Graficas.jsx'
import '../styles/estadisticas.css'

const PASO_CORTO = {
  tema: 'Tema y guion', turnos: 'Turnos', difusion: 'Difusión', revision: 'Revisión técnica', vivo: 'En vivo',
  grabacion: 'Grabación', reels: 'Reels', carrusel: 'Carrusel', bandeja: 'Bandeja', publicacion: 'Publicación',
  redes: 'Redes', registro: 'Registro', mides: 'Reporte',
}
const COLOR_RED = { instagram: '#c13584', facebook: '#1877f2', tiktok: '#14b8a6', youtube: '#e11d48' }
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

const hoy = () => claveFecha(ahoraCDMX())
function restar(dias) {
  return claveFecha(new Date(fechaDeClave(hoy()).getTime() - dias * 86400000))
}
const PERIODOS = [
  { id: '30', nombre: 'Último mes', desde: () => restar(30) },
  { id: '90', nombre: '3 meses', desde: () => restar(90) },
  { id: '180', nombre: '6 meses', desde: () => restar(180) },
  { id: 'anio', nombre: 'Este año', desde: () => `${hoy().slice(0, 4)}-01-01` },
  { id: '365', nombre: '12 meses', desde: () => restar(365) },
]
const etiquetaFecha = (clave) => { const d = fechaDeClave(clave); return `${d.getUTCDate()} ${MESES[d.getUTCMonth()]}` }

function leer() {
  try { return JSON.parse(localStorage.getItem('estadisticas-periodo')) || null } catch { return null }
}

export default function Estadisticas({ ir }) {
  const guardado = leer()
  const [periodo, setPeriodo] = useState(guardado?.periodo ?? '90')
  const [desde, setDesde] = useState(guardado?.periodo === 'propio' ? guardado.desde : PERIODOS.find((p) => p.id === (guardado?.periodo ?? '90'))?.desde() ?? restar(90))
  const [hasta, setHasta] = useState(guardado?.periodo === 'propio' ? guardado.hasta : hoy())
  const [datos, setDatos] = useState(null)
  const [error, setError] = useState('')
  const [elegido, setElegido] = useState(null)
  const [cargando, setCargando] = useState(false)

  useEffect(() => {
    if (!desde || !hasta) return
    setCargando(true)
    setError('')
    api(`/api/estadisticas?desde=${desde}&hasta=${hasta}`)
      .then((d) => { setDatos(d); setElegido(null) })
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false))
    try { localStorage.setItem('estadisticas-periodo', JSON.stringify({ periodo, desde, hasta })) } catch { /* sin almacenamiento */ }
  }, [desde, hasta, periodo])

  function elegirPeriodo(p) {
    setPeriodo(p.id)
    setDesde(p.desde())
    setHasta(hoy())
  }

  const eventos = datos?.eventos ?? []
  const conDatos = useMemo(() => eventos.map((e) => ({
    ...e, publicadas_total: Object.values(e.publicadas).reduce((a, b) => a + b, 0), ...e.publicadas,
  })), [eventos])
  const ev = elegido !== null ? conDatos[elegido] : null
  const r = datos?.resumen

  return (
    <>
      <section className="tarjeta est-filtros">
        <span className="etiqueta">Estadísticas</span>
        <div className="est-periodos" role="group" aria-label="Periodo">
          {PERIODOS.map((p) => (
            <button key={p.id} type="button" className="chip" aria-pressed={periodo === p.id} onClick={() => elegirPeriodo(p)}>{p.nombre}</button>
          ))}
        </div>
        <div className="est-rango">
          <label>Desde <input type="date" value={desde} max={hasta} onChange={(e) => { setPeriodo('propio'); setDesde(e.target.value) }} /></label>
          <label>Hasta <input type="date" value={hasta} min={desde} onChange={(e) => { setPeriodo('propio'); setHasta(e.target.value) }} /></label>
          {cargando && <span className="chico-texto">Calculando…</span>}
        </div>
        {error && <p className="error" role="alert">{error}</p>}
      </section>

      {r && (
        <section className="est-kpis" aria-label="Resumen del periodo">
          <Kpi titulo="Eventos realizados" valor={r.eventos} nota={`${r.con_tema} con tema${r.proximos ? ` · ${r.proximos} por venir` : ''}`} />
          <Kpi titulo="Con video" valor={r.con_video} nota={`${r.minutos} min grabados`} />
          <Kpi titulo="Piezas creadas" valor={r.piezas} nota={`${datos.piezas.aprobado} aprobadas`} />
          <Kpi titulo="Publicaciones" valor={r.publicadas} nota="en las redes" />
          <Kpi titulo="Ideas" valor={r.ideas} nota="guardadas" />
        </section>
      )}

      {datos && (
        <div className="est-rejilla">
          <section className="tarjeta est-ancha">
            <h3>Avance de cada evento</h3>
            <p className="chico-texto">Pasos completados de 13. Haz clic en un evento para ver su ficha. Solo cuentan los eventos que se trabajaron en la app.</p>
            <Barras datos={conDatos} etiqueta={(e) => fechaCorta(fechaDeClave(e.fecha))}
              titulo={(e) => `${nombreFecha(fechaDeClave(e.fecha))}${e.tema ? ` · ${e.tema}` : ''}`}
              series={[{ clave: 'hechos', nombre: 'Pasos hechos', color: 'var(--accent)' }]}
              alElegir={(_, i) => setElegido(i === elegido ? null : i)} elegido={elegido} />
            {ev && <Ficha e={ev} ir={ir} alCerrar={() => setElegido(null)} />}
          </section>

          <section className="tarjeta est-ancha">
            <h3>Piezas por evento</h3>
            <Barras datos={conDatos} etiqueta={(e) => fechaCorta(fechaDeClave(e.fecha))}
              titulo={(e) => nombreFecha(fechaDeClave(e.fecha))} apilar={false}
              series={[
                { clave: 'difusion', nombre: 'Difusión', color: 'var(--activo)' },
                { clave: 'reels', nombre: 'Reels', color: 'var(--accent)' },
                { clave: 'aprobados', nombre: 'Aprobadas', color: 'var(--ok)' },
                { clave: 'rechazados', nombre: 'Rechazadas', color: 'var(--err)' },
              ]}
              alElegir={(_, i) => setElegido(i)} elegido={elegido} />
          </section>

          <section className="tarjeta">
            <h3>Estado de las piezas</h3>
            <Dona partes={[
              { clave: 'pendiente', nombre: 'Por revisar', valor: datos.piezas.pendiente, color: 'var(--warn)' },
              { clave: 'aprobado', nombre: 'Aprobadas', valor: datos.piezas.aprobado, color: 'var(--ok)' },
              { clave: 'rechazado', nombre: 'Rechazadas', valor: datos.piezas.rechazado, color: 'var(--err)' },
            ]} alElegir={(k) => k && ir?.('contenido')} />
            <p className="chico-texto">Clic en una parte para ir a Contenido.</p>
          </section>

          <section className="tarjeta">
            <h3>Cómo se cumple cada paso</h3>
            <p className="chico-texto"><span className="g-punto" style={{ background: 'var(--ok)' }} />hecho <span className="g-punto" style={{ background: 'var(--off)' }} />omitido</p>
            <Porcentajes filas={datos.pasos.map((p) => ({ clave: p.id, nombre: PASO_CORTO[p.id], ...p }))} />
          </section>

          <section className="tarjeta est-ancha">
            <h3>Publicaciones por red</h3>
            <Barras datos={conDatos} etiqueta={(e) => fechaCorta(fechaDeClave(e.fecha))}
              titulo={(e) => nombreFecha(fechaDeClave(e.fecha))}
              series={Object.entries(REDES).map(([k, n]) => ({ clave: k, nombre: n, color: COLOR_RED[k] }))}
              alElegir={(_, i) => setElegido(i)} elegido={elegido} />
          </section>

          <section className="tarjeta est-ancha">
            <h3>Seguidores</h3>
            <p className="chico-texto">Se capturan a mano en el Reporte semanal (Inicio → Reporte semanal).</p>
            <Lineas desde={datos.desde} hasta={datos.hasta} etiquetaFecha={etiquetaFecha}
              series={Object.entries(REDES).map(([k, n]) => ({
                clave: k, nombre: n, color: COLOR_RED[k], puntos: datos.seguidores[k].map((p) => ({ fecha: p.fecha, y: p.cantidad })),
              }))} />
          </section>

          <section className="tarjeta est-ancha">
            <h3>Ideas por semana</h3>
            <Barras datos={datos.ideas} etiqueta={(s) => etiquetaFecha(s.semana)} titulo={(s) => `Semana del ${etiquetaFecha(s.semana)}`}
              series={[{ clave: 'ideas', nombre: 'Ideas', color: 'var(--accent)' }]} />
          </section>
        </div>
      )}
      {datos && (
        <p className="chico-texto est-pie">
          Los eventos pasados salen de la bitácora; los de hoy en adelante se calculan en vivo.{' '}
          <a href="/api/bitacora.csv" download>Descargar bitácora (Excel)</a>
        </p>
      )}
    </>
  )
}

function Kpi({ titulo, valor, nota }) {
  return (
    <div className="tarjeta est-kpi">
      <span className="etiqueta">{titulo}</span>
      <div className="numero">{valor.toLocaleString('es-MX')}</div>
      <span className="chico-texto">{nota}</span>
    </div>
  )
}

function Ficha({ e, ir, alCerrar }) {
  return (
    <div className="est-ficha">
      <div className="est-ficha-cabeza">
        <b>{nombreFecha(fechaDeClave(e.fecha))}{e.tema && ` · ${e.tema}`}</b>
        <button className="btn suave chico" type="button" onClick={alCerrar}>Cerrar</button>
      </div>
      <p className="chico-texto">
        {e.hechos} de {e.total} pasos · {e.minutos} min de video · {e.difusion} de difusión · {e.reels} reels
        {e.carrusel ? ' · carrusel' : ''} · {e.aprobados} aprobadas · {e.rechazados} rechazadas · {e.publicadas_total} publicaciones
      </p>
      <div className="est-pasos">
        {Object.entries(PASO_CORTO).map(([id, n]) => (
          <span key={id} className={`pill ${e.pasos[id] === 'hecho' ? 'verde' : e.pasos[id] === 'omitido' ? 'gris' : 'ambar'}`}>{n}</span>
        ))}
      </div>
      {e.fecha >= claveFecha(ahoraCDMX()) && ir && (
        <button className="btn suave chico" type="button" onClick={() => ir('evento', e.fecha)}>Abrir el evento</button>
      )}
    </div>
  )
}
