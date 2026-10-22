// Subir el video limpio del celular desde cualquier computadora del equipo (por partes; se reanuda si se corta).
import { useRef, useState } from 'react'
import { enviarCrudo } from '../api.js'

const PARTE = 8 * 1024 * 1024

export function SubirGrabacion({ fecha, alTerminar }) {
  const [archivo, setArchivo] = useState(null)
  const [avance, setAvance] = useState(null)
  const [error, setError] = useState('')
  const [listo, setListo] = useState('')
  const cancelar = useRef(false)

  async function subir(e) {
    e.preventDefault()
    if (!archivo) return
    setError('')
    setListo('')
    cancelar.current = false
    let inicio = 0
    let fallos = 0
    const cab = { 'X-Archivo': encodeURIComponent(archivo.name), 'X-Total': String(archivo.size), 'X-Fecha': fecha,
      'Content-Type': 'application/octet-stream' }
    setAvance(0)
    while (inicio < archivo.size) {
      if (cancelar.current) { setAvance(null); setError('Subida cancelada.'); return }
      try {
        const r = await enviarCrudo('/api/grabaciones/subir', archivo.slice(inicio, inicio + PARTE), { ...cab, 'X-Inicio': String(inicio) })
        if (r.status === 409 && typeof r.cuerpo.recibido === 'number') { inicio = r.cuerpo.recibido; continue }
        if (!r.ok) { setAvance(null); setError(r.cuerpo.error || 'No se pudo subir el video.'); return }
        inicio = r.cuerpo.recibido
        fallos = 0
        setAvance(inicio / archivo.size)
        if (r.cuerpo.listo) {
          setListo(`Listo: ${r.cuerpo.nombre} ya está en la carpeta de grabaciones. El agente de reels lo procesa en unos minutos.`)
          setAvance(null)
          setArchivo(null)
          alTerminar?.()
          return
        }
      } catch {
        fallos += 1                       // se cortó el internet: espera y reanuda donde se quedó
        if (fallos > 20) { setAvance(null); setError('Se perdió la conexión. Vuelve a intentarlo; continúa donde se quedó.'); return }
        await new Promise((ok) => setTimeout(ok, 3000))
      }
    }
  }

  return (
    <form className="formulario subir" onSubmit={subir}>
      <div className="campo">
        <label htmlFor="subir-video">Video del evento (.mp4, .mkv, .mov, .webm)</label>
        <input id="subir-video" type="file" accept=".mp4,.mkv,.mov,.webm,.flv,video/*" disabled={avance !== null}
          onChange={(e) => setArchivo(e.target.files[0] ?? null)} />
      </div>
      {avance !== null && (
        <div className="avance-barra" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(avance * 100)}>
          <div className="avance-pista"><span style={{ width: `${avance * 100}%` }} /></div>
          <b>{Math.round(avance * 100)}%</b>
        </div>
      )}
      {error && <p className="error" role="alert">{error}</p>}
      {listo && <p className="tema-aviso" role="status">{listo}</p>}
      <div className="botones">
        <button className="btn chico" type="submit" disabled={!archivo || avance !== null}>Subir grabación</button>
        {avance !== null && <button className="btn suave chico" type="button" onClick={() => { cancelar.current = true }}>Cancelar</button>}
      </div>
      <p className="chico-texto">Se guarda en la computadora donde corre la app y cuenta para el evento seleccionado. Si se corta el internet, sigue sola donde se quedó.</p>
    </form>
  )
}
