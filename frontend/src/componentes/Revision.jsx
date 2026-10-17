// Revisión técnica del día del evento: Juan la palomea antes de transmitir.
import { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function Revision({ fecha, alCambiar }) {
  const [lista, setLista] = useState(null)
  const [sinTema, setSinTema] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api(`/api/temas/${fecha}`).then((d) => {
      setSinTema(!d.tema)
      setLista(d.tema?.checklist ?? null)
    }).catch((e) => setError(e.message))
  }, [fecha])

  async function marcar(id, hecho) {
    setError('')
    setLista((l) => l.map((x) => (x.id === id ? { ...x, hecho } : x)))
    try {
      const d = await api(`/api/temas/${fecha}/checklist`, { metodo: 'PUT', datos: { id, hecho } })
      setLista(d.tema.checklist)
      alCambiar?.()
    } catch (e) {
      setError(e.message)
    }
  }

  if (sinTema) return <p className="chico-texto">Primero guarda el tema del evento; la revisión se guarda con él.</p>
  if (!lista) return error ? <p className="error">{error}</p> : <p className="chico-texto">Cargando…</p>
  const hechos = lista.filter((x) => x.hecho).length
  return (
    <fieldset className="revision">
      <legend>Revisión técnica · {hechos} de {lista.length}</legend>
      {lista.map((x) => (
        <label key={x.id} className="casilla">
          <input type="checkbox" checked={x.hecho} onChange={(e) => marcar(x.id, e.target.checked)} /> {x.texto}
        </label>
      ))}
      {error && <p className="error" role="alert">{error}</p>}
    </fieldset>
  )
}
