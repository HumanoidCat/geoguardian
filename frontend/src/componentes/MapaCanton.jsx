import { useEffect, useMemo } from 'react'
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'

/**
 * Mapa del canton de Tilaran con sus ocho distritos, coloreados por nivel de
 * riesgo del evento seleccionado.
 *
 * Historias H5.1 y H5.3. Rubrica de Computacion Grafica, criterios CG-4 y CG-1.
 *
 * Tres decisiones que conviene no deshacer sin pensarlo:
 *
 * 1. El encuadre se calcula a partir de la geometria recibida, no se escribe a
 *    mano. Hoy las geometrias son cuadrados de marcador de posicion y en la
 *    historia H1.3 se reemplazan por los limites reales del SNIT. Si las
 *    coordenadas estuvieran fijas en el codigo, ese dia el mapa apuntaria al
 *    lugar equivocado y nadie sabria por que.
 *
 * 2. El relleno se resuelve por clase de CSS y no por opciones de Leaflet. Un
 *    color plano cabe en una opcion; una trama diagonal no. Como la ausencia de
 *    dato se representa con trama, los dos casos tienen que resolverse por el
 *    mismo camino o el codigo se parte en dos.
 *
 * 3. Un distrito sin nivel NO se pinta con el color mas claro de la rampa. Va
 *    con la trama de ausencia de dato. La diferencia entre "riesgo bajo" y
 *    "nadie lo midio" es la que evita que el mapa afirme lo que no sabe.
 */

// Centro provisional mientras se calcula el encuadre real. Solo se ve durante
// el primer cuadro de render: AjustarEncuadre lo reemplaza de inmediato.
const CENTRO_PROVISIONAL = [10.47, -84.97]
const ZOOM_PROVISIONAL = 11

const CLASE_POR_NIVEL = {
  bajo: 'distrito-riesgo-bajo',
  medio: 'distrito-riesgo-medio',
  alto: 'distrito-riesgo-alto',
}

const NOMBRE_POR_NIVEL = {
  bajo: 'riesgo bajo',
  medio: 'riesgo medio',
  alto: 'riesgo alto',
}

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
    if (!limites.isValid()) return

    const ajustar = () => {
      mapa.invalidateSize()
      mapa.fitBounds(limites, { padding: [32, 32] })
    }

    // El contenedor del mapa todavia esta creciendo cuando este efecto corre.
    // Leaflet mide el tamano que hay en ese instante, y si es mas chico que el
    // final elige un zoom demasiado abierto: se ve medio pais en lugar del
    // canton. Esperar un cuadro de render no alcanza, porque el alto lo termina
    // de resolver la rejilla de CSS despues.
    //
    // ResizeObserver avisa cada vez que el contenedor cambia de tamano de
    // verdad, incluida esa ultima vez. Tambien cubre el cambio de tamano de la
    // ventana. No entra en bucle: invalidateSize no altera el tamano del
    // contenedor, solo hace que Leaflet lo relea.
    const observador = new ResizeObserver(ajustar)
    observador.observe(mapa.getContainer())

    return () => observador.disconnect()
  }, [coleccion, mapa])

  return null
}

export default function MapaCanton({ coleccion, riesgos, evento, seleccionado, alSeleccionar }) {
  // La clave fuerza a react-leaflet a recrear la capa cuando cambia el evento o
  // la seleccion. Sin esto, GeoJSON conserva los estilos del primer render y el
  // mapa no cambia de color al cambiar de evento.
  const clave = useMemo(
    () => `${evento}-${seleccionado ?? 'ninguno'}-${coleccion?.features?.length ?? 0}`,
    [evento, seleccionado, coleccion],
  )

  const nivelDe = (codigo) => riesgos?.[codigo]?.nivel ?? null

  const estilo = (rasgo) => {
    const { codigo } = rasgo.properties
    const nivel = nivelDe(codigo)
    const clases = ['distrito', nivel ? CLASE_POR_NIVEL[nivel] : 'distrito-sin-dato']
    if (codigo === seleccionado) clases.push('distrito-seleccionado')
    return { className: clases.join(' ') }
  }

  const porCadaDistrito = (rasgo, capa) => {
    const { codigo, nombre } = rasgo.properties
    const nivel = nivelDe(codigo)
    const descripcion = nivel ? NOMBRE_POR_NIVEL[nivel] : 'sin estimacion'

    capa.bindTooltip(`${nombre} (${codigo}) · ${descripcion}`, { sticky: true })

    capa.on('click', () => alSeleccionar(codigo))
    capa.on('keydown', (evt) => {
      if (evt.originalEvent.key === 'Enter' || evt.originalEvent.key === ' ') {
        evt.originalEvent.preventDefault()
        alSeleccionar(codigo)
      }
    })

    // Accesible por teclado. Un mapa que solo responde al mouse deja fuera a
    // quien navega con tabulador. La etiqueta dice el nivel en palabras: el
    // color no llega a un lector de pantalla.
    const elemento = capa.getElement()
    if (elemento) {
      elemento.setAttribute('tabindex', '0')
      elemento.setAttribute('role', 'button')
      elemento.setAttribute('aria-label', `Distrito ${nombre}, codigo ${codigo}, ${descripcion}`)
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
            <GeoJSON key={clave} data={coleccion} style={estilo} onEachFeature={porCadaDistrito} />
            <AjustarEncuadre coleccion={coleccion} />
          </>
        )}
      </MapContainer>
    </div>
  )
}
