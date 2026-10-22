// Cambiar la contraseña: obligatorio al entrar con una contraseña temporal; también desde Configuración.
import { useState } from 'react'
import { api } from '../api.js'

export default function CambiarPassword({ alCambiar }) {
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [repetir, setRepetir] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const [listo, setListo] = useState(false)

  async function enviar(e) {
    e.preventDefault()
    setError('')
    setListo(false)
    if (nueva !== repetir) {
      setError('La contraseña nueva y su confirmación no coinciden.')
      return
    }
    setOcupado(true)
    try {
      const d = await api('/api/auth/cambiar-password', { metodo: 'POST', datos: { actual, nueva } })
      setActual('')
      setNueva('')
      setRepetir('')
      setListo(true)
      alCambiar?.(d.usuario)
    } catch (err) {
      setError(err.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <form className="formulario" onSubmit={enviar}>
      <div className="campo">
        <label htmlFor="pw-actual">Contraseña actual</label>
        <input id="pw-actual" type="password" autoComplete="current-password" required value={actual}
          onChange={(e) => setActual(e.target.value)} />
      </div>
      <div className="campo">
        <label htmlFor="pw-nueva">Contraseña nueva</label>
        <input id="pw-nueva" type="password" autoComplete="new-password" required minLength={10} value={nueva}
          onChange={(e) => setNueva(e.target.value)} aria-describedby="pw-regla" />
        <span id="pw-regla" className="chico-texto">Al menos 10 caracteres, con letras y números o símbolos.</span>
      </div>
      <div className="campo">
        <label htmlFor="pw-repetir">Repite la contraseña nueva</label>
        <input id="pw-repetir" type="password" autoComplete="new-password" required value={repetir}
          onChange={(e) => setRepetir(e.target.value)} />
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {listo && <p className="tema-aviso" role="status">Contraseña cambiada.</p>}
      <div className="botones">
        <button className="btn" type="submit" disabled={ocupado}>Cambiar contraseña</button>
      </div>
    </form>
  )
}
