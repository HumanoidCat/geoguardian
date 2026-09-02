/**
 * Comprueba que la capa de mapa de calor se dibuja DENTRO del canton y lo cubre
 * ENTERO.
 *
 * ===========================================================================
 * POR QUE EXISTE
 * ===========================================================================
 *
 * El 24 de agosto el profesor vio el sitio publicado y reporto que la capa de
 * calor se salia del canton y que habia distritos que no marcaba. Las dos cosas
 * salian de la misma linea: la superficie se encuadraba sobre la caja de los
 * CENTROIDES mas un margen fijo de 0,03 grados, y se colocaba sin recortar.
 *
 * Un centroide esta, por definicion, adentro de su distrito. Encuadrar sobre
 * ellos deja afuera la mitad exterior de los distritos del borde. Y una caja es
 * un rectangulo: sobre una forma irregular, buena parte del rectangulo cae en
 * los cantones vecinos y en el lago.
 *
 * Ningun control lo miraba. Se veia en pantalla y nadie mas que un humano
 * mirando podia detectarlo, que es la misma clase de defecto que I-06 e I-10.
 * Esta herramienta es la maquina que faltaba.
 *
 * ===========================================================================
 * QUE MIDE, Y CONTRA QUE
 * ===========================================================================
 *
 * Corre `dibujarSuperficie()` **de verdad** -la funcion que usa el visor, no una
 * copia- sobre un canvas simulado, y despues pregunta pixel por pixel si lo que
 * quedo pintado coincide con el canton.
 *
 * La respuesta de referencia NO sale del mismo algoritmo. El recorte del visor
 * se resuelve con relleno por barrido de lineas y regla par-impar; la referencia
 * se calcula con lanzamiento de rayos sobre las coordenadas crudas del GeoJSON,
 * escrita aparte en este archivo. Dos implementaciones independientes que tienen
 * que coincidir. Si las dos compartieran codigo, la comprobacion no probaria
 * nada: un error en el recorte estaria tambien en la referencia.
 *
 * Se descartan las muestras que caen a menos de una celda de la mascara de
 * cualquier contorno, incluidas las **costuras internas** entre distritos
 * vecinos. Ahi el desacuerdo es de redondeo y no dice nada sobre el recorte: los
 * dos algoritmos tienen que decidir de que lado cae un pixel que el borde parte
 * por la mitad, y no tienen por que decidir igual.
 *
 * Que las costuras internas importen no es obvio y costo encontrarlo. La primera
 * version descartaba solo donde cambiaba la respuesta -o sea el contorno
 * exterior- y quedaban tres muestras en desacuerdo, a 1,8, 9,2 y 10,0 metros de
 * un limite entre distritos. Adentro del canton por los dos lados, asi que el
 * filtro no las veia. La celda de la mascara mide 36 m.
 *
 * De paso quedo medido que los poligonos del SNIT simplificados **no teselan**:
 * la union de los ocho deja 142 huecos diminutos entre distritos vecinos. No es
 * un defecto de esta capa y no se corrige aca, pero explica por que las costuras
 * necesitan tolerancia.
 *
 * Ademas del estado actual, mide el ANTERIOR con la misma vara, para que la
 * mejora quede como numero y no como afirmacion.
 *
 * Uso:
 *     node frontend/herramientas/verificar_recorte_calor.mjs
 *
 * Sale con codigo 1 si algo no se cumple, para poder correrlo en CI.
 */

import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const AQUI = dirname(fileURLToPath(import.meta.url))
const RAIZ = resolve(AQUI, '..', '..')

// Muestras por lado sobre el recuadro. 300 x 300 da 90 000 puntos sobre unos
// 1 120 km2: cada muestra representa 0,012 km2, dos ordenes de magnitud por
// debajo de las diferencias que se quieren detectar.
const MUESTRAS_POR_LADO = 300

// Grados. Solo para reproducir el estado anterior y medirlo.
const MARGEN_VIEJO = 0.03

const fallos = []

function comprobar(descripcion, condicion, detalle = '') {
  console.log(`  ${condicion ? 'OK  ' : 'FALLO'}  ${descripcion}`)
  if (!condicion) {
    fallos.push(descripcion)
    if (detalle) console.log(`        ${detalle}`)
  }
}

/* ========================================================================== *
 * Un canvas simulado, con lo justo que dibujarSuperficie() usa
 * ========================================================================== */

