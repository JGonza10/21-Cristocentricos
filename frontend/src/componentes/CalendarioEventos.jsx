// Calendario del mes con los eventos (lunes y viernes) y las personas del equipo. Se abre en una ventana
// desde Inicio. Al elegir un día se asignan sus turnos ahí mismo; al lado se ve quién lleva cuántos turnos.
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { ahoraCDMX, claveFecha, esDiaDeEvento, fechaCorta, infoEvento, proximoEvento } from '../evento.js'
import { fechaDeClave } from '../util.js'
import TemaEvento from './TemaEvento.jsx'
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

const primerNombre = (i) => i?.nombre.split(' ')[0]

export default function CalendarioEventos({ ir, alCambiar, fechaInicial }) {
  const hoy = ahoraCDMX()
  const inicial = fechaInicial ? fechaDeClave(fechaInicial) : hoy
  const [mes, setMes] = useState({ anio: inicial.getUTCFullYear(), mes: inicial.getUTCMonth() })
  const [turnos, setTurnos] = useState({})
  const [temas, setTemas] = useState({})
  const [elegido, setElegido] = useState(() => fechaInicial ?? proximoEvento()?.clave ?? null)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [version, setVersion] = useState(0) // para que el panel del equipo se recargue

  const dias = diasDelMes(mes.anio, mes.mes)
  const desde = claveFecha(dias[0])
  const hasta = claveFecha(dias[dias.length - 1])

  function cargar() {
    return Promise.all([api(`/api/turnos?desde=${desde}&hasta=${hasta}`), api(`/api/temas?desde=${desde}&hasta=${hasta}`)])
      .then(([d, t]) => { setTurnos(d.turnos); setTemas(t.temas); setError('') })
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

  function irHoy() {
    setMes({ anio: hoy.getUTCFullYear(), mes: hoy.getUTCMonth() })
    setElegido(proximoEvento()?.clave ?? null)
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
    <div className="cal-ventana">
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
            if (!esDiaDeEvento(d)) {
              return <div key={clave} className={`cal-celda ${fuera ? 'fuera' : ''} ${esHoy ? 'hoy' : ''}`} role="gridcell"><span className="cal-num">{d.getUTCDate()}</span></div>
            }
            const t = turnos[clave]
            const tema = temas[clave]?.titulo
            const i = infoEvento(d)
            const pasado = i.estado === 'pasado' || i.estado === 'hoy-terminado'
            const tono = pasado ? 'pasado' : t?.dirige ? 'asignado' : 'hueco'
            return (
              <button key={clave} role="gridcell" aria-selected={elegido === clave}
                className={`cal-celda evento ${tono} ${fuera ? 'fuera' : ''} ${esHoy ? 'hoy' : ''}`}
                onClick={() => { setElegido(clave); setAviso('') }}
                aria-label={`${i.nombre}: ${tema ? `tema ${tema}, ` : 'sin tema, '}${t?.dirige ? `dirige ${t.dirige.nombre}` : 'sin asignar'}${t?.apoyan.length ? `, apoya ${t.apoyan.map((x) => x.nombre).join(', ')}` : ''}`}>
                <span className="cal-num">{d.getUTCDate()}</span>
                <span className={`cal-tema ${tema ? '' : 'falta'}`}>{tema ?? (pasado ? '' : 'Sin tema')}</span>
                {t ? (
                  <>
                    <span className="cal-quien">{primerNombre(t.dirige) ?? (pasado ? '' : 'Sin asignar')}</span>
                    {t.apoyan.length > 0 && <span className="cal-apoya">+ {t.apoyan.map(primerNombre).join(', ')}</span>}
                  </>
                ) : <span className="cal-quien">…</span>}
              </button>
            )
          })}
        </div>

        <div className="cal-pie">
          <span className="cal-leyenda"><i className="asignado" />Asignado</span>
          <span className="cal-leyenda"><i className="hueco" />Sin asignar</span>
          <span className="cal-leyenda"><i className="pasado" />Ya pasó</span>
          <span className="cal-leyenda"><i className="sin-tema" />Sin tema</span>
          <button className="btn suave chico" onClick={repartir} disabled={ocupado}>Llenar huecos automáticamente</button>
        </div>
        {aviso && <p className="chico-texto" role="status">{aviso}</p>}
        {error && <p className="error" role="alert">{error}</p>}

        {info && (
          <div className="cal-detalle">
            <h3>{info.nombre} <span className="muted">· {info.faltan}</span></h3>
            <TemaEvento key={`tema-${elegido}`} fecha={elegido}
              alGuardar={(t) => { if (t) setTemas((x) => ({ ...x, [elegido]: t })); alCambiar?.() }} />
            <h3 className="cal-sub">Quién dirige y quién apoya</h3>
            <Turnos key={elegido} clave={elegido} yaPaso={yaPaso} ir={ir} alGuardar={(c, t) => { guardado(c, t); setVersion((v) => v + 1) }} />
          </div>
        )}
      </div>

      <EquipoDelMes turnos={turnos} mes={mes} version={version} alCambiar={() => { setVersion((v) => v + 1); alCambiar?.() }} />
    </div>
  )
}

