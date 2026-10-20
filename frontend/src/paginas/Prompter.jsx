import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api.js'
import { avanzar, prepararGuion, saltarBloque } from '../prompter.js'

const Reconocimiento = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
const CLAVE_TAM = 'cristo-prompter-tam'
const RESALTE = 4 // palabras que se iluminan a partir de la posición actual

function leerTam() {
  try { return Number(localStorage.getItem(CLAVE_TAM)) || 44 } catch { return 44 }
}

const MENSAJES = {
  listo: 'Toca Escuchar y empieza a leer.',
  escuchando: 'Escuchando… el texto avanza con tu voz.',
  pausa: 'En pausa. Toca una palabra para moverte ahí.',
  'sin-soporte': 'Este navegador no reconoce la voz. Usa Chrome (Android) o Safari (iPad). Puedes avanzar con ◀ ▶.',
  'sin-permiso': 'No hay permiso para el micrófono. Actívalo en el candado de la barra de direcciones.',
  'sin-https': 'El micrófono solo funciona con https. Entra por la dirección de Tailscale.',
  error: 'Se perdió el micrófono un momento. Toca Escuchar otra vez.',
}

export default function Prompter({ fecha, salir }) {
  const [evento, setEvento] = useState(null)
  const [error, setError] = useState('')
  const [pos, setPos] = useState(0)
  const [estado, setEstado] = useState(() => (!Reconocimiento ? 'sin-soporte' : window.isSecureContext ? 'listo' : 'sin-https'))
  const [tam, setTam] = useState(leerTam)
  const [espejo, setEspejo] = useState(false)

  const caja = useRef(null)
  const rec = useRef(null)
  const escuchando = useRef(false)
  const posRef = useRef(0)
  const candado = useRef(null)

  useEffect(() => {
    api(`/api/eventos/${fecha}`).then((d) => setEvento(d.evento)).catch((e) => setError(e.message))
  }, [fecha])

  const { bloques, palabras } = useMemo(() => prepararGuion(evento?.guion_md), [evento])

  const mover = useCallback((nueva) => {
    const p = Math.max(0, Math.min(palabras.length, nueva))
    posRef.current = p
    setPos(p)
  }, [palabras.length])

  // Mantiene la palabra actual a un tercio de la pantalla.
  useEffect(() => {
    const el = caja.current?.querySelector(`[data-i="${Math.min(pos, palabras.length - 1)}"]`)
    if (el && caja.current) {
      caja.current.scrollTo({ top: el.offsetTop - caja.current.clientHeight * 0.33, behavior: 'smooth' })
    }
  }, [pos, palabras.length, tam])

  const soltarPantalla = useCallback(() => {
    candado.current?.release?.().catch(() => {})
    candado.current = null
  }, [])

  const pausar = useCallback(() => {
    escuchando.current = false
    try { rec.current?.stop() } catch { /* ya estaba detenido */ }
    soltarPantalla()
    setEstado((e) => (e === 'escuchando' ? 'pausa' : e))
  }, [soltarPantalla])

  const escuchar = useCallback(async () => {
    if (!Reconocimiento || !window.isSecureContext) return
    if (!rec.current) {
      const r = new Reconocimiento()
      r.lang = 'es-MX'
      r.continuous = true
      r.interimResults = true
      r.onresult = (e) => {
        const oido = Array.from(e.results).slice(-2).map((x) => x[0].transcript).join(' ')
        const nueva = avanzar(palabras, posRef.current, oido)
        if (nueva !== posRef.current) mover(nueva)
      }
      r.onerror = (e) => {
        if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
          escuchando.current = false
          setEstado('sin-permiso')
        }
      }
      // Chrome corta el reconocimiento tras un silencio: si no pausaste, se reinicia solo.
      r.onend = () => {
        if (!escuchando.current) return
        try { r.start() } catch { setEstado('error'); escuchando.current = false }
      }
      rec.current = r
    }
    escuchando.current = true
    try { rec.current.start() } catch { /* ya estaba escuchando */ }
    setEstado('escuchando')
    try { candado.current = await navigator.wakeLock?.request('screen') } catch { /* sin bloqueo de pantalla */ }
  }, [palabras, mover])

  // Al cambiar el guion se crea un reconocedor nuevo con las palabras correctas.
  useEffect(() => () => {
    escuchando.current = false
    try { rec.current?.abort() } catch { /* nada */ }
    rec.current = null
    soltarPantalla()
  }, [palabras, soltarPantalla])

  const alternar = useCallback(() => (escuchando.current ? pausar() : escuchar()), [pausar, escuchar])

  useEffect(() => {
    function tecla(e) {
      if (e.target.closest('input, textarea, select')) return
      if (e.key === ' ') { e.preventDefault(); alternar() }
      else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { e.preventDefault(); mover(saltarBloque(palabras, posRef.current, 1)) }
      else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { e.preventDefault(); mover(saltarBloque(palabras, posRef.current, -1)) }
      else if (e.key === 'Escape') salir()
    }
    window.addEventListener('keydown', tecla)
    return () => window.removeEventListener('keydown', tecla)
  }, [alternar, mover, palabras, salir])

  function cambiarTam(delta) {
    const t = Math.max(24, Math.min(96, tam + delta))
    setTam(t)
    try { localStorage.setItem(CLAVE_TAM, String(t)) } catch { /* sin almacenamiento */ }
  }

  if (error) return <div className="prompter"><p className="pr-aviso">{error}</p><button className="btn" onClick={salir}>Volver</button></div>
  if (!evento) return <div className="prompter"><p className="pr-aviso">Cargando guion…</p></div>

  const avance = palabras.length ? Math.round((pos / palabras.length) * 100) : 0
  const activo = estado === 'escuchando'

  return (
    <div className="prompter">
      <div className="pr-barra">
        <button className="pr-btn" onClick={() => { pausar(); salir() }} aria-label="Salir del prompter">✕</button>
        <div className="pr-titulo">
          <b>{evento.tema || 'Guion'}</b>
          <span className={`pr-estado ${activo ? 'vivo' : ''}`} aria-live="polite">{MENSAJES[estado]}</span>
        </div>
        <div className="pr-grupo">
          <button className="pr-btn" onClick={() => cambiarTam(-4)} aria-label="Letra más chica">A−</button>
          <button className="pr-btn" onClick={() => cambiarTam(4)} aria-label="Letra más grande">A+</button>
          <button className="pr-btn" aria-pressed={espejo} onClick={() => setEspejo(!espejo)} aria-label="Modo espejo">⇋</button>
        </div>
      </div>
      <div className="pr-progreso" aria-hidden="true"><span style={{ width: `${avance}%` }} /></div>

      {palabras.length === 0 ? (
        <p className="pr-aviso">Este evento todavía no tiene guion. Cárgalo en el paso 1.</p>
      ) : (
        <div ref={caja} className={`pr-texto ${espejo ? 'espejo' : ''}`} style={{ fontSize: `${tam}px` }}>
          <div className="pr-guia" aria-hidden="true" />
          {bloques.map((b, bi) => {
            if (b.tipo === 'titulo') return <h2 key={bi} className="pr-seccion">{b.texto}</h2>
            if (b.tipo === 'indicacion') return <p key={bi} className="pr-cue">{b.texto}</p>
            return (
              <p key={bi}>
                {b.tokens.map((t, ti) => {
                  const i = t.indice
                  const clase = i < 0 ? '' : i < pos ? 'leido' : i < pos + RESALTE ? 'actual' : ''
                  return (
                    <span key={ti}>
                      <span data-i={i >= 0 ? i : undefined} className={clase}
                        onClick={i >= 0 ? () => mover(i) : undefined}>{t.texto}</span>{' '}
                    </span>
                  )
                })}
              </p>
            )
          })}
          <p className="pr-fin">— Fin del guion —</p>
        </div>
      )}

      <div className="pr-controles">
        <button className="pr-btn grande" onClick={() => mover(saltarBloque(palabras, pos, -1))} aria-label="Párrafo anterior">◀</button>
        <button className={`pr-play ${activo ? 'pausa' : ''}`} onClick={alternar}
          disabled={estado === 'sin-soporte' || estado === 'sin-https'}>
          {activo ? 'Pausa' : 'Escuchar'}
        </button>
        <button className="pr-btn grande" onClick={() => mover(saltarBloque(palabras, pos, 1))} aria-label="Párrafo siguiente">▶</button>
      </div>
    </div>
  )
}