/**
 * El relleno por barrido de lineas con regla par-impar, que es lo que hace el
 * navegador con `fill('evenodd')`. Se muestrea el centro de cada pixel, igual
 * que la especificacion de canvas.
 */
function rellenarParImpar(ancho, alto, caminos, alPintar) {
  const bordes = []
  for (const camino of caminos) {
    for (let i = 0; i < camino.length; i += 1) {
      const [x1, y1] = camino[i]
      const [x2, y2] = camino[(i + 1) % camino.length]
      if (y1 !== y2) bordes.push({ x1, y1, x2, y2 })
    }
  }

  for (let fila = 0; fila < alto; fila += 1) {
    const y = fila + 0.5
    const cruces = []
    for (const { x1, y1, x2, y2 } of bordes) {
      if (y < Math.min(y1, y2) || y >= Math.max(y1, y2)) continue
      cruces.push(x1 + ((y - y1) / (y2 - y1)) * (x2 - x1))
    }
    if (cruces.length === 0) continue
    cruces.sort((a, b) => a - b)

    for (let i = 0; i + 1 < cruces.length; i += 2) {
      const desde = Math.ceil(cruces[i] - 0.5)
      const hasta = Math.ceil(cruces[i + 1] - 0.5)
      for (let columna = Math.max(0, desde); columna < Math.min(ancho, hasta); columna += 1) {
        alPintar(fila, columna)
      }
    }
  }
}

function crearLienzo() {
  const lienzo = { width: 0, height: 0, datos: null }

  const contexto = {
    globalCompositeOperation: 'source-over',
    imageSmoothingEnabled: true,
    imageSmoothingQuality: 'low',
    _camino: [],
    _actual: null,

    createImageData(ancho, alto) {
      return { width: ancho, height: alto, data: new Uint8ClampedArray(ancho * alto * 4) }
    },

    putImageData(imagen) {
      lienzo.datos = new Uint8ClampedArray(imagen.data)
    },

    // Vecino mas cercano. El navegador suaviza; para lo que se mide -donde hay
    // pintura y donde no- el suavizado no cambia nada, porque el alfa de la
    // superficie es constante en todo el lienzo de datos.
    drawImage(origen, dx, dy, dw, dh) {
      const salida = new Uint8ClampedArray(dw * dh * 4)
      for (let fila = 0; fila < dh; fila += 1) {
        const filaOrigen = Math.min(origen.height - 1, Math.floor((fila * origen.height) / dh))
        for (let columna = 0; columna < dw; columna += 1) {
          const columnaOrigen = Math.min(
            origen.width - 1,
            Math.floor((columna * origen.width) / dw),
          )
          const desde = (filaOrigen * origen.width + columnaOrigen) * 4
          const hasta = (fila * dw + columna) * 4
          salida[hasta] = origen.datos[desde]
          salida[hasta + 1] = origen.datos[desde + 1]
          salida[hasta + 2] = origen.datos[desde + 2]
          salida[hasta + 3] = origen.datos[desde + 3]
        }
      }
      lienzo.datos = salida
    },

    beginPath() {
      this._camino = []
      this._actual = null
    },
    moveTo(x, y) {
      this._actual = [[x, y]]
      this._camino.push(this._actual)
    },
    lineTo(x, y) {
      this._actual?.push([x, y])
    },
    closePath() {
      this._actual = null
    },

    fill(regla) {
      if (regla !== 'evenodd') throw new Error(`regla de relleno inesperada: ${regla}`)
      if (this.globalCompositeOperation !== 'destination-in') {
        throw new Error(`composicion inesperada: ${this.globalCompositeOperation}`)
      }

      const dentro = new Uint8Array(lienzo.width * lienzo.height)
      rellenarParImpar(lienzo.width, lienzo.height, this._camino, (fila, columna) => {
        dentro[fila * lienzo.width + columna] = 1
      })
      for (let i = 0; i < dentro.length; i += 1) {
        if (!dentro[i]) lienzo.datos[i * 4 + 3] = 0
      }
    },
  }

  lienzo.getContext = () => contexto
  return lienzo
}

