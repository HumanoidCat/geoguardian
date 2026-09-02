/**
 * Interpolacion por distancia inversa (IDW) para el mapa de calor.
 *
 * Historia H5.4. Rubrica de Computacion Grafica, criterio CG-1.
 *
 * IDW estima el valor en un punto desconocido como el promedio de los valores
 * conocidos, pesando cada uno por el inverso de su distancia elevada a un
 * exponente. Lo cercano pesa mas. Con exponente alto la superficie se pega a los
 * puntos y queda con "islas"; con exponente bajo queda plana.
 *
 * ---------------------------------------------------------------------------
 * DOS DECISIONES QUE NO SON TECNICAS Y NO CONVIENE DESHACER
 * ---------------------------------------------------------------------------
 *
 * 1. Se interpola la PROBABILIDAD, no el nivel de riesgo.
 *
 *    El nivel es una variable ordinal de tres categorias: bajo, medio, alto.
 *    Convertirlo a 1, 2, 3 e interpolar asumiria que la distancia entre "bajo" y
 *    "medio" es igual que entre "medio" y "alto", y eso nadie lo establecio.
 *
 *    Desde D-21, `probabilidad` esta definida como P(nivel = alto): la
 *    probabilidad que el modelo asigna a la clase mas severa del evento. Eso la
 *    vuelve continua, monotona en el riesgo y comparable entre distritos y entre
 *    eventos, que son exactamente las tres propiedades que una interpolacion
 *    necesita para significar algo.
 *
 *    Consecuencia: cuando no haya modelo entrenado, `probabilidad` viene en null
 *    y NO hay mapa de calor. La pantalla lo dice; no se dibuja una superficie
 *    plana que parezca un resultado.
 *
 * 2. La paleta es distinta de la escala de riesgo, a proposito.
 *
 *    Las dos superficies representan riesgo, pero no la misma magnitud: la
 *    coropleta pinta una CLASE de tres categorias y esta pinta una PROBABILIDAD
 *    continua. Si compartieran rampa, un morado intermedio y un naranja "medio"
 *    se leerian como lo mismo, y no lo son.
 *
 *    Se usa BuPu de ColorBrewer, una familia de color que no se puede confundir
 *    con la otra. Verificada igual que la rampa de riesgo: monotona en escala de
 *    grises, con al menos 42 niveles de separacion entre pasos vecinos, y el
 *    orden se conserva bajo protanopia y deuteranopia.
 *
 *    NOTA HISTORICA. Antes de D-21 el contrato no decia que magnitud era
 *    `probabilidad`. Se asumio "confianza del modelo", y con esa lectura la
 *    superficie podia pintar mas intenso a un distrito de riesgo bajo con
 *    estimacion muy confiable que a uno de riesgo alto con estimacion dudosa. La
 *    definicion de D-21 elimina ese problema de raiz.
 *
 * ---------------------------------------------------------------------------
 * LIMITACION QUE HAY QUE DECLARAR
 * ---------------------------------------------------------------------------
 *
 * Ocho puntos son muy pocos para una interpolacion. La superficie resultante es
 * suave y parece un analisis fino, pero no lo es: es una tecnica de
 * visualizacion, no una inferencia. Por eso el visor dibuja los ocho puntos de
 * origen encima de la superficie y la leyenda declara sobre cuantos se calculo.
 */

/** BuPu de ColorBrewer, cinco pasos. Grises: 245, 200, 152, 110, 62. */
export const RAMPA_PROBABILIDAD = [
  { limite: 0.0, color: [237, 248, 251] },
  { limite: 0.25, color: [179, 205, 227] },
  { limite: 0.5, color: [140, 150, 198] },
  { limite: 0.75, color: [136, 86, 167] },
  { limite: 1.0, color: [129, 15, 124] },
]

/** Distancia minima, en grados, para no dividir entre cero. */
const EPSILON = 1e-9

