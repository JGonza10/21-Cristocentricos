import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { claveFecha, esDiaDeEvento, nombreFecha, proximoEvento } from '../evento.js'
import { fechaDeClave, fechaHora, nombres } from '../util.js'
import { AVANCE, calcularVivo, ESTADOS, QUIEN } from '../pasos.js'
import Flujo from '../componentes/Flujo.jsx'
import Modal from '../componentes/Modal.jsx'
import CalendarioEventos from '../componentes/CalendarioEventos.jsx'
import ReporteSemanal from '../componentes/ReporteSemanal.jsx'
import TemaEvento from '../componentes/TemaEvento.jsx'
import Revision from '../componentes/Revision.jsx'
import { ControlObs, SubirGrabacion } from '../componentes/Grabacion.jsx'
import '../styles/inicio.css'

const REFRESCO_MS = 20_000
const DIA_MS = 24 * 60 * 60 * 1000
const CLASE_ESTADO = { ok: 'ok', activo: 'activo', espera: 'warn', error: 'err', apagado: 'off', sin: 'off' }

function quienes(t) {
  if (!t || (!t.dirige && t.apoyan.length === 0)) return 'Sin asignar'
  const partes = []
  if (t.dirige) partes.push(`Dirige ${t.dirige.nombre}`)
  if (t.apoyan.length) partes.push(`apoya ${nombres(t.apoyan)}`)
  return partes.join(' · ')
}

/** El lunes o viernes anterior/siguiente a una fecha AAAA-MM-DD. */
function eventoVecino(clave, direccion) {
  let d = fechaDeClave(clave)
  do d = new Date(d.getTime() + direccion * DIA_MS)
  while (!esDiaDeEvento(d))
  return claveFecha(d)
}

const nombreFechaCorto = (clave) => nombreFecha(fechaDeClave(clave))

function abrirReloj() {
  window.open('/reloj', 'reloj', 'popup,width=1280,height=720')
}

