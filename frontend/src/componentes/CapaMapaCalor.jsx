import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import L from 'leaflet'
import { dibujarSuperficie, limitesDeColeccion, puntosDeOrigen } from '../datos/interpolacion'

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
 *
 * ---------------------------------------------------------------------------
 * EL DEFECTO QUE ARREGLA I-14, Y POR QUE HACEN FALTA LAS DOS MITADES
 * ---------------------------------------------------------------------------
 *
 * La version original encuadraba la superficie sobre la caja de los CENTROIDES
 * mas un margen fijo de 0,03 grados, y la colocaba tal cual, sin recortar. El
 * profesor lo vio en el sitio publicado el 24 de agosto: la capa se salia del
 * canton y habia distritos que no marcaba.
 *
 * Medido sobre las geometrias del SNIT, con verificar_recorte_calor.py:
 *
 *     caja                    pintado fuera    canton sin pintar
 *     centroides + 0,03            23,4 %            20,6 %
 *     poligonos                    40,5 %             0,0 %
 *     poligonos + recorte           0,0 %             0,0 %
 *
 * Las dos mitades son necesarias y ninguna alcanza sola. Encuadrar sobre los
 * poligonos cubre el canton entero pero empeora el desborde, porque la caja
 * envolvente de una forma irregular es mucho mas grande que la forma. Recortar
 * sin corregir la caja quitaria el desborde y dejaria los mismos huecos.
 *
 * Lo que NO se toco: la opacidad, la rampa y los puntos de origen dibujados
 * encima. Eso no tenia ningun defecto.
 */

// Resolucion de la cuadricula de calculo. 180 x 180 sobre el recuadro del canton
// da celdas de unos 200 m, mas fino de lo que ocho puntos pueden justificar.
// Subirla no agrega informacion, solo suaviza el dibujo.
const RESOLUCION = 180

// Resolucion de la mascara de recorte, que es otra cosa: su borde se ve al lado
// del borde vectorial de los distritos, asi que si queda escalonado se lee como
// un defecto de render. A 1024 el paso es de 36 m. Ver dibujarSuperficie().
const RESOLUCION_RECORTE = 1024

// Opacidad de la superficie. Mas alta tapa el terreno; mas baja hace que la
// rampa deje de distinguirse, el mismo problema que el deslizador de H5.2.
const OPACIDAD_SUPERFICIE = 0.7

export default function CapaMapaCalor({ coleccion, centroides, riesgos, exponente }) {
  const mapa = useMap()

  useEffect(() => {
    const puntos = puntosDeOrigen(centroides ?? [], riesgos)
    if (puntos.length === 0) return undefined

    // El encuadre sale de los POLIGONOS, no de los puntos de origen. Un centroide
    // esta por definicion adentro de su distrito, asi que encuadrar sobre ellos
    // deja afuera la mitad exterior de los distritos del borde.
    const limites = limitesDeColeccion(coleccion)
    if (!limites) return undefined

    const lienzo = dibujarSuperficie({
      puntos,
      limites,
      ancho: RESOLUCION,
      alto: RESOLUCION,
      exponente,
      opacidad: OPACIDAD_SUPERFICIE,
      recorte: coleccion,
      resolucionRecorte: RESOLUCION_RECORTE,
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
  }, [coleccion, centroides, riesgos, exponente, mapa])

  return null
}