/** Personas del equipo: cuántos turnos llevan este mes, su próximo turno y alta rápida. */
function EquipoDelMes({ turnos, mes, version, alCambiar }) {
  const [gente, setGente] = useState(null)
  const [nombre, setNombre] = useState('')
  const [correo, setCorreo] = useState('')
  const [dirige, setDirige] = useState(true)
  const [aviso, setAviso] = useState(false)
  const [error, setError] = useState('')
  const [mensaje, setMensaje] = useState('')
  const [ocupado, setOcupado] = useState(false)

  useEffect(() => {
    api('/api/equipo').then((d) => setGente(d.integrantes.filter((i) => i.activo))).catch((e) => setError(e.message))
  }, [version])

  const hoyClave = claveFecha(ahoraCDMX())
  const conteo = {}
  for (const [clave, t] of Object.entries(turnos)) {
    const f = fechaDeClave(clave)
    const delMes = f.getUTCMonth() === mes.mes
    for (const [rol, lista] of [['dirige', t.dirige ? [t.dirige] : []], ['apoya', t.apoyan]]) {
      for (const p of lista) {
        const c = conteo[p.id] ??= { dirige: 0, apoya: 0, proximo: null }
        if (delMes) c[rol] += 1
        if (clave >= hoyClave && (!c.proximo || clave < c.proximo)) c.proximo = clave
      }
    }
  }

  async function agregar(e) {
    e.preventDefault()
    setOcupado(true)
    setError('')
    setMensaje('')
    try {
      await api('/api/equipo', { metodo: 'POST', datos: { nombre, correo, puede_dirigir: dirige, aviso } })
      setMensaje(`${nombre} ya está en el equipo.`)
      setNombre('')
      setCorreo('')
      setAviso(false)
      alCambiar()
    } catch (err) {
      setError(err.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <aside className="cal-equipo" aria-label="Personas del equipo">
      <h3>Equipo</h3>
      {gente === null && !error && <p className="chico-texto">Cargando…</p>}
      {gente?.length === 0 && <p className="chico-texto">Todavía no hay integrantes. Agrega al primero aquí abajo.</p>}
      {gente?.length > 0 && (
        <ul className="cal-gente">
          {gente.map((i) => {
            const c = conteo[i.id] ?? { dirige: 0, apoya: 0, proximo: null }
            return (
              <li key={i.id}>
                <span className="cal-av" aria-hidden="true">{i.nombre.split(' ').map((x) => x[0]).slice(0, 2).join('')}</span>
                <div>
                  <b>{i.nombre}</b>
                  <span className="chico-texto">
                    {c.dirige} dirige · {c.apoya} apoya este mes{!i.puede_dirigir && ' · solo apoya'}
                  </span>
                  <span className="chico-texto">{c.proximo ? `Próximo: ${fechaCorta(fechaDeClave(c.proximo))}` : 'Sin turnos próximos'}</span>
                </div>
              </li>
            )
          })}
        </ul>
      )}
      <form className="formulario cal-alta" onSubmit={agregar}>
        <h3>Agregar persona</h3>
        <div className="campo">
          <label htmlFor="cal-nombre">Nombre</label>
          <input id="cal-nombre" value={nombre} maxLength={80} required autoComplete="off" onChange={(e) => setNombre(e.target.value)} />
        </div>
        <div className="campo">
          <label htmlFor="cal-correo">Correo (para su calendario)</label>
          <input id="cal-correo" type="email" value={correo} maxLength={120} required autoComplete="off" inputMode="email" onChange={(e) => setCorreo(e.target.value)} />
        </div>
        <label className="casilla"><input type="checkbox" checked={dirige} onChange={(e) => setDirige(e.target.checked)} /> Puede dirigir</label>
        <label className="casilla"><input type="checkbox" checked={aviso} required onChange={(e) => setAviso(e.target.checked)} /> Le informé el aviso de privacidad (texto completo en Ajustes)</label>
        {error && <p className="error" role="alert">{error}</p>}
        {mensaje && <p className="chico-texto" role="status">{mensaje}</p>}
        <button className="btn chico" type="submit" disabled={ocupado}>Agregar</button>
      </form>
    </aside>
  )
}
