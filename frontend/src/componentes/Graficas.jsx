// Gráficas interactivas en SVG, sin librerías: toman los colores del tema (claro/oscuro) por CSS,
// muestran el detalle al pasar el mouse o tocar, y la leyenda prende y apaga cada serie.
import { useEffect, useId, useRef, useState } from 'react'

const H = 240
const M = { arriba: 14, derecha: 12, abajo: 34, izquierda: 38 }
const ALTO = H - M.arriba - M.abajo

/** Ancho real del contenedor: la gráfica se dibuja a esa medida para que los textos no se encojan en el celular. */
function useAncho() {
  const [el, setEl] = useState(null)       // ref de callback: funciona aunque el lienzo aparezca después
  const [w, setW] = useState(640)
  useEffect(() => {
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))))
    ro.observe(el)
    return () => ro.disconnect()
  }, [el])
  return [setEl, w]
}

/** Escala "bonita" del eje Y: máximo redondeado y 4 marcas. */
function escala(max) {
  if (max <= 0) return { tope: 4, marcas: [0, 1, 2, 3, 4] }
  const paso = Math.pow(10, Math.floor(Math.log10(max / 4)))
  const opciones = [1, 2, 2.5, 5, 10].map((k) => k * paso)
  const p = opciones.find((o) => o * 4 >= max) ?? opciones.at(-1)
  const tope = p * 4
  return { tope, marcas: [0, 1, 2, 3, 4].map((k) => +(k * p).toFixed(2)) }
}

