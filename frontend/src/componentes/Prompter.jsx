// Prompter (Gonza, 2026-10-20): el guion a pantalla completa, con letra grande que sube sola.
// Espacio = iniciar/pausar · ↑/↓ = velocidad · +/- = tamaño · Inicio = volver arriba. Espejo para teleprompter físico.
import { useEffect, useRef, useState } from 'react'

const CLAVE = 'cristo-prompter'

function ajustesGuardados() {
  try { return { velocidad: 3, tamano: 54, espejo: false, ...JSON.parse(localStorage.getItem(CLAVE) || '{}') } } catch { return { velocidad: 3, tamano: 54, espejo: false } }
}

export default function Prompter({ texto }) {
  const [ajustes, setAjustes] = useState(ajustesGuardados)
  const [corriendo, setCorriendo] = useState(false)
  const caja = useRef(null)
  const { velocidad, tamano, espejo } = ajustes

  function cambiar(cambio) {
    setAjustes((a) => {
      const n = { ...a, ...cambio }
      try { localStorage.setItem(CLAVE, JSON.stringify(n)) } catch { /* sin almacenamiento */ }
      return n
    })
  }
  const vel = (d) => cambiar({ velocidad: Math.min(10, Math.max(1, velocidad + d)) })
  const tam = (d) => cambiar({ tamano: Math.min(110, Math.max(28, tamano + d)) })
  const arriba = () => { if (caja.current) caja.current.scrollTop = 0 }

  // Desplazamiento suave: velocidad 1 = 18 px/s … 10 = 180 px/s
  useEffect(() => {
    if (!corriendo) return undefined
    let id = 0
    let antes = null
    let resto = 0
    const paso = (t) => {
      const el = caja.current
      if (el) {
        if (antes !== null) {
          resto += ((t - antes) / 1000) * velocidad * 18
          const px = Math.floor(resto)
          resto -= px
          el.scrollTop += px
          if (el.scrollTop + el.clientHeight >= el.scrollHeight - 1) { setCorriendo(false); return }
        }
        antes = t
      }
      id = requestAnimationFrame(paso)
    }
    id = requestAnimationFrame(paso)
    return () => cancelAnimationFrame(id)
  }, [corriendo, velocidad])

  useEffect(() => {
    function tecla(e) {
      if (e.target.closest?.('input, textarea, select')) return
      if (e.key === ' ') { e.preventDefault(); setCorriendo((c) => !c) }
      else if (e.key === 'ArrowUp') { e.preventDefault(); vel(1) }
      else if (e.key === 'ArrowDown') { e.preventDefault(); vel(-1) }
      else if (e.key === '+' || e.key === '=') tam(4)
      else if (e.key === '-') tam(-4)
      else if (e.key === 'Home') arriba()
    }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  })

  return (
    <div className="prompter">
      <div className="prompter-mandos" role="toolbar" aria-label="Controles del prompter">
        <button className="btn chico" onClick={() => setCorriendo((c) => !c)}>{corriendo ? '❚❚ Pausa' : '▶ Iniciar'}</button>
        <button className="btn suave chico" onClick={arriba}>Al inicio</button>
        <span className="prompter-grupo">Velocidad
          <button className="btn suave chico" onClick={() => vel(-1)} aria-label="Más lento">−</button>
          <b className="prompter-valor">{velocidad}</b>
          <button className="btn suave chico" onClick={() => vel(1)} aria-label="Más rápido">+</button>
        </span>
        <span className="prompter-grupo">Letra
          <button className="btn suave chico" onClick={() => tam(-4)} aria-label="Letra más chica">A−</button>
          <button className="btn suave chico" onClick={() => tam(4)} aria-label="Letra más grande">A+</button>
        </span>
        <button className="btn suave chico" aria-pressed={espejo} onClick={() => cambiar({ espejo: !espejo })}>Espejo</button>
        <span className="chico-texto prompter-ayuda">Espacio: iniciar/pausar · ↑↓ velocidad · +/− letra</span>
      </div>
      <div className="prompter-pantalla">
        <div className="prompter-guia" aria-hidden="true" />
        <div ref={caja} className={`prompter-texto ${espejo ? 'espejo' : ''}`} style={{ fontSize: `${tamano}px` }} tabIndex={0}>
          <div className="prompter-relleno" />
          {texto.split(/\n{2,}/).map((parrafo, i) => <p key={i}>{parrafo}</p>)}
          <div className="prompter-relleno" />
        </div>
      </div>
    </div>
  )
}
