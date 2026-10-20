import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { avanzar, normalizar, parecidas, prepararGuion, saltarBloque } from '../prompter.js'

const GUION = `# No tengas miedo

## Gancho

¿Sientes que vives con miedo? ¿Con incertidumbre y miedo al futuro?

> Pausa y mira a la cámara.

Sagrado Corazón de Jesús, en ti confío.

Sagrado Corazón de Jesús, en ti confío.

Yo soy Esbeidy, y esto fue Cristocéntricos.`

const { bloques, palabras } = prepararGuion(GUION)
const posDe = (texto, desde = 0) => {
  const objetivo = normalizar(texto).split(' ')
  for (let i = desde; i < palabras.length; i++) {
    if (objetivo.every((w, k) => palabras[i + k]?.norm === w)) return i
  }
  return -1
}

describe('prepararGuion', () => {
  it('separa títulos, indicaciones y texto', () => {
    assert.deepEqual(bloques.map((b) => b.tipo), ['titulo', 'titulo', 'texto', 'indicacion', 'texto', 'texto', 'texto'])
  })
  it('las indicaciones no cuentan como palabras por leer', () => {
    assert.equal(palabras.some((p) => p.norm === 'pausa'), false)
  })
})

describe('avanzar', () => {
  it('sigue la lectura aunque falten acentos', () => {
    const p = avanzar(palabras, 0, 'sientes que vives con miedo')
    assert.equal(p, posDe('miedo') + 1)
  })
  it('tolera palabras mal oídas', () => {
    const p = avanzar(palabras, 0, 'sientes que vive con mido')
    assert.equal(p, posDe('miedo') + 1)
  })
  it('no se mueve con pocas palabras o con ruido', () => {
    assert.equal(avanzar(palabras, 0, 'miedo'), 0)
    assert.equal(avanzar(palabras, 0, 'buenos días a todos los que nos ven'), 0)
  })
  it('en frases repetidas avanza a la más cercana y nunca regresa', () => {
    const primera = posDe('sagrado corazon')
    const segunda = posDe('sagrado corazon', primera + 1)
    const p1 = avanzar(palabras, primera, 'sagrado corazón de jesús en ti confío')
    assert.equal(p1, primera + 7)
    const p2 = avanzar(palabras, p1, 'sagrado corazón de jesús en ti confío')
    assert.equal(p2, segunda + 7)
    assert.equal(avanzar(palabras, p2, 'sientes que vives con miedo'), p2)
  })
  it('si se saltan una sección larga, la encuentra con una frase casi exacta', () => {
    const largo = prepararGuion(`${'Texto de relleno número uno dos tres. '.repeat(20)}\n\nYo soy Esbeidy y esto fue Cristocéntricos.`)
    const fin = largo.palabras.length
    assert.equal(avanzar(largo.palabras, 0, 'yo soy esbeidy y esto fue cristocéntricos'), fin)
    assert.equal(avanzar(largo.palabras, 0, 'esto fue cristocéntricos'), 0)
  })
  it('se puede saltar lo improvisado: encuentra el siguiente texto', () => {
    const p = avanzar(palabras, posDe('miedo al futuro') + 3, 'yo soy esbeidy y esto fue')
    assert.equal(p, posDe('fue') + 1)
  })
})

describe('utilidades', () => {
  it('parecidas', () => {
    assert.equal(parecidas('confio', 'confio'), true)
    assert.equal(parecidas('incertidumbre', 'incertidumbres'), true)
    assert.equal(parecidas('en', 'el'), false)
  })
  it('saltarBloque va al inicio del bloque siguiente y del anterior', () => {
    const inicio2 = posDe('sagrado corazon')
    assert.equal(saltarBloque(palabras, 2, 1), inicio2)
    assert.equal(saltarBloque(palabras, inicio2 + 3, -1), inicio2)
    assert.equal(saltarBloque(palabras, inicio2, -1), 0)
  })
})
