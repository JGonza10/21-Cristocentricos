// Ideas del equipo: escritas o por voz. El audio lo pasa a texto Whisper en la computadora de la app.
// Cualquier idea se puede volver el tema (o una nota) de un evento.
import { useEffect, useRef, useState } from 'react'
import { api, enviarCrudo } from '../api.js'
import { proximoEvento, claveFecha, esDiaDeEvento, nombreFecha } from '../evento.js'
import { fechaDeClave, fechaHora } from '../util.js'
import { enNube } from '../modo.js'

const DIA_MS = 24 * 60 * 60 * 1000

function proximasFechas(n = 8) {
  const primero = proximoEvento()
  if (!primero) return []
  const lista = []
  let d = fechaDeClave(primero.clave)
  while (lista.length < n) {
    if (esDiaDeEvento(d)) lista.push(claveFecha(d))
    d = new Date(d.getTime() + DIA_MS)
  }
  return lista
}

export default function Ideas({ alCambiar }) {
  const [ideas, setIdeas] = useState(null)
  const [texto, setTexto] = useState('')
  const [grabando, setGrabando] = useState(false)
  const [segundos, setSegundos] = useState(0)
  const [error, setError] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const grabadora = useRef(null)
  const reloj = useRef(null)

  const pendientes = useRef(false)
  const cargar = () => api('/api/ideas').then((d) => {
    setIdeas(d.ideas)
    pendientes.current = d.ideas.some((i) => i.estado === 'transcribiendo')
  }).catch((e) => setError(e.message))
  useEffect(() => {
    cargar()
    const t = setInterval(() => { if (pendientes.current) cargar() }, 8000)   // mientras Whisper transcribe
    return () => { clearInterval(t); detenerTodo() }
  }, [])

  function detenerTodo() {
    clearInterval(reloj.current)
    grabadora.current?.stream.getTracks().forEach((t) => t.stop())
  }

  async function guardarTexto(e) {
    e.preventDefault()
    setOcupado(true)
    setError('')
    try {
      await api('/api/ideas', { metodo: 'POST', datos: { texto } })
      setTexto('')
      await cargar()
      alCambiar?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setOcupado(false)
    }
  }

  async function empezarAudio() {
    setError('')
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError('Este navegador no permite grabar audio. Usa Chrome o Edge.')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const tipo = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'].find((t) => MediaRecorder.isTypeSupported(t)) || ''
      const rec = new MediaRecorder(stream, tipo ? { mimeType: tipo } : undefined)
      const trozos = []
      rec.ondataavailable = (e) => e.data.size && trozos.push(e.data)
      rec.onstop = async () => {
        detenerTodo()
        setGrabando(false)
        const blob = new Blob(trozos, { type: rec.mimeType || 'audio/webm' })
        setOcupado(true)
        try {
          const r = await enviarCrudo('/api/ideas/audio', blob, { 'Content-Type': blob.type })
          if (!r.ok) throw new Error(r.cuerpo.error || 'No se pudo guardar el audio.')
          await cargar()
          alCambiar?.()
        } catch (err) {
          setError(err.message)
        } finally {
          setOcupado(false)
        }
      }
      grabadora.current = rec
      rec.start()
      setSegundos(0)
      setGrabando(true)
      reloj.current = setInterval(() => setSegundos((s) => {
        if (s + 1 >= 600) rec.stop()          // máximo 10 minutos por idea
        return s + 1
      }), 1000)
    } catch {
      setError('No se pudo usar el micrófono. Revisa que el navegador tenga permiso.')
    }
  }

  return (
    <div className="ideas">
      <form className="formulario" onSubmit={guardarTexto}>
        <div className="campo">
          <label htmlFor="idea-texto">Escribe una idea</label>
          <textarea id="idea-texto" rows={3} maxLength={4000} value={texto} onChange={(e) => setTexto(e.target.value)}
            placeholder="Un tema, una frase para un reel, un invitado, algo que mejorar…" />
        </div>
        <div className="botones">
          <button className="btn chico" type="submit" disabled={ocupado || !texto.trim()}>Guardar idea</button>
          {enNube() ? null : grabando
            ? <button className="btn chico grabando" type="button" onClick={() => grabadora.current.stop()}>
              ■ Detener · {Math.floor(segundos / 60)}:{String(segundos % 60).padStart(2, '0')}</button>
            : <button className="btn suave chico" type="button" disabled={ocupado} onClick={empezarAudio}>● Grabar idea por voz</button>}
        </div>
        {error && <p className="error" role="alert">{error}</p>}
      </form>

      {ideas === null && !error && <p className="chico-texto">Cargando ideas…</p>}
      {ideas?.length === 0 && <p className="vacio">Todavía no hay ideas. La primera puede ser por voz.</p>}
      {ideas?.length > 0 && (
        <ul className="ideas-lista">
          {ideas.map((i) => <IdeaFila key={i.id} idea={i} alCambiar={() => { cargar(); alCambiar?.() }} />)}
        </ul>
      )}
    </div>
  )
}

function IdeaFila({ idea, alCambiar }) {
  const [fecha, setFecha] = useState('')
  const [error, setError] = useState('')
  const fechas = proximasFechas()

  async function usar() {
    setError('')
    try {
      await api(`/api/ideas/${idea.id}/usar`, { metodo: 'POST', datos: { fecha } })
      alCambiar()
    } catch (e) {
      setError(e.message)
    }
  }

  async function borrar() {
    if (!window.confirm('¿Borrar esta idea?')) return
    try {
      await api(`/api/ideas/${idea.id}`, { metodo: 'DELETE' })
      alCambiar()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <li className={`idea e-${idea.estado}`}>
      <div className="idea-cabeza">
        <span className="chico-texto">{idea.autor ?? 'Equipo'} · {fechaHora(idea.creado)}{idea.audio ? ' · por voz' : ''}</span>
        {idea.estado === 'usada' && <span className="pill verde">Usada: {nombreFecha(fechaDeClave(idea.fecha_evento))}</span>}
        {idea.estado === 'transcribiendo' && <span className="pill ambar">Pasando a texto…</span>}
        {idea.estado === 'error' && <span className="pill roja">No se entendió el audio</span>}
      </div>
      {idea.texto && <p className="idea-texto">{idea.texto}</p>}
      {idea.audio && !enNube() && <audio controls preload="none" src={`/api/ideas/${idea.id}/audio`} />}
      <div className="botones">
        {idea.texto && idea.estado !== 'usada' && (
          <>
            <select aria-label="Evento" value={fecha} onChange={(e) => setFecha(e.target.value)}>
              <option value="">Usar en el evento…</option>
              {fechas.map((f) => <option key={f} value={f}>{nombreFecha(fechaDeClave(f))}</option>)}
            </select>
            <button className="btn suave chico" disabled={!fecha} onClick={usar}>Usar como tema</button>
          </>
        )}
        <button className="enlace" onClick={borrar}>Borrar</button>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
    </li>
  )
}
