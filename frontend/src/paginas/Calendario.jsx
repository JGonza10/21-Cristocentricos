import { useCallback, useEffect, useState } from 'react'
import { api } from '../api.js'
import { ahoraCDMX, claveFecha, nombreFecha } from '../fechas.js'

const MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto',
  'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
const SEMANA = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']

function diasDelMes(anio, mes) {
  const primero = new Date(Date.UTC(anio, mes, 1))
  const vacios = (primero.getUTCDay() + 6) % 7
  const total = new Date(Date.UTC(anio, mes + 1, 0)).getUTCDate()
  return [...Array(vacios).fill(null), ...Array.from({ length: total }, (_, i) => new Date(Date.UTC(anio, mes, i + 1)))]
}

export default function Calendario({ ir }) {
  const hoy = claveFecha(ahoraCDMX())
  const [mes, setMes] = useState(() => { const d = ahoraCDMX(); return { anio: d.getUTCFullYear(), mes: d.getUTCMonth() } })
  const [eventos, setEventos] = useState({})
  const [equipo, setEquipo] = useState([])
  const [elegido, setElegido] = useState(hoy)
  const [nombre, setNombre] = useState('')
  const [msg, setMsg] = useState({ texto: '', error: false })

  const clave = `${mes.anio}-${String(mes.mes + 1).padStart(2, '0')}`
  const cargarMes = useCallback(() => {
    api(`/api/eventos?mes=${clave}`)
      .then((d) => setEventos(Object.fromEntries(d.eventos.map((e) => [e.fecha, e]))))
      .catch((e) => setMsg({ texto: e.message, error: true }))
  }, [clave])

  useEffect(cargarMes, [cargarMes])
  useEffect(() => { api('/api/integrantes').then((d) => setEquipo(d.integrantes)).catch(() => {}) }, [])

  function moverMes(delta) {
    const m = mes.mes + delta
    setMes({ anio: mes.anio + Math.floor(m / 12), mes: ((m % 12) + 12) % 12 })
  }

  async function agregar(e) {
    e.preventDefault()
    try {
      const d = await api('/api/integrantes', { metodo: 'POST', datos: { nombre } })
      setEquipo([...equipo, d.integrante].sort((a, b) => a.nombre.localeCompare(b.nombre)))
      setNombre('')
      setMsg({ texto: `${d.integrante.nombre} agregado al equipo.`, error: false })
    } catch (err) {
      setMsg({ texto: err.message, error: true })
    }
  }

  async function quitar(i) {
    if (!window.confirm(`¿Quitar a ${i.nombre} del equipo?`)) return
    try {
      await api(`/api/integrantes/${i.id}`, { metodo: 'DELETE' })
      setEquipo(equipo.filter((x) => x.id !== i.id))
      cargarMes()
    } catch (err) {
      setMsg({ texto: err.message, error: true })
    }
  }

  async function alternarEnDia(i) {
    const actuales = (eventos[elegido]?.integrantes || []).map((x) => x.id)
    const ids = actuales.includes(i.id) ? actuales.filter((x) => x !== i.id) : [...actuales, i.id]
    try {
      const d = await api(`/api/eventos/${elegido}/integrantes`, { metodo: 'PUT', datos: { ids } })
      setEventos({ ...eventos, [elegido]: d.evento })
    } catch (err) {
      setMsg({ texto: err.message, error: true })
    }
  }

  const ev = eventos[elegido]
  const enDia = new Set((ev?.integrantes || []).map((x) => x.id))

  return (
    <div className="calendario">
      <section className="tarjeta">
        <div className="cal-cab">
          <h2>{MESES[mes.mes]} {mes.anio}</h2>
          <div className="acciones-fila">
            <button className="btn suave chico" onClick={() => moverMes(-1)} aria-label="Mes anterior">←</button>
            <button className="btn suave chico" onClick={() => moverMes(1)} aria-label="Mes siguiente">→</button>
          </div>
        </div>
        <div className="cal-grid">
          {SEMANA.map((s) => <span key={s} className="cal-sem" aria-hidden="true">{s}</span>)}
          {diasDelMes(mes.anio, mes.mes).map((d, i) => {
            if (!d) return <span key={`v${i}`} />
            const f = claveFecha(d)
            const e = eventos[f]
            return (
              <button key={f} className={`cal-dia ${f === elegido ? 'sel' : ''} ${f === hoy ? 'hoy' : ''} ${e?.tema ? 'con-tema' : ''}`}
                aria-pressed={f === elegido} aria-label={`${nombreFecha(d)}${e?.tema ? `, ${e.tema}` : ''}`} onClick={() => setElegido(f)}>
                <b>{d.getUTCDate()}</b>
                {e?.tema && <small>{e.tema}</small>}
              </button>
            )
          })}
        </div>
      </section>

      <section className="tarjeta">
        <span className="etiqueta">{nombreFecha(elegido)}</span>
        <h2 className="cal-tema">{ev?.tema || 'Sin tema'}</h2>
        <span className="label">Equipo de este día</span>
        {equipo.length === 0 ? <p className="chico-texto">Agrega nombres abajo para poder elegirlos.</p> : (
          <div className="chips" role="group" aria-label="Equipo de este día">
            {equipo.map((i) => (
              <button key={i.id} className="chip" aria-pressed={enDia.has(i.id)} onClick={() => alternarEnDia(i)}>{i.nombre}</button>
            ))}
          </div>
        )}
        <button className="btn suave" style={{ marginTop: 14 }} onClick={() => ir('evento', elegido)}>
          {ev?.tema ? 'Ver evento' : 'Agregar tema y guion'}
        </button>
      </section>

      <section className="tarjeta">
        <span className="etiqueta">Equipo</span>
        <ul className="lista">
          {equipo.map((i) => (
            <li key={i.id} className="item">
              <b>{i.nombre}</b>
              <button className="btn suave chico" aria-label={`Quitar a ${i.nombre}`} onClick={() => quitar(i)}>Quitar</button>
            </li>
          ))}
        </ul>
        <form className="acciones-fila" style={{ marginTop: 12 }} onSubmit={agregar}>
          <input aria-label="Nombre del integrante" maxLength={60} value={nombre} placeholder="Nombre y apellido"
            onChange={(e) => setNombre(e.target.value)} required minLength={2} />
          <button className="btn">Agregar</button>
        </form>
        <p className={msg.error ? 'error' : 'chico-texto'} role="status">{msg.texto}</p>
        <p className="chico-texto">Solo se guarda el nombre, para organizar al equipo. No se comparte con nadie.</p>
      </section>
    </div>
  )
}
