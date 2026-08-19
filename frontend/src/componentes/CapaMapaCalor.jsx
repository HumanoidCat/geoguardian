import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import { dibujarSuperficie, puntosDeOrigen } from '../datos/interpolacion'

/**
 * Superficie de probabilidad interpolada por distancia inversa, mas los puntos
 * de origen sobre los que se calculo.
 *
 * Historia H5.4. Rubrica de Computacion Grafica, criterio CG-1.
 *
 * Los puntos se dibujan encima de la superficie a proposito, y no es decoracion:
 * una interpolacion sobre ocho puntos produce una superficie suave que parece un
 * analisis fino y no lo es. Mostrar de donde salio cada valor es lo que impide
 * leerla como si fuera una medicion continua del terreno.
 *
 * La superficie se calcula en una cuadricula fija y se coloca como imagen
 * superpuesta. No se recalcula al hacer zoom: la interpolacion no gana
 * informacion por acercarse, y recalcularla daria la impresion contraria.
 */

// Resolucion de la cuadricula de calculo. 180 x 180 sobre un canton de 669 km2
// da celdas de unos 150 m, mas fino de lo que ocho puntos pueden justificar.
// Subirla no agrega informacion, solo suaviza el dibujo.
const RESOLUCION = 180

// Opacidad de la superficie. Mas alta tapa el terreno; mas baja hace que la
// rampa deje de distinguirse, el mismo problema que el deslizador de H5.2.
const OPACIDAD_SUPERFICIE = 0.7

export default function CapaMapaCalor({ centroides, riesgos, exponente }) {
  const mapa = useMap()

  useEffect(() => {
    const puntos = puntosDeOrigen(centroides ?? [], riesgos)
    if (puntos.length === 0) return undefined

    const latitudes = puntos.map((punto) => punto.lat)
    const longitudes = puntos.map((punto) => punto.lon)

    // Se extiende el area mas alla de los puntos para que la superficie no
    // termine en un borde recto justo sobre el ultimo distrito.
    const margen = 0.03
    const limites = {
      norte: Math.max(...latitudes) + margen,
      sur: Math.min(...latitudes) - margen,
      este: Math.max(...longitudes) + margen,
      oeste: Math.min(...longitudes) - margen,
    }

    const lienzo = dibujarSuperficie({
      puntos,
      limites,
      ancho: RESOLUCION,
      alto: RESOLUCION,
      exponente,
      opacidad: OPACIDAD_SUPERFICIE,
    })
    if (!lienzo) return undefined

    const grupo = L.layerGroup().addTo(mapa)

    L.imageOverlay(
      lienzo.toDataURL(),
      [
        [limites.sur, limites.oeste],
        [limites.norte, limites.este],
      ],
      { interactive: false, className: 'superficie-calor' },
    ).addTo(grupo)

    // Los puntos de origen, encima de la superficie.
    for (const punto of puntos) {
      L.circleMarker([punto.lat, punto.lon], {
        radius: 4,
        className: 'punto-origen',
        interactive: true,
      })
        .bindTooltip(`${punto.nombre}: probabilidad ${Math.round(punto.valor * 100)} %`, {
          direction: 'top',
        })
        .addTo(grupo)
    }

    return () => {
      grupo.remove()
    }
  }, [centroides, riesgos, exponente, mapa])

  return null
}
