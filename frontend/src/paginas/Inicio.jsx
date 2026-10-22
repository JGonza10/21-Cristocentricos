import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { ahoraCDMX, claveFecha, esDiaDeEvento, nombreFecha, proximoEvento, registrarEventos } from '../evento.js'
import { fechaDeClave, fechaHora } from '../util.js'
import { AVANCE, calcularVivo, ESTADOS, QUIEN } from '../pasos.js'
import Flujo from '../componentes/Flujo.jsx'
import Modal from '../componentes/Modal.jsx'
import CalendarioEventos from '../componentes/CalendarioEventos.jsx'
import TemaEvento from '../componentes/TemaEvento.jsx'
import GuionEvento from '../componentes/GuionEvento.jsx'
import CrearImagenes from '../componentes/CrearImagenes.jsx'
import Revision from '../componentes/Revision.jsx'
import { SubirGrabacion } from '../componentes/Grabacion.jsx'
import { AVISO_LAPTOP, enNube } from '../modo.js'
import '../styles/inicio.css'

const REFRESCO_MS = 20_000
const DIA_MS = 24 * 60 * 60 * 1000
const CLASE_ESTADO = { ok: 'ok', activo: 'activo', espera: 'warn', error: 'err', apagado: 'off', sin: 'off' }
// Ventanas de cada paso: al cumplirse uno se abre sola la del siguiente (Gonza, 2026-10-20).
const VENTANA_DE_PASO = { guion: 'guion', difusion: 'imagenes' }
const VENTANAS_DE_PASOS = ['calendario', 'tema', 'guion', 'imagenes']
const CLAVE_VISTA = 'cristo-vista-pasos'

function vistaGuardada() {
  try { return localStorage.getItem(CLAVE_VISTA) === 'lista' ? 'lista' : 'tarjetas' } catch { return 'tarjetas' }
}

/** El evento anterior/siguiente a una fecha AAAA-MM-DD (lunes, viernes o un día con tema). */
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