export default function Inicio({ ir }) {
  const [ahora, setAhora] = useState(() => new Date())
  const [estado, setEstado] = useState(null)
  const [turnos, setTurnos] = useState({})
  const [avance, setAvance] = useState(null)
  const [fechaSel, setFechaSel] = useState(null) // null = el evento que toca atender
  const [modal, setModal] = useState(null)       // 'diagrama' | 'calendario' | 'reporte' | 'tema' | 'subir'
  const [calFecha, setCalFecha] = useState(null)
  const [temaFecha, setTemaFecha] = useState(null)
  const [abiertos, setAbiertos] = useState(null) // null = automático (se abre el paso actual)
  const [aviso, setAviso] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [ejemploMsg, setEjemploMsg] = useState('')
  const previo = useRef(null)

  const cargarAvance = useCallback(() => {
    api(fechaSel ? `/api/avance/${fechaSel}` : '/api/avance/activo').then(setAvance).catch((e) => setError(e.message))
  }, [fechaSel])

  const cargar = useCallback(() => {
    api('/api/estado').then(setEstado).catch(() => setEstado(null))
    api('/api/turnos').then((d) => setTurnos(d.turnos)).catch(() => setTurnos({}))
    cargarAvance()
    setAhora(new Date())
  }, [cargarAvance])

  useEffect(() => {
    cargar()
    const t = setInterval(cargar, REFRESCO_MS)
    return () => clearInterval(t)
  }, [cargar])

  const { pasos, nodos } = calcularVivo(estado, turnos, ahora)
  const porId = Object.fromEntries((avance?.pasos ?? []).map((p) => [p.id, p]))
  const estadosAvance = Object.fromEntries((avance?.pasos ?? []).map((p) => [p.id, p.estado]))
  const numero = (id) => pasos.findIndex((p) => p.id === id) + 1

  // Cuando se cumple el paso en el que íbamos, avisa y abre el siguiente.
  useEffect(() => {
    if (!avance) return
    const antes = previo.current
    previo.current = { fecha: avance.fecha, actual: avance.actual }
    if (!antes || antes.fecha !== avance.fecha || antes.actual === avance.actual) return
    setAbiertos(null)
    const listo = pasos.find((p) => p.id === antes.actual)
    if (!avance.actual) setAviso(`Paso ${numero(antes.actual)} listo. ¡Este evento completó todo el proceso!`)
    else if (numero(avance.actual) > numero(antes.actual)) {
      const sigue = pasos.find((p) => p.id === avance.actual)
      setAviso(`Paso ${numero(antes.actual)} listo${listo ? `: «${listo.t}»` : ''}. Sigue el paso ${sigue.numero}: «${sigue.t}».`)
    }
  }, [avance])

  async function marcar(paso, accion) {
    setOcupado(true)
    setError('')
    try {
      const d = await api(`/api/avance/${avance.fecha}/${paso}`, { metodo: 'PUT', datos: { accion } })
      setAvance(d)
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
    }
  }

  // Solo en la copia de ejemplo (puerto 5022): simula lo que toca en el paso actual.
  async function ejemplo(accion) {
    setOcupado(true)
    setError('')
    try {
      const d = await api(`/api/ejemplo/${accion}`, { metodo: 'POST', datos: accion === 'avanzar' ? { fecha: avance?.fecha } : {} })
      setEjemploMsg(d.mensaje)
      if (d.avance) { setFechaSel(d.avance.fecha); setAvance(d.avance) } // se queda en este evento aunque termine
      else { setFechaSel(null); previo.current = null; setAbiertos(null) }
      cargar()
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
    }
  }

  function abrirCalendario(fecha = null) {
    setCalFecha(fecha)
    setModal('calendario')
  }

  function abrirTema(fecha) {
    setTemaFecha(fecha)
    setModal('tema')
  }

  // Acción propia de cada paso (además de marcar u omitir).
  function accionDe(id) {
    switch (id) {
      case 'tema': return { texto: 'Tema y guion', hacer: () => abrirTema(avance?.fecha) }
      case 'turnos': return { texto: 'Abrir calendario', hacer: () => abrirCalendario(avance?.fecha) }
      case 'vivo': return { texto: 'Abrir reloj', hacer: abrirReloj }
      case 'grabacion': return { texto: 'Subir grabación', hacer: () => setModal('subir') }
      case 'difusion': case 'reels': case 'carrusel': case 'bandeja': return { texto: 'Ir a la bandeja', hacer: () => ir('contenido') }
      case 'publicacion': case 'redes': return { texto: 'Ver publicaciones', hacer: () => ir('contenido') }
      case 'registro': return { texto: 'Descargar registro (Excel)', hacer: () => { window.location.href = '/api/registro.csv' } }
      case 'mides': return { texto: 'Ver reporte', hacer: () => setModal('reporte') }
      default: return null
    }
  }

  // Lo que se hace ahí mismo en ciertos pasos (sin abrir otra pantalla).
  function extraDe(id) {
    if (!avance) return null
    if (id === 'revision') return <Revision key={avance.fecha} fecha={avance.fecha} alCambiar={cargarAvance} />
    if (id === 'vivo' || id === 'grabacion') return <ControlObs alCambiar={cargar} />
    return null
  }

  const autoAbiertos = new Set(avance?.actual ? [avance.actual] : [])
  const estanAbiertos = abiertos ?? autoAbiertos
  function alternar(id) {
    const s = new Set(estanAbiertos)
    if (s.has(id)) s.delete(id)
    else s.add(id)
    setAbiertos(s)
  }
  function elegirPaso(id) {
    setAbiertos(new Set([id]))
    if (modal !== 'diagrama') document.getElementById(`paso-${id}`)?.scrollIntoView({ block: 'nearest' })
  }

  function cambiarEvento(direccion) {
    setAviso('')
    setAbiertos(null)
    previo.current = null
    setFechaSel(eventoVecino(avance.fecha, direccion))
  }

  const proximo = proximoEvento(ahora)
  const tProximo = proximo && turnos[proximo.clave]
  const temas = estado?.temas ?? []
  const temaProximo = proximo && temas.find((t) => t.fecha === proximo.clave)
  const faltanTema = temas.slice(0, 2).filter((t) => !t.tema)
  const actual = avance?.actual ? pasos.find((p) => p.id === avance.actual) : null
  const barra = avance && (
    <div className="avance-barra" role="progressbar" aria-valuemin={0} aria-valuemax={avance.total} aria-valuenow={avance.hechos}
      aria-label={`Avance del ${avance.nombre.toLowerCase()}`}>
      <div className="avance-pista"><span style={{ width: `${(avance.hechos / avance.total) * 100}%` }} /></div>
      <b>{avance.hechos} de {avance.total} pasos</b>
    </div>
  )
  const guia = avance && (
    <Guia avance={avance} actual={actual} item={actual && porId[actual.id]} accion={actual && accionDe(actual.id)}
      extra={actual && extraDe(actual.id)} ocupado={ocupado} alMarcar={marcar} />
  )
  const mensajes = (
    <>
      {aviso && <p className="avance-aviso" role="status">{aviso}</p>}
      {error && <p className="error" role="alert">{error}</p>}
    </>
  )

  return (
    <>
      {proximo && (
        <section className="hero">
          <div className="etiqueta">{proximo.estado === 'en-vivo' ? 'En vivo ahora' : 'Próximo evento'}</div>
          <h1>{proximo.nombre}</h1>
          <p className="meta">
            10:00 a 11:00 am · {proximo.faltan} ·{' '}
            {temaProximo?.tema
              ? <><b>{temaProximo.tema}</b> <button className="enlace" onClick={() => abrirTema(proximo.clave)}>Editar</button></>
              : <button className="enlace" onClick={() => abrirTema(proximo.clave)}>Poner tema</button>}
          </p>
          {tProximo?.dirige ? (
            <p className="meta" style={{ margin: 0 }}>
              <b>{quienes(tProximo)}</b>{' '}
              <button className="enlace" onClick={() => abrirCalendario(proximo.clave)}>Cambiar</button>
            </p>
          ) : (
            <p className="aviso">
              Todavía no se asigna quién dirige.{' '}
              <button className="enlace" onClick={() => abrirCalendario(proximo.clave)}>Asignar ahora</button>
            </p>
          )}
        </section>
      )}

      {estado?.ejemplo && (
        <section className="ejemplo-banda" aria-label="Modo ejemplo">
          <div>
            <span className="pill ambar">Modo ejemplo</span>
            <p>Datos inventados para revisar cómo funciona; tus datos reales no se tocan. «Avanzar el ejemplo» hace lo que
              haría el sistema (o tú) en el paso actual. También puedes marcar pasos o aprobar en Contenido como en la app real.</p>
            {ejemploMsg && <p className="ejemplo-msg" role="status">{ejemploMsg}</p>}
          </div>
          <div className="botones">
            <button className="btn chico" disabled={ocupado || avance?.completo} onClick={() => ejemplo('avanzar')}>Avanzar el ejemplo</button>
            <button className="btn suave chico" disabled={ocupado} onClick={() => ejemplo('reiniciar')}>Reiniciar ejemplo</button>
          </div>
        </section>
      )}

      {estado && faltanTema.length > 0 && (
        <p className="aviso-tema" role="status">
          Falta tema para {faltanTema.map((t) => nombreFechaCorto(t.fecha)).join(' y ')}. Lo ideal es tener siempre
          los próximos 2 eventos con tema (así la difusión sale con tiempo).{' '}
          <button className="enlace" onClick={() => abrirCalendario(faltanTema[0].fecha)}>Poner tema</button>
        </p>
      )}

      <section className="tarjeta proceso">
        <div className="proceso-cabeza">
          <div>
            <span className="etiqueta">Proceso del evento</span>
            {avance && (
              <div className="evento-nav">
                <button className="btn suave chico" onClick={() => cambiarEvento(-1)} aria-label="Evento anterior">‹</button>
                <b aria-live="polite">{avance.nombre}{avance.tema && <span className="evento-tema"> · {avance.tema}</span>}</b>
                <button className="btn suave chico" onClick={() => cambiarEvento(1)} aria-label="Evento siguiente">›</button>
                {fechaSel && <button className="enlace" onClick={() => { setFechaSel(null); previo.current = null }}>Ir al que toca</button>}
              </div>
            )}
          </div>
          <button className="btn suave chico" onClick={() => setModal('diagrama')}>Ver en grande</button>
        </div>
        {barra}
        <Flujo pasos={pasos} nodosVivo={nodos} avance={estadosAvance} actual={avance?.actual} alElegirPaso={elegirPaso} />
        {mensajes}
        {guia}
      </section>

      <section className="pasos-lista" aria-label="Pasos del proceso">
        {pasos.map((p) => {
          const item = porId[p.id]
          const abierto = estanAbiertos.has(p.id)
          const esActual = avance?.actual === p.id
          const a = accionDe(p.id)
          const est = item?.estado ?? 'pendiente'
          return (
            <article key={p.id} id={`paso-${p.id}`} className={`tarjeta paso a-${est} ${esActual ? 'es-actual' : ''}`}>
              <button className="paso-cabeza" aria-expanded={abierto} aria-controls={`cuerpo-${p.id}`} onClick={() => alternar(p.id)}>
                <span className={`paso-num a-${est} ${esActual ? 'es-actual' : ''}`} aria-hidden="true">{est === 'hecho' ? '✓' : est === 'omitido' ? '–' : p.numero}</span>
                <span className="paso-nombre">
                  <b>{p.t}</b>
                  <span className="chico-texto">{esActual ? 'Paso actual' : AVANCE[est]} · {QUIEN[p.q]}</span>
                </span>
                {(p.estado === 'error' || (p.estado === 'espera' && est === 'pendiente')) && <span className={`pill ${p.estado === 'error' ? 'roja' : 'ambar'}`}>{ESTADOS[p.estado]}</span>}
                <span className="paso-flecha" aria-hidden="true">{abierto ? '▴' : '▾'}</span>
              </button>
              {abierto && (
                <div className="paso-cuerpo" id={`cuerpo-${p.id}`}>
                  {item?.detalle && <p className="paso-resumen">{item.detalle}</p>}
                  {item?.manual && item.quien && <p className="chico-texto">Marcado por {item.quien}{item.cuando ? ` el ${fechaHora(item.cuando)}` : ''}.</p>}
                  {p.estado && <p className="chico-texto"><span className={`estado ${CLASE_ESTADO[p.estado]} en-linea`}>{ESTADOS[p.estado]}</span> {p.resumen}</p>}
                  {p.detalle.map((d) => <p key={d} className="chico-texto">{d}</p>)}
                  <p className="chico-texto paso-que">{p.x}</p>
                  {item && <p className="chico-texto"><b>Cómo se cumple:</b> {item.como}</p>}
                  {abierto && extraDe(p.id) && !esActual && <div className="paso-extra">{extraDe(p.id)}</div>}
                  <div className="botones paso-accion">
                    {esActual && <button className="btn chico" disabled={ocupado} onClick={() => marcar(p.id, 'hecho')}>Marcar como hecho</button>}
                    {esActual && <button className="btn suave chico" disabled={ocupado} onClick={() => marcar(p.id, 'omitir')}>Omitir: no es necesario</button>}
                    {item?.manual && <button className="btn suave chico" disabled={ocupado} onClick={() => marcar(p.id, 'deshacer')}>Deshacer</button>}
                    {a && <button className="btn suave chico" onClick={a.hacer}>{a.texto}</button>}
                  </div>
                  {!esActual && est === 'pendiente' && avance?.actual && (
                    <p className="chico-texto">Primero termina el paso {numero(avance.actual)}; así no se brinca ninguno.</p>
                  )}
                </div>
              )}
            </article>
          )
        })}
      </section>

      <Modal abierto={modal === 'diagrama'} titulo={avance ? `Proceso del ${avance.nombre.toLowerCase()}` : 'Proceso del evento'}
        ancho="grande" alCerrar={() => setModal(null)}>
        {barra}
        <Flujo pasos={pasos} nodosVivo={nodos} avance={estadosAvance} actual={avance?.actual} grande alElegirPaso={elegirPaso} />
        {mensajes}
        {guia}
      </Modal>

      <Modal abierto={modal === 'calendario'} titulo="Calendario y equipo" ancho="medio" alCerrar={() => setModal(null)}>
        <CalendarioEventos ir={ir} fechaInicial={calFecha} alCambiar={cargar} />
      </Modal>

      <Modal abierto={modal === 'reporte'} titulo="Reporte semanal" alCerrar={() => setModal(null)}>
        <ReporteSemanal alCambiar={cargar} />
      </Modal>

      <Modal abierto={modal === 'tema'} titulo={temaFecha ? `Tema del ${nombreFechaCorto(temaFecha).toLowerCase()}` : 'Tema del evento'}
        alCerrar={() => setModal(null)}>
        {temaFecha && <TemaEvento fecha={temaFecha} alGuardar={cargar} />}
      </Modal>

      <Modal abierto={modal === 'subir'} titulo={avance ? `Subir grabación del ${avance.nombre.toLowerCase()}` : 'Subir grabación'}
        alCerrar={() => setModal(null)}>
        {avance && <SubirGrabacion fecha={avance.fecha} alTerminar={cargar} />}
      </Modal>
    </>
  )
}

