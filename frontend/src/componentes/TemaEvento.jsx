// Tema, guion e intenciones de un evento. Se llena desde el calendario (con anticipación) o desde Inicio.
// «Preparar guion con Claude» copia las instrucciones y abre Claude para pegarlas (sin API de pago).
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { fechaHora } from '../util.js'

const VACIO = { titulo: '', descripcion: '', cita: '', intenciones: '', guion: '', notas: '' }

export default function TemaEvento({ fecha, alGuardar }) {
  const [tema, setTema] = useState(undefined)   // undefined = cargando, null = sin tema
  const [form, setForm] = useState(VACIO)
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')

  useEffect(() => {
    setTema(undefined)
    setError('')
    setAviso('')
    api(`/api/temas/${fecha}`).then((d) => {
      setTema(d.tema)
      setForm(d.tema ? Object.fromEntries(Object.keys(VACIO).map((k) => [k, d.tema[k] ?? ''])) : VACIO)
    }).catch((e) => setError(e.message))
  }, [fecha])

  const campo = (k) => ({ value: form[k], onChange: (e) => setForm((f) => ({ ...f, [k]: e.target.value })) })
  const cambiado = tema === null ? form.titulo.trim() !== '' : tema && Object.keys(VACIO).some((k) => (tema[k] ?? '') !== form[k])

  async function guardar(e) {
    e?.preventDefault()
    setOcupado(true)
    setError('')
    try {
      const d = await api(`/api/temas/${fecha}`, { metodo: 'PUT', datos: form })
      setTema(d.tema)
      setAviso(d.tema.aviso_pendiente ? 'Tema guardado. El equipo recibirá el aviso por correo y en su calendario.' : 'Cambios guardados.')
      alGuardar?.(d.tema)
    } catch (err) {
      setError(err.message)
    } finally {
      setOcupado(false)
    }
  }

  async function prepararConClaude() {
    setError('')
    // La ventana se abre en el clic (si no, el navegador la bloquea); después se copian las instrucciones.
    const ventana = window.open('https://claude.ai/new', '_blank', 'noopener')
    try {
      if (cambiado) await guardar()
      const { texto } = await api(`/api/temas/${fecha}/instrucciones`)
      await navigator.clipboard.writeText(texto)
      setAviso(`Instrucciones copiadas${ventana ? ' y Claude abierto en otra pestaña' : ''}: pégalas con Ctrl+V. Cuando te dé el guion, pégalo aquí y guarda.`)
    } catch {
      setError('No se pudieron copiar las instrucciones. Intenta de nuevo.')
    }
  }

  async function difusion(otra = false) {
    setOcupado(true)
    setError('')
    try {
      const d = await api(`/api/temas/${fecha}/difusion`, { metodo: 'POST', datos: { otra } })
      setAviso(d.creados ? `Listo: ${d.creados} piezas de difusión en la bandeja (pestaña Contenido).`
        : 'La difusión de este evento ya existe. Usa «Hacer otra versión» si cambiaste el tema.')
      alGuardar?.(tema)
    } catch (err) {
      setError(err.message)
    } finally {
      setOcupado(false)
    }
  }

  if (tema === undefined && !error) return <p className="chico-texto">Cargando tema…</p>

  return (
    <form className="formulario tema-evento" onSubmit={guardar}>
      <div className="campo">
        <label htmlFor={`tema-${fecha}`}>Tema del evento</label>
        <input id={`tema-${fecha}`} maxLength={120} required placeholder="Ej. El perdón que libera" {...campo('titulo')} />
      </div>
      <div className="campo">
        <label htmlFor={`desc-${fecha}`}>De qué trata (1 o 2 frases para la difusión)</label>
        <input id={`desc-${fecha}`} maxLength={400} placeholder="Ej. Cómo perdonar de corazón y recuperar la paz" {...campo('descripcion')} />
      </div>
      <div className="campo">
        <label htmlFor={`cita-${fecha}`}>Cita bíblica (opcional)</label>
        <input id={`cita-${fecha}`} maxLength={200} placeholder="Ej. Perdona y serás perdonado (Lc 6,37)" {...campo('cita')} />
      </div>
      <div className="campo">
        <label htmlFor={`int-${fecha}`}>Intenciones recibidas</label>
        <textarea id={`int-${fecha}`} rows={3} maxLength={4000} placeholder="Una por renglón. Sin apellidos si no hay permiso." {...campo('intenciones')} />
      </div>
      <div className="campo">
        <label htmlFor={`guion-${fecha}`}>Guion</label>
        <textarea id={`guion-${fecha}`} rows={8} maxLength={20000} placeholder="Escríbelo aquí o pídele ayuda a Claude con el botón de abajo." {...campo('guion')} />
      </div>
      <div className="campo">
        <label htmlFor={`notas-${fecha}`}>Notas del equipo</label>
        <textarea id={`notas-${fecha}`} rows={2} maxLength={4000} {...campo('notas')} />
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {aviso && <p className="tema-aviso" role="status">{aviso}</p>}
      {tema?.aviso_error && <p className="chico-texto">Aviso al equipo: {tema.aviso_error}</p>}
      <div className="botones">
        <button className="btn chico" type="submit" disabled={ocupado || !cambiado}>Guardar tema</button>
        <button className="btn suave chico" type="button" disabled={ocupado || !form.titulo.trim()} onClick={prepararConClaude}>Preparar guion con Claude</button>
        {tema && <button className="btn suave chico" type="button" disabled={ocupado} onClick={() => difusion(false)}>Generar difusión ahora</button>}
        {tema && <button className="enlace" type="button" disabled={ocupado} onClick={() => difusion(true)}>Hacer otra versión</button>}
      </div>
      {tema && <p className="chico-texto">Guardado por {tema.actualizado_por ?? 'alguien del equipo'} el {fechaHora(tema.actualizado).replace(/\.$/, '')}.</p>}
    </form>
  )
}
