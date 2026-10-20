// Paso 2 «Agregar guion» (Gonza, 2026-10-20): ventana propia para escribir, pegar o cargar el guion desde un
// archivo (.docx, .pdf, .txt, .md; también arrastrándolo). El texto se revisa aquí y se guarda en el tema.
// «Preparar guion con Claude» copia las instrucciones y abre Claude (sin API de pago).
import { useEffect, useRef, useState } from 'react'
import { api, enviarCrudo } from '../api.js'

const CAMPOS = ['titulo', 'descripcion', 'cita', 'intenciones', 'guion', 'notas']
const ACEPTA = '.docx,.pdf,.txt,.md'

export default function GuionEvento({ fecha, alGuardar, alPedirTema }) {
  const [tema, setTema] = useState(undefined) // undefined = cargando, null = sin tema
  const [guion, setGuion] = useState('')
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState('')
  const [aviso, setAviso] = useState('')
  const [encima, setEncima] = useState(false)
  const archivo = useRef(null)

  useEffect(() => {
    setTema(undefined)
    setError('')
    setAviso('')
    api(`/api/temas/${fecha}`).then((d) => { setTema(d.tema); setGuion(d.tema?.guion ?? '') }).catch((e) => setError(e.message))
  }, [fecha])

  async function cargarArchivo(f) {
    if (!f) return
    setOcupado(true)
    setError('')
    setAviso('')
    try {
      const r = await enviarCrudo(`/api/temas/${fecha}/guion/archivo`, f,
        { 'Content-Type': 'application/octet-stream', 'X-Nombre': encodeURIComponent(f.name).slice(0, 200) })
      if (!r.ok) throw new Error(r.cuerpo.error || (r.status === 413 ? 'El archivo pesa más de 15 MB.' : 'No se pudo leer el archivo.'))
      setGuion(r.cuerpo.texto)
      setAviso(`Se cargó «${f.name}». Revísalo y pulsa «Guardar guion».`)
    } catch (e) {
      setError(e.message)
    } finally {
      setOcupado(false)
    }
  }

  async function guardar(e) {
    e?.preventDefault()
    setOcupado(true)
    setError('')
    try {
      const datos = Object.fromEntries(CAMPOS.map((k) => [k, tema?.[k] ?? '']))
      const d = await api(`/api/temas/${fecha}`, { metodo: 'PUT', datos: { ...datos, guion } })
      setTema(d.tema)
      setAviso('Guion guardado.')
      alGuardar?.(d.tema)
    } catch (err) {
      setError(err.message)
    } finally {
      setOcupado(false)
    }
  }

  async function prepararConClaude() {
    setError('')
    const ventana = window.open('https://claude.ai/new', '_blank', 'noopener') // en el clic, si no el navegador la bloquea
    try {
      const { texto } = await api(`/api/temas/${fecha}/instrucciones`)
      await navigator.clipboard.writeText(texto)
      setAviso(`Instrucciones copiadas${ventana ? ' y Claude abierto en otra pestaña' : ''}: pégalas con Ctrl+V. Cuando te dé el guion, pégalo aquí y guarda.`)
    } catch {
      setError('No se pudieron copiar las instrucciones. Intenta de nuevo.')
    }
  }

  if (tema === undefined && !error) return <p className="chico-texto">Cargando…</p>
  if (tema === null) {
    return (
      <div className="guion-sin-tema">
        <p>Este evento todavía no tiene tema. Primero ponle fecha y tema; después se agrega el guion.</p>
        {alPedirTema && <button className="btn chico" type="button" onClick={alPedirTema}>Poner tema</button>}
      </div>
    )
  }

  const cambiado = (tema?.guion ?? '') !== guion
  return (
    <form className="formulario guion-evento" onSubmit={guardar}>
      <p className="chico-texto">Tema: <b>{tema.titulo}</b></p>
      <div className={`guion-soltar ${encima ? 'encima' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setEncima(true) }}
        onDragLeave={() => setEncima(false)}
        onDrop={(e) => { e.preventDefault(); setEncima(false); cargarArchivo(e.dataTransfer.files?.[0]) }}>
        <div className="guion-opciones">
          <button className="btn chico" type="button" disabled={ocupado} onClick={() => archivo.current?.click()}>Cargar archivo</button>
          <button className="btn suave chico" type="button" disabled={ocupado} onClick={prepararConClaude}>Preparar guion con Claude</button>
          <span className="chico-texto">o arrastra aquí un .docx, .pdf o .txt</span>
          <input ref={archivo} type="file" accept={ACEPTA} hidden
            onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ''; cargarArchivo(f) }} />
        </div>
        <label htmlFor={`guion-${fecha}`} className="sr-solo">Guion</label>
        <textarea id={`guion-${fecha}`} rows={14} maxLength={20000} value={guion} onChange={(e) => setGuion(e.target.value)}
          placeholder="Escribe o pega el guion aquí, o cárgalo desde un archivo." />
        <p className="chico-texto contador">{guion.length.toLocaleString('es-MX')} / 20,000</p>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      {aviso && <p className="tema-aviso" role="status">{aviso}</p>}
      <div className="botones">
        <button className="btn" type="submit" disabled={ocupado || !cambiado || !guion.trim()}>Guardar guion</button>
      </div>
    </form>
  )
}
