/**
 * El dibujo de la serie. Historia H7.2.
 *
 * POR QUE ESTA SEPARADO DE `GraficaSerie.jsx`
 *
 * **Este es el unico archivo del visor que importa `recharts`**, y por eso es el
 * unico que se carga tarde.
 *
 * Medido construyendo las dos versiones:
 *
 *     sin la grafica      324,87 kB   (gzip 101,07 kB)
 *     con la grafica      710,33 kB   (gzip 203,13 kB)
 *
 * O sea que la libreria **mas que duplica** el paquete inicial. Sin separarla,
 * ese peso lo descarga todo el mundo al abrir el visor, aunque nunca haga clic en
 * un distrito —y el mapa es lo primero y a veces lo unico que se mira.
 *
 * Con el corte, `recharts` viaja en un fragmento aparte que el navegador pide
 * **cuando se abre la ficha de un distrito**, que es el momento en que la grafica
 * de verdad hace falta.
 *
 * SOBRE LA PROPIEDAD DE ESTE ARCHIVO
 *
 * `frontend/` es de Avril. H7.2 paso a Alejandro por **D-33**. Declarado en
 * `docs/07-propiedad-archivos.md`.
 */

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

/** Etiqueta corta para el eje: `2026-08-16` -> `16 ago`. */
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

function etiquetaFecha(fecha) {
  const [, mes, dia] = fecha.split('-')
  return `${Number(dia)} ${MESES[Number(mes) - 1]}`
}

/**
 * Globo del punto bajo el cursor.
 *
 * Un dia sin medir dice **«sin dato»**, no cero y no vacio. Es la misma regla que
 * `PanelDistrito` aplica con la poblacion: lo que no se sabe se dice.
 */
function Globo({ active, payload, unidad }) {
  if (!active || !payload?.length) return null
  const punto = payload[0]
  const valor = punto.value
  return (
    <div className="gs-globo">
      <strong>{punto.payload.fecha}</strong>
      <span>
        {valor === null || valor === undefined ? 'sin dato' : `${valor} ${unidad}`}
      </span>
    </div>
  )
}

export default function GraficaSerieLienzo({ filas, unidad }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={filas} margin={{ top: 8, right: 12, bottom: 4, left: -12 }}>
        <CartesianGrid stroke="var(--borde)" strokeDasharray="2 4" vertical={false} />
        <XAxis
          dataKey="fecha"
          tickFormatter={etiquetaFecha}
          minTickGap={36}
          tick={{ fontSize: 11, fill: 'var(--texto-tenue)' }}
          stroke="var(--borde-fuerte)"
        />
        <YAxis
          tick={{ fontSize: 11, fill: 'var(--texto-tenue)' }}
          stroke="var(--borde-fuerte)"
          width={48}
        />
        <Tooltip content={<Globo unidad={unidad} />} />
        {/* `connectNulls={false}` ES EL CRITERIO DE ACEPTACION, no un detalle de
            estilo. Un dia sin medir deja la linea CORTADA. Unirla por encima
            afirmaria una medicion que nadie tomo, y el simulado trae un hueco
            cada veinte dias justamente para que esto se pueda comprobar.
            Ver CA-3 en frontend/herramientas/verificar_h72.mjs. */}
        <Line
          type="monotone"
          dataKey="valor"
          stroke="var(--simulado-acento)"
          strokeWidth={1.8}
          dot={false}
          connectNulls={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