/**
 * Valor interpolado en un punto, o null si no hay ningun punto de origen.
 *
 * Si la celda coincide con un punto conocido, devuelve su valor exacto en lugar
 * de dividir entre una distancia nula.
 */
export function interpolar(puntos, lat, lon, exponente = 2) {
  if (!puntos?.length) return null

  let numerador = 0
  let denominador = 0

  for (const punto of puntos) {
    const dLat = lat - punto.lat
    const dLon = lon - punto.lon
    const distancia2 = dLat * dLat + dLon * dLon

    if (distancia2 < EPSILON) return punto.valor

    const peso = 1 / Math.pow(distancia2, exponente / 2)
    numerador += peso * punto.valor
    denominador += peso
  }

  return denominador === 0 ? null : numerador / denominador
}

/** Color RGB para un valor de 0 a 1, interpolando dentro de la rampa. */
export function colorDeValor(valor) {
  const v = Math.min(Math.max(valor, 0), 1)

  for (let i = 0; i < RAMPA_PROBABILIDAD.length - 1; i += 1) {
    const desde = RAMPA_PROBABILIDAD[i]
    const hasta = RAMPA_PROBABILIDAD[i + 1]

    if (v <= hasta.limite) {
      const tramo = hasta.limite - desde.limite
      const t = tramo === 0 ? 0 : (v - desde.limite) / tramo
      return [
        Math.round(desde.color[0] + t * (hasta.color[0] - desde.color[0])),
        Math.round(desde.color[1] + t * (hasta.color[1] - desde.color[1])),
        Math.round(desde.color[2] + t * (hasta.color[2] - desde.color[2])),
      ]
    }
  }

  return RAMPA_PROBABILIDAD[RAMPA_PROBABILIDAD.length - 1].color
}

/**
 * Caja envolvente de la coleccion entera, en grados.
 *
 * ---------------------------------------------------------------------------
 * POR QUE ESTA FUNCION EXISTE Y POR QUE NO SE USAN LOS CENTROIDES
 * ---------------------------------------------------------------------------
 *
 * La primera version encuadraba la superficie sobre la caja de los CENTROIDES
 * mas un margen fijo de 0,03 grados. El margen estaba puesto para tapar el corte
 * recto, y lo que en realidad hacia era dejar territorio del canton afuera: el
 * centroide de un distrito esta, por definicion, adentro del distrito, asi que
 * la mitad exterior de los distritos del borde caia fuera de la caja.
 *
 * Medido sobre las geometrias del SNIT (verificar_recorte_calor.py):
 *
 *     caja de centroides + 0,03      caja de los poligonos
 *     20,6 % del canton sin pintar   0,0 % sin pintar
 *     Tronadora cubierta al 54,5 %   todos los distritos al 100 %
 *     Arenal al 68,3 %
 *
 * Eso es exactamente lo que reporto el profesor el 24 de agosto: la capa se
 * salia del canton y habia distritos que no marcaba.
 */
export function limitesDeColeccion(coleccion) {
  if (!coleccion?.features?.length) return null

  let oeste = Infinity
  let este = -Infinity
  let sur = Infinity
  let norte = -Infinity

  for (const rasgo of coleccion.features) {
    const coordenadas = rasgo.geometry.coordinates.flat(Infinity)
    for (let i = 0; i < coordenadas.length; i += 2) {
      const lon = coordenadas[i]
      const lat = coordenadas[i + 1]
      if (lon < oeste) oeste = lon
      if (lon > este) este = lon
      if (lat < sur) sur = lat
      if (lat > norte) norte = lat
    }
  }

  if (!(este > oeste) || !(norte > sur)) return null
  return { norte, sur, este, oeste }
}

/**
 * Anillos de todos los poligonos de la coleccion, como listas de pares.
 *
 * Aplana Polygon y MultiPolygon a la misma forma: una lista de anillos, cada uno
 * una lista de [lon, lat]. El consumidor no tiene que saber cual de los dos vino.
 */
