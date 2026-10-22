// Calendario del mes con los eventos y su tema. Se abre en una ventana desde Inicio.
// Lunes y viernes son los fijos; cualquier otro día (que no haya pasado) se elige para ponerle tema y volverlo evento.
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { ahoraCDMX, claveFecha, esDiaFijo, infoEvento, proximoEvento, registrarEventos } from '../evento.js'
import { fechaDeClave } from '../util.js'
import TemaEvento from './TemaEvento.jsx'

const DIA_MS = 24 * 60 * 60 * 1000
const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
const CABECERA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

/** Los 35 o 42 días (lunes a domingo) que cubren el mes. */
function diasDelMes(anio, mes) {
  const primero = new Date(Date.UTC(anio, mes, 1))
  const inicio = new Date(primero.getTime() - ((primero.getUTCDay() + 6) % 7) * DIA_MS)
  const ultimo = new Date(Date.UTC(anio, mes + 1, 0))
  const semanas = Math.ceil(((ultimo - inicio) / DIA_MS + 1) / 7)
  return Array.from({ length: semanas * 7 }, (_, i) => new Date(inicio.getTime() + i * DIA_MS))
}

export default function CalendarioEventos({ alCambiar, fechaInicial }) {
  const hoy = ahoraCDMX()
  const inicial = fechaInicial ? fechaDeClave(fechaInicial) : hoy
  const [mes, setMes] = useState({ anio: inicial.getUTCFullYear(), mes: inicial.getUTCMonth() })
  const [temas, setTemas] = useState({})
  const [elegido, setElegido] = useState(() => fechaInicial ?? proximoEvento()?.clave ?? null)
  const [error, setError] = useState('')

  const dias = diasDelMes(mes.anio, mes.mes)
  const desde = claveFecha(dias[0])
  const hasta = claveFecha(dias[dias.length - 1])

  useEffect(() => {
    api(`/api/temas?desde=${desde}&hasta=${hasta}`)
      .then((t) => { registrarEventos(Object.keys(t.temas)); setTemas(t.temas); setError('') })
      .catch((e) => setError(e.message))
  }, [desde, hasta])

  function mover(n) {
    setMes(({ anio, mes: m }) => {
      const d = new Date(Date.UTC(anio, m + n, 1))
      return { anio: d.getUTCFullYear(), mes: d.getUTCMonth() }
    })
  }

  function irHoy() {
    setMes({ anio: hoy.getUTCFullYear(), mes: hoy.getUTCMonth() })
    setElegido(proximoEvento()?.clave ?? null)
  }

  const info = elegido ? infoEvento(fechaDeClave(elegido)) : null

  return (
    <div className="cal-ventana solo">
      <div className="cal-principal">
        <div className="cal-cabeza">
          <div className="cal-nav">
            <button className="btn suave chico" onClick={() => mover(-1)} aria-label="Mes anterior">‹</button>
            <b className="cal-mes" aria-live="polite">{MESES[mes.mes]} {mes.anio}</b>
            <button className="btn suave chico" onClick={() => mover(1)} aria-label="Mes siguiente">›</button>
          </div>
          <button className="btn suave chico" onClick={irHoy}>Hoy</button>
        </div>

        <div className="cal" role="grid" aria-label={`Eventos de ${MESES[mes.mes]} ${mes.anio}`}>
          {CABECERA.map((c) => <div key={c} className="cal-dia-nombre" role="columnheader">{c}</div>)}
          {dias.map((d) => {
            const clave = claveFecha(d)
            const fuera = d.getUTCMonth() !== mes.mes
            const esHoy = clave === claveFecha(hoy)
            const tema = temas[clave]?.titulo
            const i = infoEvento(d)
            const pasado = i.estado === 'pasado' || i.estado === 'hoy-terminado'
            if (!tema && !esDiaFijo(d)) {      // día libre: se le puede poner tema si no ha pasado
              if (pasado) return <div key={clave} className={`cal-celda ${fuera ? 'fuera' : ''} ${esHoy ? 'hoy' : ''}`} role="gridcell"><span className="cal-num">{d.getUTCDate()}</span></div>
              return (
                <button key={clave} role="gridcell" aria-selected={elegido === clave}
                  className={`cal-celda libre ${fuera ? 'fuera' : ''} ${esHoy ? 'hoy' : ''}`}
                  onClick={() => setElegido(clave)} aria-label={`${i.nombre}: sin evento, ponle un tema`}>
                  <span className="cal-num">{d.getUTCDate()}</span>
                </button>
              )
            }
            const tono = pasado ? 'pasado' : tema ? 'asignado' : 'hueco'
            return (
              <button key={clave} role="gridcell" aria-selected={elegido === clave}
                className={`cal-celda evento ${tono} ${fuera ? 'fuera' : ''} ${esHoy ? 'hoy' : ''}`}
                onClick={() => setElegido(clave)}
                aria-label={`${i.nombre}: ${tema ? `tema ${tema}` : 'sin tema'}`}>
                <span className="cal-num">{d.getUTCDate()}</span>
                <span className={`cal-tema ${tema ? '' : 'falta'}`}>{tema ?? (pasado ? '' : 'Sin tema')}</span>
              </button>
            )
          })}
        </div>

        <div className="cal-pie">
          <span className="cal-leyenda"><i className="asignado" />Con tema</span>
          <span className="cal-leyenda"><i className="hueco" />Falta tema</span>
          <span className="cal-leyenda"><i className="pasado" />Ya pasó</span>
          <span className="cal-leyenda">Cualquier otro día: tócalo y ponle tema</span>
        </div>
        {error && <p className="error" role="alert">{error}</p>}

        {info && (
          <div className="cal-detalle">
            <h3>{info.nombre} <span className="muted">· {info.faltan}</span></h3>
            <TemaEvento key={`tema-${elegido}`} fecha={elegido}
              alGuardar={(t) => { if (t) { registrarEventos([elegido]); setTemas((x) => ({ ...x, [elegido]: t })) } alCambiar?.() }} />
          </div>
        )}
      </div>
    </div>
  )
}
