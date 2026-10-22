import { fijarModo } from '../modo.js'
import { useState } from 'react'
import { api } from '../api.js'

export default function Login({ alEntrar }) {
  const [usuario, setUsuario] = useState('')
  const [password, setPassword] = useState('')
  const [ver, setVer] = useState(false)
  const [error, setError] = useState('')
  const [enviando, setEnviando] = useState(false)

  async function entrar(e) {
    e.preventDefault()
    if (!usuario.trim() || !password) {
      setError('Escribe tu usuario y tu contraseña.')
      return
    }
    setEnviando(true)
    setError('')
    try {
      const d = await api('/api/auth/login', { metodo: 'POST', datos: { usuario, password } })
      fijarModo(d.modo)
      alEntrar(d.usuario)
    } catch (err) {
      setError(err.message)
      setPassword('')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <main className="login">
      <div className="login-caja">
        <div className="sello" aria-hidden="true">†</div>
        <div className="etiqueta">Sistema del equipo</div>
        <h1 style={{ marginTop: 6 }}>Cristocéntricos</h1>
        <p className="muted" style={{ marginTop: 8 }}>Entra para preparar cada evento y descargar su material.</p>

        <form className="tarjeta" onSubmit={entrar} noValidate>
          <div className="campo">
            <label htmlFor="usuario">Usuario</label>
            <input id="usuario" autoComplete="username" autoCapitalize="none" spellCheck="false"
              maxLength={40} value={usuario} onChange={(e) => setUsuario(e.target.value)} />
          </div>
          <div className="campo">
            <label htmlFor="password">Contraseña</label>
            <div className="con-boton">
              <input id="password" type={ver ? 'text' : 'password'} autoComplete="current-password"
                maxLength={128} value={password} onChange={(e) => setPassword(e.target.value)} />
              <button type="button" onClick={() => setVer(!ver)} aria-pressed={ver}>{ver ? 'Ocultar' : 'Mostrar'}</button>
            </div>
          </div>
          <p className="error" role="alert" aria-live="polite">{error}</p>
          <button className="btn" type="submit" disabled={enviando}>{enviando ? 'Entrando…' : 'Entrar'}</button>
        </form>
      </div>
    </main>
  )
}
