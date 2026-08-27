/**
 * Un punto representativo de cada distrito, para poder decir donde esta.
 *
 * Historia H5.6.
 *
 * ---------------------------------------------------------------------------
 * POR QUE NO SE USA EL CENTROIDE
 * ---------------------------------------------------------------------------
 *
 * **El centroide de area de un poligono concavo puede caer fuera del poligono**,
 * y aca eso no es una curiosidad geometrica: la coordenada existe para que
 * alguien la pase por radio. Mandar a una cuadrilla al distrito vecino es el
 * peor defecto posible en esta pantalla.
 *
 * Medido sobre las geometrias reales del SNIT, antes de escribir esto:
 *
 *     distrito          centroide de area            dentro del poligono
 *     Tilaran           -84.907579, 10.482454        NO
 *     los otros siete                                si
 *
 * **Uno de ocho.** No es un caso teorico ni un borde raro: es el distrito
 * cabecera del canton.
 *
 * ---------------------------------------------------------------------------
 * QUE SE USA EN SU LUGAR
 * ---------------------------------------------------------------------------
 *
 * Un **punto sobre la superficie**, garantizado dentro. Es lo mismo que hace
 * `ST_PointOnSurface` de PostGIS y por la misma razon.
 *
 * El metodo: se corta el poligono con la horizontal que pasa por la latitud del
 * centroide, se ordenan los cortes, y se toma el punto medio del **tramo
 * interior mas largo**. El tramo mas largo y no el primero: en un poligono con
 * una entrante estrecha, el primer tramo puede ser un hilo de pocos metros y el
 * punto quedaria pegado al borde.
 *
 * Se comprueba en `verificar_proyeccion.py` que los ocho caen dentro, con el
 * mismo algoritmo de punto en poligono que se usa aca.
 */

/** Los anillos exteriores, tanto de un Polygon como de un MultiPolygon. */
function anillosExteriores(geometria) {
  if (!geometria) return []
  if (geometria.type === 'Polygon') return [geometria.coordinates[0]]
  if (geometria.type === 'MultiPolygon') return geometria.coordinates.map((p) => p[0])
  return []
}

/** Centroide de area. Solo se usa para elegir la latitud del barrido. */
function centroideDeArea(anillos) {
  let sx = 0
  let sy = 0
  let area = 0

  for (const anillo of anillos) {
    for (let i = 0; i < anillo.length - 1; i += 1) {
      const [x0, y0] = anillo[i]
      const [x1, y1] = anillo[i + 1]
      const cruz = x0 * y1 - x1 * y0
      area += cruz / 2
      sx += ((x0 + x1) * cruz) / 6
      sy += ((y0 + y1) * cruz) / 6
    }
  }

  if (area === 0) return null
  return [sx / area, sy / area]
}

/**
 * Punto dentro del poligono, o `null` si la geometria no permite calcularlo.
 *
 * Devolver null y no una aproximacion es deliberado: si no se puede garantizar
 * que el punto esta dentro, **no hay coordenada que mostrar**. Un punto dudoso
 * rotulado como la ubicacion del distrito es peor que la ausencia.
 */
export function puntoEnSuperficie(geometria) {
  const anillos = anillosExteriores(geometria)
  if (anillos.length === 0) return null

  const centro = centroideDeArea(anillos)
  if (!centro) return null

  const latitud = centro[1]
  const cortes = []

  for (const anillo of anillos) {
    for (let i = 0; i < anillo.length - 1; i += 1) {
      const [x0, y0] = anillo[i]
      const [x1, y1] = anillo[i + 1]
      if (y0 > latitud !== y1 > latitud) {
        cortes.push(((x1 - x0) * (latitud - y0)) / (y1 - y0) + x0)
      }
    }
  }

  if (cortes.length < 2) return null
  cortes.sort((uno, otro) => uno - otro)

  let mejor = null
  let largo = -1
  for (let i = 0; i + 1 < cortes.length; i += 2) {
    const ancho = cortes[i + 1] - cortes[i]
    if (ancho > largo) {
      largo = ancho
      mejor = (cortes[i] + cortes[i + 1]) / 2
    }
  }

  return mejor === null ? null : { longitud: mejor, latitud }
}
