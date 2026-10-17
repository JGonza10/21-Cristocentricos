// Diagrama del flujo estilo lienzo (como la guía): recuadros por tipo, conexiones curvas, reproductor paso a paso
// y, encima, el estado en vivo de cada recuadro que el sistema conoce.
import { useEffect, useRef, useState } from 'react'
import { CONEXIONES, ESTADOS, LIENZO, NODOS, QUIEN } from '../pasos.js'
import '../styles/lienzo.css'

const PORID = Object.fromEntries(NODOS.map((n) => [n.id, n]))
const mitad = (n) => n.r || 36
const DURACION_PASO = 4200

function geometria(c) {
  const A = PORID[c.a]
  const B = PORID[c.b]
  const x1 = A.x + mitad(A)
  const y1 = A.y + (c.sa || 0)
  const xt = B.x - mitad(B) - 5
  const y2 = B.y
  const x2 = xt - 8
  const dx = Math.max(40, (x2 - x1) / 2)
  return {
    d: `M${x1},${y1} C${x1 + dx},${y1} ${x2 - dx},${y2} ${x2},${y2}`,
    punta: `${xt},${y2} ${xt - 9},${y2 - 5.5} ${xt - 9},${y2 + 5.5}`,
    a: [x1, y1], b: [B.x - mitad(B), y2],
  }
}
const GEO = Object.fromEntries(CONEXIONES.map((c) => [c.id, geometria(c)]))

function Iconos() {
  const g = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round', strokeLinejoin: 'round' }
  return (
    <defs>
      <symbol id="i-bolt" viewBox="0 0 24 24"><path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" {...g} /></symbol>
      <symbol id="i-cal" viewBox="0 0 24 24"><g {...g}><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M3 10h18M8 3v4M16 3v4" /></g></symbol>
      <symbol id="i-folder" viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" {...g} /></symbol>
      <symbol id="i-film" viewBox="0 0 24 24"><g {...g}><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4" /></g></symbol>
      <symbol id="i-img" viewBox="0 0 24 24"><g {...g}><rect x="3" y="5" width="18" height="14" rx="2" /><circle cx="9" cy="10" r="1.6" /><path d="M21 16l-5-5-8 8" /></g></symbol>
      <symbol id="i-shield" viewBox="0 0 24 24"><g {...g}><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /><path d="M8.5 12l2.5 2.5L16 9.5" /></g></symbol>
      <symbol id="i-send" viewBox="0 0 24 24"><g {...g}><path d="M22 2L11 13" /><path d="M22 2l-7 20-4-9-9-4z" /></g></symbol>
      <symbol id="i-sheet" viewBox="0 0 24 24"><g {...g}><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M4 9h16M4 15h16M10 9v12" /></g></symbol>
      <symbol id="i-pen" viewBox="0 0 24 24"><g {...g}><path d="M4 20l1-4L16.5 4.5a2 2 0 0 1 3 3L8 19z" /><path d="M14 7l3 3" /></g></symbol>
      <symbol id="i-check" viewBox="0 0 24 24"><g {...g}><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M8 8l1.5 1.5L12 7M8 14l1.5 1.5L12 13M14 9h3M14 15h3" /></g></symbol>
      <symbol id="i-chart" viewBox="0 0 24 24"><g {...g}><path d="M4 20V4M4 20h16" /><path d="M8 16v-4M12 16V8M16 16v-6" /></g></symbol>
      <symbol id="i-users" viewBox="0 0 24 24"><g {...g}><circle cx="9" cy="8" r="3.2" /><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6" /><circle cx="17" cy="9" r="2.4" /><path d="M16.5 14c2.7 0 4.5 2 4.5 5" /></g></symbol>
      <symbol id="i-x" viewBox="0 0 24 24"><g {...g}><circle cx="12" cy="12" r="9" /><path d="M9 9l6 6M15 9l-6 6" /></g></symbol>
      <symbol id="i-ig" viewBox="0 0 24 24"><g {...g}><rect x="4" y="4" width="16" height="16" rx="5" /><circle cx="12" cy="12" r="3.6" /><circle cx="17" cy="7" r=".6" fill="currentColor" /></g></symbol>
      <symbol id="i-fb" viewBox="0 0 24 24"><path d="M14 8h3V4h-3a4 4 0 0 0-4 4v3H7v4h3v6h4v-6h3l1-4h-4V8z" {...g} /></symbol>
      <symbol id="i-tt" viewBox="0 0 24 24"><g {...g}><path d="M14 4v10.5a3.5 3.5 0 1 1-3.5-3.5" /><path d="M14 4c.5 2.5 2.2 4 5 4" /></g></symbol>
      <symbol id="i-yt" viewBox="0 0 24 24"><g {...g}><rect x="2" y="6" width="20" height="12" rx="4" /><path d="M10 9l6 3-6 3z" /></g></symbol>
      <symbol id="i-tv" viewBox="0 0 24 24"><g {...g}><rect x="3" y="7" width="18" height="12" rx="2" /><path d="M8 3l4 4 4-4" /></g></symbol>
    </defs>
  )
}