export function anillosDeColeccion(coleccion) {
  if (!coleccion?.features?.length) return []

  const anillos = []

  const recorrer = (nodo) => {
    // Un anillo es una lista de pares: su primer elemento es un par, y el primer
    // elemento de ese par es un numero.
    if (Array.isArray(nodo?.[0]) && typeof nodo[0][0] === 'number') {
      anillos.push(nodo)
      return
    }
    for (const hijo of nodo ?? []) recorrer(hijo)
  }

  for (const rasgo of coleccion.features) recorrer(rasgo.geometry?.coordinates)
  return anillos
}

/**
 * Centro de la caja envolvente de cada distrito.
 *
 * Se calcula con aritmetica simple sobre las coordenadas del GeoJSON, sin
 * depender de Leaflet, para que la funcion se pueda probar sin un navegador y
 * para que el mismo resultado sirva al mapa y a la leyenda.
 *
 * Es el centro de la caja, no el centroide del poligono. Con los cuadrados
 * actuales coinciden; con las geometrias del SNIT sera aproximado. Para ubicar
 * un punto de interpolacion alcanza, y la diferencia es mucho menor que el error
 * que ya introduce interpolar sobre ocho puntos.
 */
export function centroidesDeColeccion(coleccion) {
  if (!coleccion?.features) return []

  return coleccion.features.map((rasgo) => {
    const coordenadas = rasgo.geometry.coordinates.flat(Infinity)
    let minLon = Infinity
    let maxLon = -Infinity
    let minLat = Infinity
    let maxLat = -Infinity

    for (let i = 0; i < coordenadas.length; i += 2) {
      const lon = coordenadas[i]
      const lat = coordenadas[i + 1]
      if (lon < minLon) minLon = lon
      if (lon > maxLon) maxLon = lon
      if (lat < minLat) minLat = lat
      if (lat > maxLat) maxLat = lat
    }

    return {
      codigo: rasgo.properties.codigo,
      nombre: rasgo.properties.nombre,
      lat: (minLat + maxLat) / 2,
      lon: (minLon + maxLon) / 2,
    }
  })
}

/**
 * Extrae los puntos de origen: un centroide por distrito con probabilidad.
 *
 * Los distritos sin probabilidad quedan fuera. No se sustituyen por cero ni por
 * el promedio de los demas: un distrito sin estimacion no aporta informacion, y
 * rellenarlo inventaria un dato para que la superficie quede mas bonita.
 */
export function puntosDeOrigen(centroides, riesgos) {
  return centroides
    .map((centroide) => {
      const probabilidad = riesgos?.[centroide.codigo]?.probabilidad
      if (probabilidad === null || probabilidad === undefined) return null
      return { ...centroide, valor: probabilidad }
    })
    .filter(Boolean)
}

/**
 * Dibuja la superficie interpolada sobre un canvas, recortada contra los
 * poligonos si se le pasa una coleccion.
 *
 * Devuelve el canvas listo para usarse como imagen superpuesta, o null si no hay
 * puntos suficientes.
 *
 * ---------------------------------------------------------------------------
 * POR QUE SON DOS LIENZOS Y NO UNO
 * ---------------------------------------------------------------------------
 *
 * Los dos tienen que resolver cosas distintas y no conviene atarlos:
 *
 * - La INTERPOLACION es cara -una pasada por cada punto de origen en cada
 *   celda- y no gana nada con mas resolucion: sale de ocho puntos. A 180 x 180
 *   la celda mide unos 200 m, ya mas fino de lo que ocho puntos justifican.
 *
 * - El RECORTE si necesita resolucion, porque su borde se ve al lado del borde
 *   vectorial de los distritos que dibuja Leaflet. A 180 el recorte quedaria
 *   escalonado en pasos de 200 m y se leeria como otro defecto de render, que es
 *   justo lo que estamos arreglando. A 1024 el paso baja a 36 m.
 *
 * Asi que se interpola barato, se amplia con el suavizado del navegador -que es
 * lo que da la apariencia continua que se busca- y se recorta caro. Subir el
 * exponente con el deslizador solo rehace el lienzo chico.
 *
 * ---------------------------------------------------------------------------
 * UNA IMPRECISION MEDIDA QUE SE DEJA COMO ESTA
 * ---------------------------------------------------------------------------
 *
 * Las filas del lienzo son lineales en LATITUD, y `L.imageOverlay` coloca la
 * imagen linealmente en el plano PROYECTADO de Mercator. Las dos escalas no son
 * la misma, asi que la mascara queda corrida respecto del borde vectorial.
 *
 * Medido sobre el recuadro del canton: **4,9 m en el peor caso**, a media
 * altura. La celda de la propia mascara mide 36 m. Corregirlo seria afinar por
 * debajo de lo que la mascara puede expresar.
 */