globalThis.document = {
  createElement(etiqueta) {
    if (etiqueta !== 'canvas') throw new Error(`elemento inesperado: ${etiqueta}`)
    const lienzo = crearLienzo()
    // El codigo asigna width/height despues de crear el elemento.
    return new Proxy(lienzo, {
      set(objetivo, clave, valor) {
        objetivo[clave] = valor
        if ((clave === 'width' || clave === 'height') && objetivo.width && objetivo.height) {
          objetivo.datos = new Uint8ClampedArray(objetivo.width * objetivo.height * 4)
        }
        return true
      },
    })
  },
}

/* ========================================================================== *
 * La respuesta de referencia: lanzamiento de rayos, escrito aparte
 * ========================================================================== */

function anillosConCaja(coleccion) {
  const anillos = []
  const recorrer = (nodo) => {
    if (Array.isArray(nodo?.[0]) && typeof nodo[0][0] === 'number') {
      let oeste = Infinity
      let este = -Infinity
      let sur = Infinity
      let norte = -Infinity
      for (const [lon, lat] of nodo) {
        if (lon < oeste) oeste = lon
        if (lon > este) este = lon
        if (lat < sur) sur = lat
        if (lat > norte) norte = lat
      }
      anillos.push({ puntos: nodo, oeste, este, sur, norte })
      return
    }
    for (const hijo of nodo ?? []) recorrer(hijo)
  }
  for (const rasgo of coleccion.features) recorrer(rasgo.geometry?.coordinates)
  return anillos
}

/** Par-impar por lanzamiento de rayos hacia el este. */
function estaDentro(anillos, lon, lat) {
  let cruces = 0
  for (const anillo of anillos) {
    if (lat < anillo.sur || lat > anillo.norte || lon > anillo.este) continue
    const puntos = anillo.puntos
    for (let i = 0, j = puntos.length - 1; i < puntos.length; j = i, i += 1) {
      const [xi, yi] = puntos[i]
      const [xj, yj] = puntos[j]
      if (yi > lat !== yj > lat) {
        const x = xi + ((lat - yi) / (yj - yi)) * (xj - xi)
        if (x > lon) cruces += 1
      }
    }
  }
  return cruces % 2 === 1
}

/* ========================================================================== *
 * La medicion
 * ========================================================================== */

const kmPorGradoLat = 110.574
const kmPorGradoLon = (lat) => 111.32 * Math.cos((lat * Math.PI) / 180)

/**
 * Marca las celdas por las que pasa algun contorno, mas sus vecinas.
 *
 * Es la banda de tolerancia: una celda de ancho a cada lado de cualquier linea
 * dibujada, exterior o interna. Se calcula una sola vez y no depende de la
 * superficie, asi que el estado anterior y el actual se miden descartando
 * exactamente las mismas muestras.
 */
function celdasDeContorno(anillos, caja, lado) {
  const marcadas = new Uint8Array(lado * lado)
  const columna = (lon) => ((lon - caja.oeste) / (caja.este - caja.oeste)) * (lado - 1)
  const fila = (lat) => ((caja.norte - lat) / (caja.norte - caja.sur)) * (lado - 1)

  const marcar = (c, f) => {
    for (let df = -1; df <= 1; df += 1) {
      for (let dc = -1; dc <= 1; dc += 1) {
        const ff = f + df
        const cc = c + dc
        if (ff >= 0 && ff < lado && cc >= 0 && cc < lado) marcadas[ff * lado + cc] = 1
      }
    }
  }

  for (const anillo of anillos) {
    const puntos = anillo.puntos
    for (let i = 0; i < puntos.length; i += 1) {
      const [lon1, lat1] = puntos[i]
      const [lon2, lat2] = puntos[(i + 1) % puntos.length]
      const c1 = columna(lon1)
      const f1c = fila(lat1)
      const c2 = columna(lon2)
      const f2 = fila(lat2)
      const pasos = Math.max(1, Math.ceil(Math.max(Math.abs(c2 - c1), Math.abs(f2 - f1c)) * 2))
      for (let p = 0; p <= pasos; p += 1) {
        const t = p / pasos
        marcar(Math.round(c1 + t * (c2 - c1)), Math.round(f1c + t * (f2 - f1c)))
      }
    }
  }

  return { marcadas, lado, columna, fila }
}

/**
 * Compara lo pintado contra la referencia sobre una rejilla de muestras.
 */
