// Tema claro/oscuro. Se recuerda en este navegador (si el navegador lo permite).
const CLAVE = 'cristo-tema'

export function temaGuardado() {
  try { return localStorage.getItem(CLAVE) } catch { return null }
}

export function aplicarTema(tema) {
  if (tema) document.documentElement.dataset.theme = tema
  else delete document.documentElement.dataset.theme
  try { tema ? localStorage.setItem(CLAVE, tema) : localStorage.removeItem(CLAVE) } catch { /* sin almacenamiento */ }
}

export function temaActual() {
  const t = document.documentElement.dataset.theme
  if (t) return t
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}
