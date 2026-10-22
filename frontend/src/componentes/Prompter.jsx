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

  // Karaoke (Gonza, 2026-10-20): cada palabra que llega a un tercio de la pantalla (punto de lectura,
  // sin línea visible desde el 2026-10-21) se pinta de oro;
  // la línea que se está leyendo se resalta más. Se calcula con la posición real de cada palabra,
  // así funciona igual al cambiar el tamaño de letra, en espejo o moviendo el texto a mano.
  useEffect(() => {
    const el = caja.current
    if (!el) return undefined
    const palabras = [...el.querySelectorAll('.pp')]
    let leidas = -1
    let renglon = null
    function marcar() {
      const lectura = el.scrollTop + el.clientHeight * 0.33
      let lo = 0
      let hi = palabras.length - 1
      let n = -1
      while (lo <= hi) {             // última palabra cuyo centro ya pasó la línea de lectura
        const m = (lo + hi) >> 1
        const w = palabras[m]
        if (w.offsetTop + w.offsetHeight / 2 <= lectura) { n = m; lo = m + 1 } else hi = m - 1
      }
      if (n !== leidas) {
        const [a, b] = n > leidas ? [leidas + 1, n] : [n + 1, leidas]
        for (let i = a; i <= b; i++) palabras[i]?.classList.toggle('leida', i <= n)
        leidas = n
      }
      const top = n >= 0 ? palabras[n].offsetTop : null
      if (top !== renglon) {
        palabras.forEach((w) => w.classList.toggle('actual', top !== null && w.offsetTop === top))
        renglon = top
      }
    }
    marcar()
    el.addEventListener('scroll', marcar, { passive: true })
    window.addEventListener('resize', marcar)
    return () => { el.removeEventListener('scroll', marcar); window.removeEventListener('resize', marcar) }
  }, [texto, tamano])

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
        <div ref={caja} className={`prompter-texto ${espejo ? 'espejo' : ''}`} style={{ fontSize: `${tamano}px` }} tabIndex={0}>
          <div className="prompter-relleno" />
          {texto.split(/\n{2,}/).map((parrafo, i) => (
            <p key={i}>{parrafo.split(/(\s+)/).map((t, j) => (/^\s+$/.test(t) || !t ? t : <span key={j} className="pp">{t}</span>))}</p>
          ))}
          <div className="prompter-relleno" />
        </div>
      </div>
    </div>
  )
}