function medir({ lienzo, limites, anillos, cajaMuestreo, contorno }) {
  const { norte, sur, este, oeste } = cajaMuestreo
  const pasoLat = (norte - sur) / (MUESTRAS_POR_LADO - 1)
  const pasoLon = (este - oeste) / (MUESTRAS_POR_LADO - 1)

  const areaMuestra = pasoLat * kmPorGradoLat * pasoLon * kmPorGradoLon((norte + sur) / 2)

  let dentroYPintado = 0
  let dentroSinPintar = 0
  let fueraYPintado = 0
  let evaluadas = 0
  let deBorde = 0

  const pintadoEn = (lat, lon) => {
    if (!lienzo) return false
    if (lat > limites.norte || lat < limites.sur || lon > limites.este || lon < limites.oeste) {
      return false
    }
    const columna = Math.min(
      lienzo.width - 1,
      Math.floor(((lon - limites.oeste) / (limites.este - limites.oeste)) * lienzo.width),
    )
    const fila = Math.min(
      lienzo.height - 1,
      Math.floor(((limites.norte - lat) / (limites.norte - limites.sur)) * lienzo.height),
    )
    return lienzo.datos[(fila * lienzo.width + columna) * 4 + 3] > 0
  }

  for (let f = 0; f < MUESTRAS_POR_LADO; f += 1) {
    const lat = norte - f * pasoLat
    for (let c = 0; c < MUESTRAS_POR_LADO; c += 1) {
      const lon = oeste + c * pasoLon

      const celdaC = Math.round(contorno.columna(lon))
      const celdaF = Math.round(contorno.fila(lat))
      if (
        celdaC >= 0 &&
        celdaC < contorno.lado &&
        celdaF >= 0 &&
        celdaF < contorno.lado &&
        contorno.marcadas[celdaF * contorno.lado + celdaC]
      ) {
        deBorde += 1
        continue
      }

      const dentro = estaDentro(anillos, lon, lat)
      evaluadas += 1
      const pintado = pintadoEn(lat, lon)
      if (dentro && pintado) dentroYPintado += 1
      else if (dentro && !pintado) dentroSinPintar += 1
      else if (!dentro && pintado) fueraYPintado += 1
    }
  }

  const pintadas = dentroYPintado + fueraYPintado
  const delCanton = dentroYPintado + dentroSinPintar

  return {
    evaluadas,
    deBorde,
    km2FueraPintado: fueraYPintado * areaMuestra,
    km2CantonSinPintar: dentroSinPintar * areaMuestra,
    km2Canton: delCanton * areaMuestra,
    porcentajeFuera: pintadas === 0 ? 0 : (100 * fueraYPintado) / pintadas,
    porcentajeSinPintar: delCanton === 0 ? 0 : (100 * dentroSinPintar) / delCanton,
  }
}

/* ========================================================================== *
 * Principal
 * ========================================================================== */

const { dibujarSuperficie, limitesDeColeccion, centroidesDeColeccion, puntosDeOrigen } =
  await import(resolve(RAIZ, 'frontend/src/datos/interpolacion.js'))

const coleccion = JSON.parse(
  readFileSync(resolve(RAIZ, 'frontend/public/simulados/distritos.geojson'), 'utf-8'),
)
const paquete = JSON.parse(
  readFileSync(resolve(RAIZ, 'frontend/public/simulados/riesgos-sequia.json'), 'utf-8'),
)
const riesgos = paquete.riesgos ?? paquete

console.log('\nRecorte de la capa de mapa de calor (I-14)\n')

const anillos = anillosConCaja(coleccion)
const centroides = centroidesDeColeccion(coleccion)
const puntos = puntosDeOrigen(centroides, riesgos)

comprobar('el simulado trae los ocho distritos', coleccion.features.length === 8)
comprobar(
  'hay al menos un punto de origen con probabilidad',
  puntos.length > 0,
  'sin probabilidad no hay superficie que medir, y esta herramienta no probaria nada',
)
if (fallos.length > 0) process.exit(1)

const limites = limitesDeColeccion(coleccion)

// --------------------------------------------------------------- encuadre -- //
console.log('El encuadre sale de los poligonos, no de los centroides:')

const cajaCentroides = {
  norte: Math.max(...centroides.map((c) => c.lat)) + MARGEN_VIEJO,
  sur: Math.min(...centroides.map((c) => c.lat)) - MARGEN_VIEJO,
  este: Math.max(...centroides.map((c) => c.lon)) + MARGEN_VIEJO,
  oeste: Math.min(...centroides.map((c) => c.lon)) - MARGEN_VIEJO,
}