export function dibujarSuperficie({
  puntos,
  limites,
  ancho,
  alto,
  exponente,
  opacidad,
  recorte,
  resolucionRecorte,
}) {
  if (!puntos?.length) return null

  const datos = document.createElement('canvas')
  datos.width = ancho
  datos.height = alto

  const contextoDatos = datos.getContext('2d')
  const imagen = contextoDatos.createImageData(ancho, alto)

  const { norte, sur, este, oeste } = limites
  const pasoLat = (norte - sur) / (alto - 1)
  const pasoLon = (este - oeste) / (ancho - 1)
  const alfa = Math.round(Math.min(Math.max(opacidad, 0), 1) * 255)

  for (let fila = 0; fila < alto; fila += 1) {
    const lat = norte - fila * pasoLat

    for (let columna = 0; columna < ancho; columna += 1) {
      const lon = oeste + columna * pasoLon
      const valor = interpolar(puntos, lat, lon, exponente)
      const [r, g, b] = colorDeValor(valor ?? 0)

      const indice = (fila * ancho + columna) * 4
      imagen.data[indice] = r
      imagen.data[indice + 1] = g
      imagen.data[indice + 2] = b
      imagen.data[indice + 3] = alfa
    }
  }

  contextoDatos.putImageData(imagen, 0, 0)

  const anillos = anillosDeColeccion(recorte)
  if (anillos.length === 0) return datos

  const lado = resolucionRecorte ?? Math.max(ancho, alto)
  const lienzo = document.createElement('canvas')
  lienzo.width = Math.round(lado * ((este - oeste) / (norte - sur)))
  lienzo.height = lado

  const contexto = lienzo.getContext('2d')
  contexto.imageSmoothingEnabled = true
  contexto.imageSmoothingQuality = 'high'
  contexto.drawImage(datos, 0, 0, lienzo.width, lienzo.height)

  // La mascara. `destination-in` conserva lo ya dibujado solo donde el trazo
  // nuevo lo cubre, asi que la superficie sobrevive dentro de los poligonos y
  // desaparece afuera. Es una sola operacion sobre el lienzo entero: no hay que
  // decidir celda por celda si esta dentro.
  const x = (lon) => ((lon - oeste) / (este - oeste)) * lienzo.width
  const y = (lat) => ((norte - lat) / (norte - sur)) * lienzo.height

  contexto.globalCompositeOperation = 'destination-in'
  contexto.beginPath()
  for (const anillo of anillos) {
    anillo.forEach(([lon, lat], indice) => {
      if (indice === 0) contexto.moveTo(x(lon), y(lat))
      else contexto.lineTo(x(lon), y(lat))
    })
    contexto.closePath()
  }
  // `evenodd` y no `nonzero`: con evenodd un anillo interior descuenta al
  // exterior sea cual sea el sentido en que este escrito. El GeoJSON del SNIT no
  // garantiza la regla de la mano derecha, y con `nonzero` un hueco escrito al
  // reves quedaria relleno.
  contexto.fill('evenodd')
  contexto.globalCompositeOperation = 'source-over'

  return lienzo
}
