// Ventana emergente con <dialog> nativo: mientras está abierta el foco se queda adentro (el resto de la
// página queda inerte), Escape la cierra y al cerrarse el foco regresa a donde estaba antes de abrirla.
import { useEffect, useRef } from 'react'

export default function Modal({ abierto, titulo, alCerrar, ancho = 'normal', children }) {
  const ref = useRef(null)
  const anterior = useRef(null)

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (abierto && !d.open) {
      anterior.current = document.activeElement
      d.showModal()
      document.body.classList.add('con-modal')
    } else if (!abierto && d.open) {
      d.close()
    }
  }, [abierto])

  function alCerrarse() {
    document.body.classList.remove('con-modal')
    const previo = anterior.current
    anterior.current = null
    if (previo && document.contains(previo)) previo.focus()
    if (abierto) alCerrar()
  }

  // Clic en el fondo oscuro (fuera del contenido) también cierra.
  function clicFondo(e) {
    if (e.target === ref.current) ref.current.close()
  }

  return (
    <dialog ref={ref} className={`modal modal-${ancho}`} aria-labelledby="modal-titulo" onClose={alCerrarse} onClick={clicFondo}>
      {abierto && (
        <div className="modal-caja">
          <header className="modal-cabeza">
            <h2 id="modal-titulo">{titulo}</h2>
            <button className="btn suave chico" onClick={() => ref.current.close()} aria-label="Cerrar ventana">Cerrar</button>
          </header>
          <div className="modal-cuerpo">{children}</div>
        </div>
      )}
    </dialog>
  )
}
