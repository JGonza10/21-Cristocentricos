// Calendario del mes con los eventos (lunes y viernes). Al elegir un día se asignan sus turnos ahí mismo.
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { ahoraCDMX, claveFecha, esDiaDeEvento, infoEvento, proximoEvento } from '../evento.js'
import { fechaDeClave } from '../util.js'
import Turnos from './Turnos.jsx'

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

const primerNombre = (t) => t?.dirige?.nombre.split(' ')[0]

export default function CalendarioEventos({ ir, alCambiar }) {
  const hoy = ahoraCDMX()
  const [mes, setMes] = useState({ anio: hoy.getUTCFullYear(), mes: hoy.getUTCMonth() })
  const [turnos, setTurnos] = useState({})
  const [elegido, setElegido] = useState(() => proximoEvento()?.clave ?? null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [ocupado, setOcupado] = useState(false)

  const dias = diasDelMes(mes.anio, mes.mes)
  const desde = claveFecha(dias[0])
  const hasta = claveFecha(dias[dias.length - 1])

  function cargar() {
    return api(`/api/turnos?desde=${desde}&hasta=${hasta}`)
      .then((d) => { setTurnos(d.turnos); setError('') })
      .catch((e) => setError(e.message))
  }
  useEffect(() => { cargar() }, [desde, hasta])

  function mover(n) {
    setAviso('')
    setMes(({ anio, mes: m }) => {
      const d = new Date(Date.UTC(anio, m + n, 1))
      return { anio: d.getUTCFullYear(), mes: d.getUTCMonth() }
    })
  }

  async function repartir() {
    setOcupado(true)
    setAviso('')
    try {
      const d = await api('/api/turnos/repartir', { metodo: 'POST' })
      setAviso(d.asignados ? `Se asignaron ${d.asignados} turnos en los huecos de las próximas 2 semanas.` : 'No había huecos que llenar (o falta gente en el equipo).')
      await cargar()
      alCambiar?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
    }
  }

  function guardado(clave, turno) {
    setTurnos((t) => ({ ...t, [clave]: turno }))
    alCambiar?.()
  }

  const info = elegido ? infoEvento(fechaDeClave(elegido)) : null
  const yaPaso = info && (info.estado === 'pasado' || info.estado === 'hoy-terminado')

  return (
    <section className="tarjeta" id="calendario">
      <div className="cal-cabeza">
        <span className="etiqueta">Calendario de eventos</span>
        <div className="cal-nav">
          <button className="btn suave chico" onClick={() => mover(-1)} aria-label="Mes anterior">‹</button>
          <b className="cal-mes" aria-live="polite">{MESES[mes.mes]} {mes.anio}</b>
          <button className="btn suave chico" onClick={() => mover(1)} aria-label="Mes siguiente">›</button>
        </div>
      </div>

      <div className="cal" role="grid" aria-label={`Eventos de ${MESES[mes.mes]} ${mes.anio}`}>
        {CABECERA.map((c) => <div key={c} className="cal-dia-nombre" role="columnheader">{c}</div>)}
        {dias.map((d) => {
          const clave = claveFecha(d)
          const fuera = d.getUTCMonth() !== mes.mes
          const esHoy = clave === claveFecha(hoy)
          if (!esDiaDeEvento(d)) {
            return <div key={clave} className={`cal-celda ${fuera ? 'fuera' : ''} ${esHoy ? 'hoy' : ''}`} role="gridcell"><span className="cal-num">{d.getUTCDate()}</span></div>
          }
          const t = turnos[clave]
          const i = infoEvento(d)
          const pasado = i.estado === 'pasado' || i.estado === 'hoy-terminado'
          const tono = pasado ? 'pasado' : t?.dirige ? 'asignado' : 'hueco'
          return (
            <button key={clave} role="gridcell" aria-selected={elegido === clave}
              className={`cal-celda evento ${tono} ${fuera ? 'fuera' : ''} ${esHoy ? 'hoy' : ''}`}
              onClick={() => { setElegido(clave); setAviso('') }}
              aria-label={`${i.nombre}: ${t?.dirige ? `dirige ${t.dirige.nombre}` : 'sin asignar'}`}>
              <span className="cal-num">{d.getUTCDate()}</span>
              <span className="cal-quien">{t ? (primerNombre(t) ?? (pasado ? '' : 'Sin asignar')) : '…'}</span>
            </button>
          )
        })}
      </div>

      <div className="cal-pie">
        <span className="cal-leyenda"><i className="asignado" />Asignado</span>
        <span className="cal-leyenda"><i className="hueco" />Sin asignar</span>
        <span className="cal-leyenda"><i className="pasado" />Ya pasó</span>
        <button className="btn suave chico" onClick={repartir} disabled={ocupado}>Llenar huecos automáticamente</button>
      </div>
      {aviso && <p className="chico-texto" role="status">{aviso}</p>}
      {error && <p className="error" role="alert">{error}</p>}

      {info && (
        <div className="cal-detalle">
          <h3>{info.nombre} <span className="muted">· {info.misterios} · {info.faltan}</span></h3>
          <Turnos key={elegido} clave={elegido} yaPaso={yaPaso} ir={ir} alGuardar={guardado} />
        </div>
      )}
    </section>
  )
}
