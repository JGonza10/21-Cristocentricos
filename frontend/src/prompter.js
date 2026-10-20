// Lógica del prompter: convierte el guion (Markdown) en bloques y palabras, y decide hasta dónde
// avanzar según lo que el micrófono va escuchando. Sin React, para poder probarla sola.

/** «¡Jesús!» → «jesus». Minúsculas, sin acentos ni signos. */
export function normalizar(texto) {
  return texto.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9ñ\s]/g, ' ').trim()
}

/**
 * Bloques del guion. Tipos: titulo (#), indicacion (>) y texto (se lee en voz alta).
 * Solo las palabras de los bloques de texto cuentan para seguir la voz.
 */
export function prepararGuion(md) {
  const bloques = []
  const palabras = []
  for (const cruda of (md || '').split('\n')) {
    const linea = cruda.trim()
    if (!linea) continue
    if (linea.startsWith('#')) {
      bloques.push({ tipo: 'titulo', texto: linea.replace(/^#+\s*/, ''), nivel: linea.match(/^#+/)[0].length })
    } else if (linea.startsWith('>')) {
      bloques.push({ tipo: 'indicacion', texto: linea.replace(/^>\s*/, '') })
    } else {
      const b = bloques.length
      const tokens = linea.split(/\s+/).map((t) => {
        const norm = normalizar(t).replace(/\s+/g, '')
        const token = { texto: t, indice: norm ? palabras.length : -1 }
        if (norm) palabras.push({ norm, bloque: b })
        return token
      })
      bloques.push({ tipo: 'texto', tokens })
    }
  }
  return { bloques, palabras }
}

function distancia(a, b) {
  if (Math.abs(a.length - b.length) > 2) return 3
  const fila = Array.from({ length: b.length + 1 }, (_, i) => i)
  for (let i = 1; i <= a.length; i++) {
    let previo = fila[0]
    fila[0] = i
    for (let j = 1; j <= b.length; j++) {
      const guardado = fila[j]
      fila[j] = Math.min(fila[j] + 1, fila[j - 1] + 1, previo + (a[i - 1] === b[j - 1] ? 0 : 1))
      previo = guardado
    }
  }
  return fila[b.length]
}

/** El reconocimiento de voz se equivoca un poco: «confio» ≈ «confío», «jesus» ≈ «jesús». */
export function parecidas(a, b) {
  if (a === b) return true
  if (a.length < 4 || b.length < 4) return false
  return distancia(a, b) <= (Math.max(a.length, b.length) >= 7 ? 2 : 1)
}

export const COLA = 6        // últimas palabras escuchadas que se comparan
export const VENTANA = 45    // cuántas palabras hacia adelante se busca

/**
 * Devuelve la nueva posición (índice de la siguiente palabra por leer) o la misma si no hay
 * coincidencia segura. Solo avanza: los rezos repetidos no lo regresan.
 * Primero busca cerca (ventana); si no encuentra, busca en el resto con una regla más estricta.
 */
export function avanzar(palabras, posicion, oido, { cola = COLA, ventana = VENTANA } = {}) {
  const escuchadas = normalizar(oido).split(/\s+/).filter(Boolean).slice(-cola)
  if (escuchadas.length < 2) return posicion
  const cerca = buscar(palabras, escuchadas, posicion, posicion + ventana, Math.max(2, Math.ceil(escuchadas.length * 0.6)))
  if (cerca !== null) return cerca + 1
  // ¿Se saltaron una sección? Busca en todo lo que falta, pero solo con una coincidencia casi exacta.
  if (escuchadas.length < 5) return posicion
  const lejos = buscar(palabras, escuchadas, posicion + ventana + 1, palabras.length - 1, escuchadas.length - 1)
  return lejos !== null ? lejos + 1 : posicion
}

function buscar(palabras, escuchadas, desde, hasta, minimo) {
  let mejor = null
  for (let fin = Math.max(desde, 0); fin <= Math.min(hasta, palabras.length - 1); fin++) {
    // La última palabra oída debe coincidir: así no se adelanta por palabras sueltas.
    if (!parecidas(escuchadas.at(-1), palabras[fin].norm)) continue
    let aciertos = 0
    for (let k = 0; k < escuchadas.length; k++) {
      const j = fin - (escuchadas.length - 1 - k)
      if (j >= 0 && parecidas(escuchadas[k], palabras[j].norm)) aciertos++
    }
    if (aciertos >= minimo && (!mejor || aciertos > mejor.aciertos)) mejor = { fin, aciertos }
  }
  return mejor ? mejor.fin : null
}

/** Índice de la primera palabra del bloque de texto siguiente (o anterior) a la posición. */
export function saltarBloque(palabras, posicion, direccion) {
  if (!palabras.length) return 0
  const actual = palabras[Math.min(posicion, palabras.length - 1)].bloque
  if (direccion > 0) {
    const i = palabras.findIndex((p) => p.bloque > actual)
    return i === -1 ? palabras.length : i
  }
  const inicioActual = palabras.findIndex((p) => p.bloque === actual)
  const objetivo = posicion > inicioActual ? actual : (palabras[inicioActual - 1]?.bloque ?? actual)
  return palabras.findIndex((p) => p.bloque === objetivo)
}