comprobar(
  'la caja de la superficie contiene el canton entero',
  limites.norte >= cajaCentroides.norte &&
    limites.sur <= cajaCentroides.sur &&
    limites.este >= cajaCentroides.este &&
    limites.oeste <= cajaCentroides.oeste,
  'si la caja no contiene a la de los centroides, alguien volvio a encuadrar sobre los puntos',
)

for (const rasgo of coleccion.features) {
  const coordenadas = rasgo.geometry.coordinates.flat(Infinity)
  let dentro = true
  for (let i = 0; i < coordenadas.length; i += 2) {
    const lon = coordenadas[i]
    const lat = coordenadas[i + 1]
    if (lon < limites.oeste || lon > limites.este || lat < limites.sur || lat > limites.norte) {
      dentro = false
      break
    }
  }
  comprobar(`el encuadre cubre ${rasgo.properties.nombre} entero`, dentro)
}

// ---------------------------------------------------------------- recorte -- //
console.log('\nLo pintado coincide con el canton:')

const lienzo = dibujarSuperficie({
  puntos,
  limites,
  ancho: 180,
  alto: 180,
  exponente: 2,
  opacidad: 0.7,
  recorte: coleccion,
  resolucionRecorte: 1024,
})

comprobar('dibujarSuperficie devuelve un lienzo', Boolean(lienzo))
if (!lienzo) process.exit(1)

comprobar(
  'el lienzo devuelto es el del recorte, no el de datos',
  lienzo.width > 180 && lienzo.height > 180,
  `mide ${lienzo.width} x ${lienzo.height}. Si mide 180 x 180, el recorte no se aplico`,
)

const cajaMuestreo = limites
const contorno = celdasDeContorno(anillos, cajaMuestreo, 1024)
const ahora = medir({ lienzo, limites, anillos, cajaMuestreo, contorno })

// El estado anterior, medido con la misma vara: caja de centroides mas margen,
// sin recorte. Se reconstruye llamando a la misma funcion sin `recorte`.
const antes = medir({
  lienzo: dibujarSuperficie({
    puntos,
    limites: cajaCentroides,
    ancho: 180,
    alto: 180,
    exponente: 2,
    opacidad: 0.7,
  }),
  limites: cajaCentroides,
  anillos,
  cajaMuestreo,
  contorno,
})

const f1 = (x) => x.toFixed(1)
console.log('')
console.log('                                    antes (D-28)      ahora')
console.log(
  `  pintado fuera del canton        ${f1(antes.porcentajeFuera).padStart(8)} %   ${f1(ahora.porcentajeFuera).padStart(8)} %`,
)
console.log(
  `  canton sin pintar               ${f1(antes.porcentajeSinPintar).padStart(8)} %   ${f1(ahora.porcentajeSinPintar).padStart(8)} %`,
)
console.log(
  `  km2 fuera del canton            ${f1(antes.km2FueraPintado).padStart(8)}     ${f1(ahora.km2FueraPintado).padStart(8)}`,
)
console.log(
  `  km2 del canton sin pintar       ${f1(antes.km2CantonSinPintar).padStart(8)}     ${f1(ahora.km2CantonSinPintar).padStart(8)}`,
)
console.log(
  `\n  ${ahora.evaluadas} muestras evaluadas, ${ahora.deBorde} descartadas por caer a menos de` +
    ` una celda de\n  la mascara de algun contorno, incluidas las costuras entre distritos\n`,
)

comprobar(
  'no se pinta nada fuera del canton',
  ahora.km2FueraPintado === 0,
  `${f1(ahora.km2FueraPintado)} km2 pintados sobre los cantones vecinos o el lago`,
)
comprobar(
  'no queda territorio del canton sin pintar',
  ahora.km2CantonSinPintar === 0,
  `${f1(ahora.km2CantonSinPintar)} km2 del canton sin superficie`,
)
comprobar(
  'el estado anterior si fallaba las dos, o sea que la medicion distingue',
  antes.km2FueraPintado > 0 && antes.km2CantonSinPintar > 0,
  'si el estado anterior tambien pasa, esta herramienta no esta midiendo nada',
)

if (fallos.length > 0) {
  console.log(`\n${fallos.length} comprobaciones fallaron:\n`)
  for (const f of fallos) console.log(`  - ${f}`)
  console.log('')
  process.exit(1)
}

console.log('El recorte de la capa de calor se cumple.\n')
