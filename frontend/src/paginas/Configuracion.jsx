export default function Configuracion({ usuario }) {
  return (
    <>
      <section className="tarjeta">
        <span className="etiqueta">Tu cuenta</span>
        <dl className="dl">
          <dt>Nombre</dt><dd>{usuario.nombre}</dd>
          <dt>Usuario</dt><dd>{usuario.usuario}</dd>
        </dl>
        <p className="chico-texto" style={{ marginTop: 14 }}>
          Para cambiar tu contraseña, en la PC del sistema ejecuta: <code>flask --app app cambiar-password {usuario.usuario}</code>
        </p>
      </section>
      <section className="tarjeta">
        <span className="etiqueta">Seguridad</span>
        <ul className="lista">
          <li className="item"><div><b>Sesión cifrada</b><span className="muted">Se cierra sola a las 8 horas.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Bloqueo por intentos</b><span className="muted">15 minutos tras 5 intentos fallidos.</span></div><span className="pill verde">activo</span></li>
          <li className="item"><div><b>Acceso remoto por Tailscale</b><span className="muted">Solo la PC del aprobador puede entrar desde fuera.</span></div><span className="pill gris">según .env</span></li>
        </ul>
      </section>
    </>
  )
}
