// Cliente para hablar con Flask. Agrega el token CSRF en todo lo que no sea GET.
let csrf = null

async function obtenerCsrf() {
  const r = await fetch('/api/auth/csrf', { credentials: 'same-origin' })
  csrf = (await r.json()).csrf
  return csrf
}

export function olvidarCsrf() {
  csrf = null
}

export async function api(ruta, { metodo = 'GET', datos } = {}) {
  const opciones = { method: metodo, credentials: 'same-origin', headers: { Accept: 'application/json' } }
  if (metodo !== 'GET') {
    opciones.headers['Content-Type'] = 'application/json'
    opciones.headers['X-CSRFToken'] = csrf || (await obtenerCsrf())
    opciones.body = JSON.stringify(datos ?? {})
  }
  let r
  try {
    r = await fetch(ruta, opciones)
  } catch {
    throw Object.assign(new Error('No hay conexión con el servidor. ¿Está abierta la ventana del servidor?'), { status: 0 })
  }
  let cuerpo = {}
  try { cuerpo = await r.json() } catch { /* respuesta sin JSON */ }
  if (cuerpo.csrf) csrf = cuerpo.csrf
  if (!r.ok) {
    if (r.status === 400 && /sesión expiró/i.test(cuerpo.error || '')) csrf = null
    throw Object.assign(new Error(cuerpo.error || 'Algo salió mal. Intenta de nuevo.'), { status: r.status })
  }
  return cuerpo
}

/** POST con un cuerpo binario (video o audio) y cabeceras propias. Devuelve { ok, status, cuerpo }. */
export async function enviarCrudo(ruta, cuerpo, cabeceras = {}) {
  const headers = { ...cabeceras, 'X-CSRFToken': csrf || (await obtenerCsrf()) }
  let r
  try {
    r = await fetch(ruta, { method: 'POST', credentials: 'same-origin', headers, body: cuerpo })
  } catch {
    throw Object.assign(new Error('Se perdió la conexión con el servidor.'), { status: 0 })
  }
  let datos = {}
  try { datos = await r.json() } catch { /* sin JSON */ }
  return { ok: r.ok, status: r.status, cuerpo: datos }
}
