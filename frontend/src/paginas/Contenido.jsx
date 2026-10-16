const PASOS = [
  { fase: 2, titulo: 'Bandeja de aprobación', texto: 'Ver, aprobar, rechazar y editar el texto de cada paquete.' },
  { fase: 3, titulo: 'Carruseles', texto: '5 imágenes blanco y vino por rosario, listas 2 días antes.' },
  { fase: 4, titulo: 'Reels', texto: '3 videos verticales con subtítulos de cada transmisión.' },
  { fase: 5, titulo: 'Publicación', texto: 'Carpeta por red social y subida directa a YouTube.' },
]

export default function Contenido() {
  return (
    <>
      <section className="tarjeta">
        <span className="etiqueta">Bandeja</span>
        <p className="vacio">No hay paquetes por revisar. Aquí aparecerán los carruseles y reels que preparen los agentes.</p>
      </section>
      <section className="tarjeta">
        <span className="etiqueta">Lo que viene en esta sección</span>
        <ul className="lista">
          {PASOS.map((p) => (
            <li key={p.fase} className="item">
              <div><b>{p.titulo}<span className="pill">fase {p.fase}</span></b><span className="muted">{p.texto}</span></div>
            </li>
          ))}
        </ul>
      </section>
    </>
  )
}
