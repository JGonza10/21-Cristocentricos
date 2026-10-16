// Diagrama animado del flujo de trabajo. Las cajas son botones en una cuadrícula (se acomoda sola en
// celular) y las flechas se dibujan encima midiendo dónde quedó cada caja.
import { useLayoutEffect, useRef, useState } from 'react'
import { CONEXIONES, ESTADOS } from '../pasos.js'

const PUNTA = 7

function flecha(a, b) {
  const ca = { x: (a.left + a.right) / 2, y: (a.top + a.bottom) / 2 }
  const cb = { x: (b.left + b.right) / 2, y: (b.top + b.bottom) / 2 }
  const dx = cb.x - ca.x
  const dy = cb.y - ca.y
  if (Math.abs(dx) > Math.abs(dy)) {
    const s = Math.sign(dx)
    const x1 = s > 0 ? a.right : a.left
    const x2 = (s > 0 ? b.left : b.right) - s * PUNTA
    const m = (x1 + x2) / 2
    return {
      d: `M${x1} ${ca.y} C${m} ${ca.y} ${m} ${cb.y} ${x2} ${cb.y}`,
      punta: `${x2 + s * PUNTA},${cb.y} ${x2},${cb.y - 4.5} ${x2},${cb.y + 4.5}`,
    }
  }
  const s = Math.sign(dy)
  const y1 = s > 0 ? a.bottom : a.top
  const y2 = (s > 0 ? b.top : b.bottom) - s * PUNTA
  const m = (y1 + y2) / 2
  return {
    d: `M${ca.x} ${y1} C${ca.x} ${m} ${cb.x} ${m} ${cb.x} ${y2}`,
    punta: `${cb.x},${y2 + s * PUNTA} ${cb.x - 4.5},${y2} ${cb.x + 4.5},${y2}`,
  }
}

export default function Flujo({ pasos, trabajando, alElegir }) {
  const caja = useRef(null)
  const nodos = useRef({})
  const [lineas, setLineas] = useState([])
  const porId = Object.fromEntries(pasos.map((p) => [p.id, p]))

  useLayoutEffect(() => {
    function medir() {
      if (!caja.current) return
      const base = caja.current.getBoundingClientRect()
      const r = (id) => {
        const b = nodos.current[id].getBoundingClientRect()
        return { left: b.left - base.left, right: b.right - base.left, top: b.top - base.top, bottom: b.bottom - base.top }
      }
      setLineas(CONEXIONES.map(([a, b]) => ({
        id: `${a}-${b}`, ...flecha(r(a), r(b)),
        activa: porId[a]?.estado === 'activo' || porId[b]?.estado === 'activo',
      })))
    }
    medir()
    const ro = new ResizeObserver(medir)
    ro.observe(caja.current)
    return () => ro.disconnect()
  }, [pasos.map((p) => p.estado).join()])

  return (
    <div className={`flujo ${trabajando ? 'trabajando' : 'quieto'}`} ref={caja}>
      <svg className="flujo-lineas" aria-hidden="true">
        {lineas.map((l) => (
          <g key={l.id} className={`linea ${l.activa ? 'activa' : ''}`}>
            <path d={l.d} />
            <polygon points={l.punta} />
          </g>
        ))}
      </svg>
      {pasos.map((p) => (
        <button key={p.id} ref={(el) => { nodos.current[p.id] = el }} className={`nodo ${p.estado} ${p.id === 'bandeja' || p.id === 'publicacion' ? 'ancho' : ''}`}
          style={{ gridArea: p.id }} onClick={() => alElegir(p.id)}
          aria-label={`${p.numero}. ${p.titulo}: ${ESTADOS[p.estado]}, ${p.corto}. Ver detalle`}>
          <span className="nodo-titulo"><span className="nodo-num">{p.numero}</span>{p.titulo}</span>
          <span className="nodo-dato">{p.corto}</span>
        </button>
      ))}
    </div>
  )
}