export default function Flujo({ pasos, nodosVivo, trabajando, alVerTarjeta }) {
  const lienzo = useRef(null)
  const [paso, setPaso] = useState(null) // null = vista general con el estado en vivo
  const [jugando, setJugando] = useState(false)
  const quieto = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const pasoDe = (idNodo) => pasos.findIndex((p) => p.n.includes(idNodo))
  const pasoDeCx = (idCx) => pasos.findIndex((p) => p.v.includes(idCx))

  useEffect(() => {
    if (!jugando) return undefined
    const t = setTimeout(() => {
      if (paso >= pasos.length - 1) setJugando(false)
      else setPaso(paso + 1)
    }, DURACION_PASO)
    return () => clearTimeout(t)
  }, [jugando, paso, pasos.length])

  useEffect(() => {
    if (paso === null || !lienzo.current) return
    const xs = pasos[paso].n.map((id) => PORID[id].x)
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2
    const el = lienzo.current
    const escala = el.scrollWidth / LIENZO.ancho
    el.scrollTo?.({ left: Math.max(0, cx * escala - el.clientWidth / 2), behavior: quieto ? 'auto' : 'smooth' })
  }, [paso, pasos, quieto])

  function ir(i) { setJugando(false); setPaso(i) }
  function ejecutar() {
    if (jugando) { setJugando(false); return }
    setPaso(paso === null || paso >= pasos.length - 1 ? 0 : paso)
    setJugando(true)
  }

  const actual = paso === null ? null : pasos[paso]

  return (
    <>
      <div className="lienzo-barra">
        <div className="lienzo-nombre"><b>Flujo del evento</b>
          {trabajando ? <span className="pill-vivo">Activo</span> : <span className="pill-vivo off">Agentes apagados</span>}
        </div>
        <div className="botones-fila">
          {paso !== null && <button className="btn suave chico" onClick={() => { setJugando(false); setPaso(null) }}>Ver estado en vivo</button>}
          <button className="btn chico" onClick={ejecutar}>{jugando ? 'Pausar' : paso === pasos.length - 1 ? 'Ejecutar otra vez' : 'Ejecutar flujo'}</button>
        </div>
      </div>
      <div className={`lienzo ${paso === null ? 'general' : 'enfocado'} ${trabajando ? 'trabajando' : ''}`} ref={lienzo} tabIndex={0}
        aria-label="Lienzo del flujo. Se desliza hacia los lados.">
        <svg className="lienzo-svg" viewBox={`0 0 ${LIENZO.ancho} ${LIENZO.alto}`} role="img"
          aria-label="Flujo del evento: turnos, preparación con Claude, evento en vivo, grabación, agentes de reels y carrusel, bandeja de aprobación, agente de publicación, cinco redes y hoja de registro.">
          <Iconos />
          {CONEXIONES.map((c) => {
            const s = pasoDeCx(c.id)
            const fase = paso === null ? '' : s < paso && s >= 0 ? 'hecha' : s === paso ? 'viva' : ''
            const vivaEnVivo = paso === null && trabajando && (nodosVivo[c.a]?.estado === 'activo' || nodosVivo[c.b]?.estado === 'activo')
            const g = GEO[c.id]
            return (
              <g key={c.id} className={`cx ${c.fija ? 'fija' : ''} ${fase} ${vivaEnVivo ? 'viva' : ''}`}>
                <path className="l" d={g.d} />
                <polygon points={g.punta} />
                <circle className="asa" cx={g.a[0]} cy={g.a[1]} r="5" />
                <circle className="asa" cx={g.b[0]} cy={g.b[1]} r="5" />
                {c.l && <Etiqueta texto={c.l} d={g.d} />}
                {fase === 'viva' && !quieto && <Punto key={paso} d={g.d} />}
              </g>
            )
          })}
          {NODOS.map((n) => {
            const h = mitad(n)
            const s = pasoDe(n.id)
            const fase = paso === null ? '' : s < paso ? 'hecho' : s === paso ? 'actual' : ''
            const vivo = nodosVivo[n.id]
            return (
              <g key={n.id} className={`nodo d-${n.k} ${fase} ${vivo?.estado ? `v-${vivo.estado}` : ''}`} transform={`translate(${n.x},${n.y})`}
                tabIndex={0} role="button" aria-label={`${n.t}. ${n.s}${vivo?.estado ? `. ${ESTADOS[vivo.estado]}: ${vivo.corto}` : ''}`}
                onClick={() => s >= 0 && ir(s)} onKeyDown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && s >= 0) { e.preventDefault(); ir(s) } }}>
                <rect className="anillo" x={-h - 6} y={-h - 6} width={2 * h + 12} height={2 * h + 12} rx="20" />
                <rect className="tile" x={-h} y={-h} width={2 * h} height={2 * h} rx="16" />
                <use className="ico" href={`#i-${n.i}`} x={-h * 0.42} y={-h * 0.42} width={h * 0.84} height={h * 0.84} />
                {vivo?.estado && <circle className="insignia" cx={h - 4} cy={-h + 4} r="8" />}
                <text className="t" x="0" y={h + 22}>{n.t}</text>
                <text className="s" x="0" y={h + 39}>{n.s}</text>
                {vivo?.corto && <text className="vivo" x="0" y={h + 56}>{vivo.corto}</text>}
              </g>
            )
          })}
        </svg>
      </div>
      <div className="lienzo-chips" aria-label="Colores">
        <span><i className="c-disp" />Disparador</span><span><i className="c-agente" />Agente</span><span><i className="c-humano" />Tú decides</span>
        <span><i className="c-verde" />Sube solo</span><span><i className="c-plata" />Archivo o lo subes tú</span><span><i className="c-hab" />Se la pides a Claude</span>
        <span className="sep">Puntos de estado:</span>
        {Object.entries(ESTADOS).map(([k, v]) => <span key={k} className={`ley-v v-${k}`}><i />{v}</span>)}
      </div>

      <div className="panel-paso" aria-live="polite">
        {actual ? (
          <>
            <span className={`quien q-${actual.q}`}>Paso {paso + 1} de {pasos.length} · {QUIEN[actual.q]}</span>
            <h3>{actual.t}</h3>
            <p>{actual.x}</p>
          </>
        ) : (
          <>
            <span className="quien q-solo">Estado en vivo</span>
            <h3>Así va el trabajo ahora</h3>
            <p>Los puntos de color sobre cada recuadro muestran cómo está. Toca un recuadro o un número para ver ese paso, o «Ejecutar flujo» para recorrerlo completo. En el celular, desliza el lienzo hacia los lados.</p>
          </>
        )}
        <div className="botones-fila panel-nav">
          <button className="btn suave chico" onClick={() => ir(Math.max(0, (paso ?? 1) - 1))} disabled={paso === null || paso === 0}>Anterior</button>
          <button className="btn suave chico" onClick={() => ir(paso === null ? 0 : Math.min(pasos.length - 1, paso + 1))} disabled={paso === pasos.length - 1}>Siguiente</button>
          {actual && <button className="btn suave chico" onClick={() => alVerTarjeta(actual.id)}>Ver su tarjeta</button>}
        </div>
        <div className="numeros" role="group" aria-label="Ir a un paso">
          {pasos.map((p, i) => (
            <button key={p.id} className={`num v-${p.estado ?? 'ninguno'}`} aria-current={paso === i ? 'step' : undefined}
              aria-label={`Ir al paso ${i + 1}: ${p.t}`} onClick={() => ir(i)}>{i + 1}</button>
          ))}
        </div>
      </div>
    </>
  )
}

