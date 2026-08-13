import { useEffect, useMemo, useRef } from 'react'
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'

/**
 * Mapa del canton de Tilaran con sus ocho distritos.
 *
 * Historia H5.1. Rubrica de Computacion Grafica, criterio CG-4.
 *
 * Dos decisiones que conviene no deshacer sin pensarlo:
 *
 * 1. El encuadre se calcula a partir de la geometria recibida, no se escribe a
 *    mano. Hoy las geometrias son cuadrados de marcador de posicion y en la
 *    historia H1.3 se reemplazan por los limites reales del SNIT. Si las
 *    coordenadas estuvieran fijas en el codigo, ese dia el mapa apuntaria al
 *    lugar equivocado y nadie sabria por que.
 *
 * 2. Todos los distritos se dibujan con la trama de ausencia de dato, porque
 *    todavia no hay modelo entrenado y ninguno tiene nivel de riesgo. Ese es el
 *    estado honesto. Pintarlos de un color de la rampa seria afirmar un riesgo
 *    que nadie calculo.
 */

// Centro provisional mientras se calcula el encuadre real. Solo se ve durante
// el primer cuadro de render: AjustarEncuadre lo reemplaza de inmediato.
const CENTRO_PROVISIONAL = [10.47, -84.97]
const ZOOM_PROVISIONAL = 11

/**
 * Ajusta la vista para que quepan todos los distritos, sea cual sea su
 * geometria. Es un componente y no una llamada suelta porque useMap solo existe
 * dentro del arbol de MapContainer.
 */
function AjustarEncuadre({ coleccion }) {
  const mapa = useMap()

  useEffect(() => {
    if (!coleccion) return
    const limites = L.geoJSON(coleccion).getBounds()
    if (limites.isValid()) {
      mapa.fitBounds(limites, { padding: [40, 40] })
    }
  }, [coleccion, mapa])

  return null
}

export default function MapaCanton({ coleccion, seleccionado, alSeleccionar }) {
  const capaRef = useRef(null)

  // La clave fuerza a react-leaflet a recrear la capa cuando cambia la
  // coleccion. Sin esto, GeoJSON conserva la geometria del primer render.
  const clave = useMemo(
    () => coleccion?.features?.map((r) => r.properties.codigo).join('-'),
    [coleccion],
  )

  const estilo = (rasgo) => ({
    className:
      rasgo.properties.codigo === seleccionado
        ? 'distrito distrito-sin-dato distrito-seleccionado'
        : 'distrito distrito-sin-dato',
  })

  const porCadaDistrito = (rasgo, capa) => {
    const { codigo, nombre } = rasgo.properties

    capa.bindTooltip(`${nombre} (${codigo})`, { sticky: true })

    capa.on('click', () => alSeleccionar(codigo))
    capa.on('keydown', (evento) => {
      if (evento.originalEvent.key === 'Enter' || evento.originalEvent.key === ' ') {
        evento.originalEvent.preventDefault()
        alSeleccionar(codigo)
      }
    })

    // Accesible por teclado. Un mapa que solo responde al mouse deja fuera a
    // quien navega con tabulador.
    const elemento = capa.getElement()
    if (elemento) {
      elemento.setAttribute('tabindex', '0')
      elemento.setAttribute('role', 'button')
      elemento.setAttribute('aria-label', `Distrito ${nombre}, codigo ${codigo}, sin estimacion`)
    }
  }

  return (
    <div className="contenedor-mapa">
      {/* Trama de ausencia de dato. Va en el documento para que los poligonos de
          Leaflet puedan referenciarla con fill: url(#patron-sin-dato). */}
      <svg width="0" height="0" aria-hidden="true" style={{ position: 'absolute' }}>
        <defs>
          <pattern
            id="patron-sin-dato"
            patternUnits="userSpaceOnUse"
            width="8"
            height="8"
            patternTransform="rotate(45)"
          >
            <rect width="8" height="8" style={{ fill: 'var(--sin-dato-fondo)', opacity: 0.55 }} />
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="8"
              style={{ stroke: 'var(--sin-dato-trama)', strokeWidth: 2 }}
            />
          </pattern>
        </defs>
      </svg>

      <MapContainer
        center={CENTRO_PROVISIONAL}
        zoom={ZOOM_PROVISIONAL}
        scrollWheelZoom
        className="mapa"
      >
        <TileLayer
          attribution='&copy; colaboradores de <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {coleccion && (
          <>
            <GeoJSON key={clave} ref={capaRef} data={coleccion} style={estilo} onEachFeature={porCadaDistrito} />
            <AjustarEncuadre coleccion={coleccion} />
          </>
        )}
      </MapContainer>
    </div>
  )
}