/** Degradado vertical por serie: del color principal (arriba) a su segundo tono (abajo). */
function Degradados({ id, series, area = false }) {
  return (
    <defs>
      {series.map((s) => (
        <linearGradient key={s.clave} id={`${id}-${s.clave}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" style={{ stopColor: s.color, stopOpacity: area ? 0.35 : 1 }} />
          <stop offset="100%" style={{ stopColor: s.color2 ?? s.color, stopOpacity: area ? 0 : 0.85 }} />
        </linearGradient>
      ))}
    </defs>
  )
}
const relleno = (id, s) => `url(#${CSS.escape(id)}-${s.clave})`

const fmt = (n) => (Number.isInteger(n) ? n.toLocaleString('es-MX') : n.toLocaleString('es-MX', { maximumFractionDigits: 1 }))

function Leyenda({ series, apagadas, alternar }) {
  if (series.length < 2) return null
  return (
    <div className="g-leyenda" role="group" aria-label="Series de la gráfica">
      {series.map((s) => (
        <button key={s.clave} type="button" aria-pressed={!apagadas.has(s.clave)} onClick={() => alternar(s.clave)}
          title={apagadas.has(s.clave) ? 'Mostrar' : 'Ocultar'}>
          <span className="g-punto" style={{ background: `linear-gradient(135deg, ${s.color}, ${s.color2 ?? s.color})` }} />{s.nombre}
        </button>
      ))}
    </div>
  )
}

function useSeries() {
  const [apagadas, setApagadas] = useState(new Set())
  const alternar = (clave) => setApagadas((a) => {
    const n = new Set(a)
    if (n.has(clave)) n.delete(clave)
    else n.add(clave)
    return n
  })
  return [apagadas, alternar]
}

function Tooltip({ info }) {
  if (!info) return null
  return (
    <div className="g-tooltip" style={{ left: `${info.x}%`, top: `${info.y}%` }} role="status">
      {info.titulo && <b>{info.titulo}</b>}
      {info.lineas.map((l) => (
        <span key={l.nombre}>{l.color && <span className="g-punto" style={{ background: l.color }} />}{l.nombre}: <b>{l.valor}</b></span>
      ))}
    </div>
  )
}

function Ejes({ marcas, tope, etiquetas, W }) {
  const cada = Math.max(1, Math.ceil(etiquetas.length / Math.max(3, Math.floor(W / 64))))
  return (
    <>
      {marcas.map((m) => {
        const y = M.arriba + ALTO - (m / tope) * ALTO
        return (
          <g key={m}>
            <line x1={M.izquierda} x2={W - M.derecha} y1={y} y2={y} className="g-rejilla" />
            <text x={M.izquierda - 6} y={y + 4} className="g-eje" textAnchor="end">{fmt(m)}</text>
          </g>
        )
      })}
      {etiquetas.map((e, i) => ((i % cada === 0 && (i === etiquetas.length - 1 || etiquetas.length - 1 - i >= cada)) || i === etiquetas.length - 1) && (
        <text key={i} x={e.x} y={H - 12} className="g-eje" textAnchor="middle">{e.texto}</text>
      ))}
    </>
  )
}

/**
 * Barras por categoría (apiladas o lado a lado).
 * datos: [{...}], series: [{clave, nombre, color}], etiqueta(d) → texto corto del eje X,
 * titulo(d) → título del tooltip, alElegir(d) al hacer clic, elegido: índice resaltado.
 */
export function Barras({ datos, series, etiqueta, titulo, apilar = true, alElegir, elegido, sufijo = '' }) {
  const id = useId()
  const [apagadas, alternar] = useSeries()
  const [info, setInfo] = useState(null)
  const [caja, W] = useAncho()
  const ANCHO = W - M.izquierda - M.derecha
  const visibles = series.filter((s) => !apagadas.has(s.clave))
  if (!datos.length) return <p className="vacio">No hay datos en este periodo.</p>
  const valor = (d, s) => (typeof s.valor === 'function' ? s.valor(d) : d[s.clave]) || 0
  const max = Math.max(0, ...datos.map((d) => (apilar
    ? visibles.reduce((t, s) => t + valor(d, s), 0)
    : Math.max(0, ...visibles.map((s) => valor(d, s))))))
  const { tope, marcas } = escala(max)
  const banda = ANCHO / datos.length
  const anchoBarra = Math.max(2, Math.min(42, banda * 0.7))
  const y = (v) => (v / tope) * ALTO

  function mostrar(d, i) {
    setInfo({
      x: ((M.izquierda + banda * (i + 0.5)) / W) * 100,
      y: 4,
      titulo: titulo ? titulo(d) : etiqueta(d),
      lineas: visibles.map((s) => ({ nombre: s.nombre, valor: `${fmt(valor(d, s))}${sufijo}`, color: s.color })),
    })
  }

  return (
    <div className="g-caja">
      <Leyenda series={series} apagadas={apagadas} alternar={alternar} />
      <div className="g-lienzo" ref={caja} onMouseLeave={() => setInfo(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Gráfica de barras">
          <Degradados id={id} series={series} />
          <Ejes W={W} marcas={marcas} tope={tope}
            etiquetas={datos.map((d, i) => ({ x: M.izquierda + banda * (i + 0.5), texto: etiqueta(d) }))} />
          {datos.map((d, i) => {
            const x0 = M.izquierda + banda * i + (banda - anchoBarra) / 2
            let base = M.arriba + ALTO
            const sub = anchoBarra / Math.max(1, visibles.length)
            return (
              <g key={i} className={`g-grupo ${elegido === i ? 'elegido' : ''}`}
                onMouseEnter={() => mostrar(d, i)} onFocus={() => mostrar(d, i)} onBlur={() => setInfo(null)}
                onClick={() => { mostrar(d, i); alElegir?.(d, i) }}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); alElegir?.(d, i) } }}
                tabIndex={0} role="button" aria-label={`${titulo ? titulo(d) : etiqueta(d)}: ${visibles.map((s) => `${s.nombre} ${valor(d, s)}`).join(', ')}`}>
                <rect x={M.izquierda + banda * i} y={M.arriba} width={banda} height={ALTO} className="g-zona" />
                {visibles.map((s, k) => {
                  const h = y(valor(d, s))
                  if (apilar) {
                    base -= h
                    return <rect key={s.clave} x={x0} y={base} width={anchoBarra} height={h} rx={h > 6 ? 6 : 0} className="g-barra" style={{ fill: relleno(id, s) }} />
                  }
                  return <rect key={s.clave} x={x0 + sub * k} y={M.arriba + ALTO - h} width={Math.max(1, sub - 1)} height={h} rx={h > 4 ? 4 : 0} className="g-barra" style={{ fill: relleno(id, s) }} />
                })}
              </g>
            )
          })}
        </svg>
        <Tooltip info={info} />
      </div>
    </div>
  )
}

/** Líneas en el tiempo. series: [{clave, nombre, color, puntos: [{fecha:'AAAA-MM-DD', y}]}] */
export function Lineas({ series, desde, hasta, etiquetaFecha }) {
  const id = useId()
  const [apagadas, alternar] = useSeries()
  const [info, setInfo] = useState(null)
  const ref = useRef(null)
  const [caja, W] = useAncho()
  const ANCHO = W - M.izquierda - M.derecha
  const visibles = series.filter((s) => !apagadas.has(s.clave) && s.puntos.length)
  if (!series.some((s) => s.puntos.length)) return <p className="vacio">No hay datos en este periodo.</p>
  const t0 = Date.parse(desde)
  const t1 = Math.max(Date.parse(hasta), t0 + 86400000)
  const x = (f) => M.izquierda + ((Date.parse(f) - t0) / (t1 - t0)) * ANCHO
  const { tope, marcas } = escala(Math.max(0, ...visibles.flatMap((s) => s.puntos.map((p) => p.y))))
  const y = (v) => M.arriba + ALTO - (v / tope) * ALTO
  const etiquetas = [0, 0.25, 0.5, 0.75, 1].map((k) => {
    const f = new Date(t0 + k * (t1 - t0)).toISOString().slice(0, 10)
    return { x: M.izquierda + k * ANCHO, texto: etiquetaFecha(f) }
  })

  function mover(e) {
    const caja = ref.current?.getBoundingClientRect()
    if (!caja) return
    const px = ((e.clientX - caja.left) / caja.width) * W
    const t = t0 + ((px - M.izquierda) / ANCHO) * (t1 - t0)
    const lineas = visibles.map((s) => {
      const p = s.puntos.reduce((a, b) => (Math.abs(Date.parse(b.fecha) - t) < Math.abs(Date.parse(a.fecha) - t) ? b : a))
      return { nombre: s.nombre, valor: `${fmt(p.y)} (${etiquetaFecha(p.fecha)})`, color: s.color, fecha: p.fecha }
    })
    if (!lineas.length) return
    setInfo({ x: Math.min(85, Math.max(5, (px / W) * 100)), y: 4, titulo: null, lineas, guia: px })
  }

  return (
    <div className="g-caja">
      <Leyenda series={series} apagadas={apagadas} alternar={alternar} />
      <div className="g-lienzo" ref={caja} onMouseLeave={() => setInfo(null)}>
        <svg viewBox={`0 0 ${W} ${H}`} ref={ref} onMouseMove={mover} onTouchStart={(e) => mover(e.touches[0])}
          role="img" aria-label="Gráfica de líneas">
          <Degradados id={id} series={series} area />
          <Ejes W={W} marcas={marcas} tope={tope} etiquetas={etiquetas} />
          {info && <line x1={info.guia} x2={info.guia} y1={M.arriba} y2={M.arriba + ALTO} className="g-guia" />}
          {visibles.map((s) => (
            <g key={s.clave}>
              {s.puntos.length > 1 && (
                <polygon className="g-area" style={{ fill: relleno(id, s) }} points={[
                  `${x(s.puntos[0].fecha)},${M.arriba + ALTO}`,
                  ...s.puntos.map((p) => `${x(p.fecha)},${y(p.y)}`),
                  `${x(s.puntos.at(-1).fecha)},${M.arriba + ALTO}`,
                ].join(' ')} />
              )}
              <polyline points={s.puntos.map((p) => `${x(p.fecha)},${y(p.y)}`).join(' ')} className="g-linea" style={{ stroke: s.color }} />
              {s.puntos.map((p) => <circle key={p.fecha} cx={x(p.fecha)} cy={y(p.y)} r={4.5} className="g-nodo" style={{ stroke: s.color }} />)}
            </g>
          ))}
        </svg>
        <Tooltip info={info} />
      </div>
    </div>
  )
}

/** Dona con porcentaje. partes: [{clave, nombre, valor, color}] */
export function Dona({ partes, alElegir, elegida }) {
  const [sobre, setSobre] = useState(null)
  const total = partes.reduce((t, p) => t + p.valor, 0)
  if (!total) return <p className="vacio">No hay piezas en este periodo.</p>
  const R = 70
  const C = 2 * Math.PI * R
  let acumulado = 0
  const activa = partes.find((p) => p.clave === (sobre ?? elegida))
  return (
    <div className="g-dona">
      <svg viewBox="0 0 200 200" role="img" aria-label="Gráfica de dona">
        <circle cx="100" cy="100" r={R} className="g-dona-fondo" />
        {partes.map((p) => {
          const largo = (p.valor / total) * C
          const el = (
            <circle key={p.clave} cx="100" cy="100" r={R} className={`g-dona-parte ${activa?.clave === p.clave ? 'activa' : ''}`}
              style={{ stroke: p.color, strokeDasharray: `${largo} ${C - largo}`, strokeDashoffset: -acumulado }}
              onMouseEnter={() => setSobre(p.clave)} onMouseLeave={() => setSobre(null)}
              onClick={() => alElegir?.(p.clave === elegida ? null : p.clave)} />
          )
          acumulado += largo
          return el
        })}
        <text x="100" y="96" textAnchor="middle" className="g-dona-num">{fmt(activa ? activa.valor : total)}</text>
        <text x="100" y="118" textAnchor="middle" className="g-eje">{activa ? `${Math.round((activa.valor / total) * 100)}% ${activa.nombre.toLowerCase()}` : 'piezas'}</text>
      </svg>
      <ul className="g-dona-lista">
        {partes.map((p) => (
          <li key={p.clave}>
            <button type="button" aria-pressed={elegida === p.clave} onMouseEnter={() => setSobre(p.clave)} onMouseLeave={() => setSobre(null)}
              onClick={() => alElegir?.(p.clave === elegida ? null : p.clave)}>
              <span className="g-punto" style={{ background: p.color }} />{p.nombre}<b>{fmt(p.valor)}</b>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

/** Barras horizontales de porcentaje. filas: [{clave, nombre, hecho, omitido, de}] */
export function Porcentajes({ filas }) {
  const [sobre, setSobre] = useState(null)
  if (!filas.length || !filas[0].de) return <p className="vacio">Todavía no hay eventos trabajados en este periodo.</p>
  return (
    <ul className="g-porcentajes">
      {filas.map((f) => {
        const ph = Math.round((f.hecho / f.de) * 100)
        const po = Math.round((f.omitido / f.de) * 100)
        return (
          <li key={f.clave} onMouseEnter={() => setSobre(f.clave)} onMouseLeave={() => setSobre(null)}
            className={sobre === f.clave ? 'sobre' : ''}>
            <span className="g-p-nombre">{f.nombre}</span>
            <span className="g-p-pista" role="img" aria-label={`${f.nombre}: ${ph}% hecho, ${po}% omitido`}>
              <span className="g-p-hecho" style={{ width: `${ph}%` }} />
              <span className="g-p-omitido" style={{ width: `${po}%` }} />
            </span>
            <span className="g-p-num">{sobre === f.clave ? `${f.hecho} de ${f.de}` : `${ph}%`}</span>
          </li>
        )
      })}
    </ul>
  )
}