// Punto dorado que recorre la conexión una vez (como en la guía).
function Punto({ d }) {
  const ref = useRef(null)
  useEffect(() => {
    const c = ref.current
    const guia = c.parentNode.querySelector('path.l') // la propia conexión (dibujada, para que getTotalLength funcione)
    const largo = guia.getTotalLength()
    let inicio = null
    let id = 0
    const mover = (t) => {
      if (inicio === null) inicio = t
      const k = Math.min(1, (t - inicio) / 1100)
      const p = guia.getPointAtLength(largo * k)
      c.setAttribute('cx', p.x)
      c.setAttribute('cy', p.y)
      if (k < 1) id = requestAnimationFrame(mover)
    }
    id = requestAnimationFrame(mover)
    return () => cancelAnimationFrame(id)
  }, [d])
  return <circle ref={ref} className="punto" r="7" cx="-50" cy="-50" />
}

function Etiqueta({ texto, d }) {
  // Punto medio aproximado de la curva (promedio de sus 4 puntos de control).
  const nums = d.match(/-?\d+(\.\d+)?/g).map(Number)
  const x = (nums[0] + nums[2] + nums[4] + nums[6]) / 4
  const y = (nums[1] + nums[3] + nums[5] + nums[7]) / 4
  const w = texto.length * 6.3 + 18
  return (
    <g className="pill">
      <rect x={x - w / 2} y={y - 11} width={w} height="22" rx="11" />
      <text x={x} y={y + 4}>{texto}</text>
    </g>
  )
}
