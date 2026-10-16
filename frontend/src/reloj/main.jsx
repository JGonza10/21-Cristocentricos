// Overlay del reloj para la transmisión (OBS / ventana compartida en StreamYard).
// Página pública SIN datos privados: no llama a la API, todo se calcula en el navegador.
//   /reloj?canal=Cristocéntricos  (solo tema perla, a pedido de Gonza)
import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { cuenta, estadoReloj, horaCDMX } from './tiempo.js'
import './reloj.css'

const params = new URLSearchParams(window.location.search)
const canal = (params.get('canal') || 'Cristocéntricos').slice(0, 40)
document.documentElement.dataset.overlay = 'perla'

function Overlay() {
  const [ahora, setAhora] = useState(() => new Date())
  useEffect(() => {
    const t = setInterval(() => setAhora(new Date()), 250)
    return () => clearInterval(t)
  }, [])
  const e = estadoReloj(ahora)

  return (
    <main className="panel">
      <div className="cabeza"><span className="cruz">†</span> {canal}</div>
      {e.modo === 'vivo' && <div className="vivo"><span className="punto" /> EN VIVO · {e.rosario.misterios}</div>}
      {e.modo === 'antes' && <div className="eyebrow">Santo Rosario · {e.rosario.misterios}</div>}
      <div className="hora">{horaCDMX(ahora)}</div>
      <div className="sub">Hora de la Ciudad de México</div>
      {e.modo === 'antes' && (
        <div className="cuenta">
          <span>Comenzamos en</span>
          <b>{cuenta(e.faltan)}</b>
          <small>{e.rosario.nombre} · 10:00 am</small>
        </div>
      )}
      {e.modo === 'vivo' && <div className="cuenta"><span>Termina en</span><b>{cuenta(e.restante)}</b></div>}
    </main>
  )
}

createRoot(document.getElementById('reloj')).render(<React.StrictMode><Overlay /></React.StrictMode>)
