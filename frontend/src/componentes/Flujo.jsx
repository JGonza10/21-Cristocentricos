// Diagrama del flujo estilo lienzo (como la guía). Se ajusta al ancho disponible.
//   Modo avance (normal): marca los pasos hechos, omitidos y el paso en el que va el evento.
//   Modo recorrido («Ver cómo funciona»): pasa solo por los 11 pasos explicando cada uno.
// Encima, una marca roja avisa de errores en vivo (publicación fallida, grabación con error…).
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
    medio: [(x1 + x1 + dx + x2 - dx + x2) / 4, (y1 + y1 + y2 + y2) / 4],
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

export default function Flujo({ pasos, nodosVivo, avance, actual, grande = false, alElegirPaso }) {
  const [recorrido, setRecorrido] = useState(null) // índice del paso explicado, o null = modo avance
  const quieto = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const indice = Object.fromEntries(pasos.map((p, i) => [p.id, i]))
  const pasoDeNodo = Object.fromEntries(pasos.flatMap((p) => p.n.map((n) => [n, p.id])))
  const pasoDeCx = Object.fromEntries(pasos.flatMap((p) => p.v.map((v) => [v, p.id])))

  useEffect(() => {
    if (recorrido === null) return undefined
    const t = setTimeout(() => setRecorrido(recorrido >= pasos.length - 1 ? null : recorrido + 1), DURACION_PASO)
    return () => clearTimeout(t)
  }, [recorrido, pasos.length])

  // Fase de cada paso: en modo recorrido según el paso explicado; en modo avance según el evento.
  function fase(idPaso) {
    if (!idPaso) return ''
    if (recorrido !== null) {
      const i = indice[idPaso]
      return i < recorrido ? 'hecho' : i === recorrido ? 'actual' : 'futuro'
    }
    if (idPaso === actual) return 'actual'
    return avance?.[idPaso] === 'hecho' ? 'hecho' : avance?.[idPaso] === 'omitido' ? 'omitido' : 'futuro'
  }

  const explicado = recorrido === null ? null : pasos[recorrido]

  return (
    <div className={`flujo-caja ${grande ? 'grande' : ''}`}>
      <div className="lienzo-barra">
        <b>{recorrido === null ? 'Avance del evento' : 'Cómo funciona'}</b>
        <button className="btn suave chico" onClick={() => setRecorrido(recorrido === null ? 0 : null)}>
          {recorrido === null ? 'Ver cómo funciona' : 'Volver a mi avance'}
        </button>
      </div>
      <div className={`lienzo ${recorrido === null ? 'modo-avance' : 'modo-recorrido'}`} tabIndex={grande ? 0 : undefined}
        aria-label={grande ? 'Lienzo del flujo. En pantallas angostas se desliza hacia los lados.' : undefined}>
        <svg className="lienzo-svg" viewBox={`0 0 ${LIENZO.ancho} ${LIENZO.alto}`} role="img"
          aria-label="Flujo del evento en 11 pasos: turnos, preparación, evento en vivo, grabación, reels, carrusel, bandeja, publicación, redes, hoja de registro y reporte semanal.">
          <Iconos />
          {CONEXIONES.map((c) => {
            const f = fase(pasoDeCx[c.id])
            const g = GEO[c.id]
            const ancho = c.l ? c.l.length * 6.3 + 18 : 0
            return (
              <g key={c.id} className={`cx ${c.fija ? 'fija' : ''} ${f === 'hecho' || f === 'omitido' ? 'hecha' : ''} ${f === 'actual' ? 'viva' : ''}`}>
                <path className="l" d={g.d} />
                <polygon points={g.punta} />
                <circle className="asa" cx={g.a[0]} cy={g.a[1]} r="5" />
                <circle className="asa" cx={g.b[0]} cy={g.b[1]} r="5" />
                {c.l && (
                  <g className="pill">
                    <rect x={g.medio[0] - ancho / 2} y={g.medio[1] - 11} width={ancho} height="22" rx="11" />
                    <text x={g.medio[0]} y={g.medio[1] + 4}>{c.l}</text>
                  </g>
                )}
                {f === 'actual' && recorrido !== null && !quieto && <Punto key={recorrido} />}
              </g>
            )
          })}
          {NODOS.map((n) => {
            const h = mitad(n)
            const idPaso = pasoDeNodo[n.id]
            const f = fase(idPaso)
            const vivo = nodosVivo[n.id]
            const error = vivo?.estado === 'error'
            const paso = pasos[indice[idPaso]]
            const texto = f === 'hecho' ? 'Hecho' : f === 'omitido' ? 'Omitido' : f === 'actual' ? 'Paso actual' : 'Pendiente'
            return (
              <g key={n.id} className={`nodo d-${n.k} f-${f || 'ninguna'} ${error ? 'v-error' : ''}`} transform={`translate(${n.x},${n.y})`}
                tabIndex={0} role="button" aria-label={`Paso ${paso?.numero}: ${n.t}. ${texto}${error ? `. Error: ${vivo.corto}` : ''}`}
                onClick={() => idPaso && alElegirPaso?.(idPaso)}
                onKeyDown={(e) => { if ((e.key === 'Enter' || e.key === ' ') && idPaso) { e.preventDefault(); alElegirPaso?.(idPaso) } }}>
                <rect className="anillo" x={-h - 7} y={-h - 7} width={2 * h + 14} height={2 * h + 14} rx="20" />
                <rect className="tile" x={-h} y={-h} width={2 * h} height={2 * h} rx="16" />
                <use className="ico" href={`#i-${n.i}`} x={-h * 0.42} y={-h * 0.42} width={h * 0.84} height={h * 0.84} />
                {error ? (
                  <g className="marca m-error" transform={`translate(${h - 4},${-h + 4})`}><circle r="10" /><path d="M-3.5,-3.5 L3.5,3.5 M3.5,-3.5 L-3.5,3.5" /></g>
                ) : f === 'hecho' ? (
                  <g className="marca m-hecho" transform={`translate(${h - 4},${-h + 4})`}><circle r="10" /><path d="M-4.5,0.5 L-1.5,3.5 L4.5,-3" /></g>
                ) : f === 'omitido' ? (
                  <g className="marca m-omitido" transform={`translate(${h - 4},${-h + 4})`}><circle r="10" /><path d="M-4,0 L4,0" /></g>
                ) : null}
                <text className="t" x="0" y={h + 24}>{n.t}</text>
                <text className="s" x="0" y={h + 42}>{n.s}</text>
              </g>
            )
          })}
        </svg>
      </div>

      {explicado ? (
        <div className="recorrido-panel" aria-live="polite">
          <span className={`quien q-${explicado.q}`}>Paso {recorrido + 1} de {pasos.length} · {QUIEN[explicado.q]}</span>
          <h3>{explicado.t}</h3>
          <p>{explicado.x}</p>
          <div className="botones-fila">
            <button className="btn suave chico" onClick={() => setRecorrido(Math.max(0, recorrido - 1))} disabled={recorrido === 0}>Anterior</button>
            <button className="btn suave chico" onClick={() => setRecorrido(recorrido + 1 >= pasos.length ? null : recorrido + 1)}>
              {recorrido + 1 >= pasos.length ? 'Terminar' : 'Siguiente'}
            </button>
          </div>
        </div>
      ) : (
        <div className="lienzo-chips" aria-hidden="true">
          <span className="ley-a hecho"><i />Hecho</span><span className="ley-a omitido"><i />Omitido</span>
          <span className="ley-a actual"><i />Paso actual</span><span className="ley-a error"><i />{ESTADOS.error}</span>
          <span><i className="c-humano" />Lo haces tú</span><span><i className="c-agente" />Lo hace un agente</span><span><i className="c-hab" />Se la pides a Claude</span>
        </div>
      )}
    </div>
  )
}

// Punto dorado que recorre su conexión una vez (como en la guía).
function Punto() {
  const ref = useRef(null)
  useEffect(() => {
    const c = ref.current
    const guia = c.parentNode.querySelector('path.l')
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
  }, [])
  return <circle ref={ref} className="punto" r="7" cx="-50" cy="-50" />
}