export default function Inicio({ ir, verDiagrama = false, alVerDiagrama, abrirIdeas }) {
  const [ahora, setAhora] = useState(() => new Date())
  const [estado, setEstado] = useState(null)
  const [avance, setAvance] = useState(null)
  const [fechaSel, setFechaSel] = useState(null) // null = el evento que toca atender
  const [modal, setModal] = useState(null)       // 'diagrama' | 'calendario' | 'tema' | 'guion' | 'imagenes' | 'subir'
  const [vista, setVista] = useState(vistaGuardada) // 'tarjetas' | 'lista' (la elige cada quien)
  const [calFecha, setCalFecha] = useState(null)
  const [temaFecha, setTemaFecha] = useState(null)
  const [abiertos, setAbiertos] = useState(null) // null = automático (se abre el paso actual)
  const [aviso, setAviso] = useState('')
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const previo = useRef(null)

  useEffect(() => {          // el botón del menú lo pide una sola vez; al volver a Inicio no se reabre
    if (verDiagrama) { setModal('diagrama'); alVerDiagrama?.() }
  }, [verDiagrama, alVerDiagrama])

  const cargarAvance = useCallback(() => {
    api(fechaSel ? `/api/avance/${fechaSel}` : '/api/avance/activo').then(setAvance).catch((e) => setError(e.message))
  }, [fechaSel])

  const cargar = useCallback(() => {
    api('/api/estado').then((d) => { registrarEventos(d.eventos_extra); setEstado(d) }).catch(() => setEstado(null))
    cargarAvance()
    setAhora(new Date())
  }, [cargarAvance])

  useEffect(() => {
    cargar()
    const t = setInterval(cargar, REFRESCO_MS)
    return () => clearInterval(t)
  }, [cargar])

  const { pasos, nodos } = calcularVivo(estado, ahora)
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
      // Se abre solo el siguiente: su ventana si tiene (guion, imágenes); si no, se cierra la del paso anterior
      // y queda abierta su tarjeta.
      const ventana = VENTANA_DE_PASO[avance.actual]
      setModal((m) => (ventana && m !== 'diagrama' ? ventana : VENTANAS_DE_PASOS.includes(m) ? null : m))
      if (!ventana) setTimeout(() => document.getElementById(`paso-${avance.actual}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }), 50)
    }
  }, [avance])

  function elegirVista(v) {
    setVista(v)
    try { localStorage.setItem(CLAVE_VISTA, v) } catch { /* sin almacenamiento */ }
  }

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
      case 'tema': return { texto: 'Abrir calendario', hacer: () => abrirCalendario(avance?.fecha) }
      case 'guion': return { texto: 'Agregar guion', hacer: () => setModal('guion') }
      case 'difusion': return { texto: 'Crear imágenes', hacer: () => setModal('imagenes') }
      case 'reels': return enNube() ? null : { texto: 'Ver en Material', hacer: () => ir('contenido') }
      case 'revision': return { texto: 'Abrir reloj', hacer: abrirReloj }
      case 'grabacion': return enNube() ? { texto: 'Se hace en la laptop', hacer: () => setAviso(AVISO_LAPTOP) }
        : { texto: 'Subir video del celular', hacer: () => setModal('subir') }
      case 'ideas': return { texto: 'Abrir Ideas', hacer: () => abrirIdeas?.() }
      default: return null
    }
  }

  // Lo que se hace ahí mismo en ciertos pasos (sin abrir otra pantalla).
  function extraDe(id) {
    if (!avance) return null
    if (id === 'revision') return <Revision key={avance.fecha} fecha={avance.fecha} alCambiar={cargarAvance} />
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
        <section className="hero con-virgen">
          <div>
          <div className="etiqueta">{proximo.estado === 'en-vivo' ? 'En vivo ahora' : 'Próximo evento'}</div>
          <h1>{proximo.nombre}</h1>
          <p className="meta">
            10:00 a 11:00 am · {proximo.faltan} ·{' '}
            {temaProximo?.tema
              ? <><b>{temaProximo.tema}</b> <button className="enlace" onClick={() => abrirTema(proximo.clave)}>Editar</button></>
              : <button className="enlace" onClick={() => abrirTema(proximo.clave)}>Poner tema</button>}
          </p>
          </div>
          <img className="hero-virgen" src="/marca/virgen.png" alt="" aria-hidden="true" width="238" height="800" />
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
                <button className="btn suave chico" onClick={() => cambiarEvento(-1)} aria-label="Evento anterior"
                  disabled={eventoVecino(avance.fecha, -1) < claveFecha(ahoraCDMX())}
                  title="Los eventos que ya pasaron no se muestran">‹</button>
                <b aria-live="polite">{avance.nombre}{avance.tema && <span className="evento-tema"> · {avance.tema}</span>}</b>
                <button className="btn suave chico" onClick={() => cambiarEvento(1)} aria-label="Evento siguiente">›</button>
                {fechaSel && <button className="enlace" onClick={() => { setFechaSel(null); previo.current = null }}>Ir al que toca</button>}
              </div>
            )}
          </div>
        </div>
        {barra}
        {mensajes}
        {guia}
      </section>

      <div className="vista-pasos" role="group" aria-label="Ver los pasos como">
        <span className="etiqueta">Pasos</span>
        <div className="vista-botones">
          <button type="button" aria-pressed={vista === 'tarjetas'} onClick={() => elegirVista('tarjetas')}>Tarjetas</button>
          <button type="button" aria-pressed={vista === 'lista'} onClick={() => elegirVista('lista')}>Lista</button>
        </div>
      </div>

      {vista === 'tarjetas' && (
        <section className="pasos-tarjetas" aria-label="Pasos del proceso">
          {pasos.map((p) => {
            const item = porId[p.id]
            const esActual = avance?.actual === p.id
            const est = item?.estado ?? 'pendiente'
            const a = accionDe(p.id)
            return (
              <article key={p.id} id={`paso-${p.id}`} className={`tarjeta paso-tarjeta a-${est} ${esActual ? 'es-actual' : ''}`}
                style={{ '--paso': `var(--p${p.numero})` }}>
                <div className="pt-cabeza">
                  <span className={`paso-num a-${est} ${esActual ? 'es-actual' : ''}`} aria-hidden="true">{est === 'hecho' ? '✓' : est === 'omitido' ? '–' : p.numero}</span>
                  <span className="chico-texto">{esActual ? 'Paso actual' : AVANCE[est]} · {QUIEN[p.q]}</span>
                </div>
                <h3>{p.t}</h3>
                <p className="chico-texto pt-texto">{item?.detalle || p.resumen}</p>
                {esActual && extraDe(p.id) && <div className="paso-extra">{extraDe(p.id)}</div>}
                <div className="botones pt-botones">
                  {a && <button className={`btn chico ${esActual ? '' : 'suave'}`} onClick={a.hacer}>{a.texto}</button>}
                  {esActual && <button className="btn suave chico" disabled={ocupado} onClick={() => marcar(p.id, 'hecho')}>Marcar como hecho</button>}
                  {esActual && <button className="enlace" disabled={ocupado} onClick={() => marcar(p.id, 'omitir')}>Omitir</button>}
                  {item?.manual && <button className="enlace" disabled={ocupado} onClick={() => marcar(p.id, 'deshacer')}>Deshacer</button>}
                </div>
              </article>
            )
          })}
        </section>
      )}

      {vista === 'lista' && <section className="pasos-lista" aria-label="Pasos del proceso">
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
      </section>}

      <Modal abierto={modal === 'diagrama'} titulo={avance ? `Proceso del ${avance.nombre.toLowerCase()}` : 'Proceso del evento'}
        ancho="completo" alCerrar={() => setModal(null)}>
        {barra}
        <Flujo pasos={pasos} nodosVivo={nodos} avance={estadosAvance} actual={avance?.actual} grande alElegirPaso={elegirPaso} />
      </Modal>

      <Modal abierto={modal === 'guion'} titulo={avance ? `Agregar guion · ${avance.nombre.toLowerCase()}` : 'Agregar guion'}
        ancho="medio" alCerrar={() => setModal(null)}>
        {avance && <GuionEvento fecha={avance.fecha} alGuardar={cargar} alPedirTema={() => abrirCalendario(avance.fecha)} />}
      </Modal>

      <Modal abierto={modal === 'imagenes'} titulo={avance ? `Crear imágenes · ${avance.nombre.toLowerCase()}` : 'Crear imágenes'}
        alCerrar={() => setModal(null)}>
        {avance && <CrearImagenes fecha={avance.fecha} listo={porId.difusion?.estado === 'hecho'} alCrear={cargar}
          alVerMaterial={() => { setModal(null); ir('contenido') }} />}
      </Modal>

      <Modal abierto={modal === 'calendario'} titulo="Calendario: fecha y tema" ancho="medio" alCerrar={() => setModal(null)}>
        <CalendarioEventos fechaInicial={calFecha} alCambiar={cargar} />
      </Modal>

      <Modal abierto={modal === 'tema'} titulo={temaFecha ? `Tema del ${nombreFechaCorto(temaFecha).toLowerCase()}` : 'Tema del evento'}
        alCerrar={() => setModal(null)}>
        {temaFecha && <TemaEvento fecha={temaFecha} alGuardar={cargar} />}
      </Modal>

      <Modal abierto={modal === 'subir'} titulo={avance ? `Video del celular del ${avance.nombre.toLowerCase()}` : 'Subir grabación'}
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