/** El paso en el que va el evento, con lo que hay que hacer para cumplirlo. */
function Guia({ avance, actual, item, accion, extra, ocupado, alMarcar }) {
  if (avance.completo) {
    return (
      <div className="guia completo">
        <span className="quien q-solo">Proceso completo</span>
        <h3>El {avance.nombre.toLowerCase()} cumplió los {avance.total} pasos.</h3>
        <p>Usa las flechas de arriba para ver otro evento.</p>
      </div>
    )
  }
  return (
    <div className="guia">
      <span className={`quien q-${actual.q}`}>Ahora · paso {actual.numero} de {avance.total} · {QUIEN[actual.q]}</span>
      <h3>{actual.t}</h3>
      {item?.detalle && <p className="paso-resumen">{item.detalle}</p>}
      <p>{item?.como}</p>
      {extra && <div className="paso-extra">{extra}</div>}
      <div className="botones">
        <button className="btn chico" disabled={ocupado} onClick={() => alMarcar(actual.id, 'hecho')}>Marcar como hecho</button>
        <button className="btn suave chico" disabled={ocupado} onClick={() => alMarcar(actual.id, 'omitir')}>Omitir: no es necesario</button>
        {accion && <button className="btn suave chico" onClick={accion.hacer}>{accion.texto}</button>}
      </div>
    </div>
  )
}
