// Paso 3 «Crear imágenes» (Gonza, 2026-10-20): las 5 imágenes de difusión del tema para redes sociales.
// Salen solas al guardar el tema; aquí se crean al momento o se rehacen («Otra versión») si cambió el tema.
import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function CrearImagenes({ fecha, listo, alCrear, alVerMaterial }) {
  const [tema, setTema] = useState(undefined)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    api(`/api/temas/${fecha}`).then((d) => setTema(d.tema)).catch((e) => setError(e.message))
  }, [fecha])

  async function crear(otra) {
    setOcupado(true)
    setError('')
    setAviso('')
    try {
      const d = await api(`/api/temas/${fecha}/difusion`, { metodo: 'POST', datos: { otra } })
      setAviso(d.creados ? 'Listo: las 5 imágenes están en Material.' : 'Las imágenes de este evento ya existen. Usa «Otra versión» si cambiaste el tema.')
      alCrear?.()
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
    }
  }

  if (tema === undefined && !error) return <p className="chico-texto">Cargando…</p>
  if (!tema) return <p>Este evento todavía no tiene tema: primero ponle fecha y tema.</p>
  return (
    <div className="crear-imagenes">
      <p>Se arman <b>5 imágenes para redes sociales</b> con el tema <b>«{tema.titulo}»</b>
        {tema.descripcion ? <>, su descripción</> : null}{tema.cita ? <> y la cita bíblica</> : null}. Quedan en Material para descargarlas y subirlas.</p>
      {listo && !aviso && <p className="tema-aviso">Las imágenes de este evento ya están listas.</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {aviso && <p className="tema-aviso" role="status">{aviso}</p>}
      <div className="botones">
        {!listo && <button className="btn" disabled={ocupado} onClick={() => crear(false)}>{ocupado ? 'Creando…' : 'Crear imágenes'}</button>}
        {listo && <button className="btn suave chico" disabled={ocupado} onClick={() => crear(true)}>Otra versión</button>}
        <button className="btn suave chico" onClick={alVerMaterial}>Ver en Material</button>
      </div>
    </div>
  )
}
