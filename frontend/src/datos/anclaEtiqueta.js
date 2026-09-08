/**
 * Donde poner el nombre de un poligono, sin que caiga fuera ni encima de otro.
 *
 * EL CENTRO DE LA CAJA ENVOLVENTE NO SIRVE, Y ESTA MEDIDO
 *
 * Era lo que usaban las etiquetas de distrito. Con cuadrados coincidia con el
 * centro real; con las geometrias del SNIT no. El 2026-09-08, al prender la capa
 * de nombres por omision, **«Quebrada Grande» y «Libano» se solapaban**: el
 * centro de la caja de un distrito alargado cae fuera de su propia parte ancha y
 * se va contra el vecino. Y en el Lago Arenal, que es un arco curvo, el centro de
 * la caja cae directamente en tierra.
 *
 * COMO SE ELIGE EL PUNTO
 *
 *   1. Se cortan `LINEAS` rectas horizontales a lo largo del poligono.
 *   2. En cada una se calculan los cruces con TODOS los anillos -el exterior y
 *      los interiores- y se ordenan. Con la regla de paridad, los tramos entre
 *      el cruce 1 y el 2, el 3 y el 4, etc. son interior; los de en medio son
 *      hueco. Asi la etiqueta nunca cae sobre una isla ni sobre un enclave.
 *   3. Gana el tramo mas largo y el nombre va en su punto medio.
 *
 * Es la parte mas ancha del poligono medida en horizontal, que es justo la
 * direccion en la que se escribe. No es el centroide ni el polo de
 * inaccesibilidad: es mas barato que los dos y alcanza para una etiqueta.
 *
 * Se calcula al vuelo y no se guarda en el GeoJSON a proposito: agregarle una
 * propiedad a un archivo derivado le cambia la suma SHA-256 que declara su
 * procedencia.
 */

const LINEAS = 90

/** Todos los anillos de un rasgo o de una coleccion, exteriores e interiores. */
export function anillosDe(geometria) {
  const salida = []
  const agregar = (poligono) => poligono.forEach((anillo) => salida.push(anillo))
  for (const rasgo of geometria.features ?? [geometria]) {
    const forma = rasgo.geometry ?? rasgo
    if (forma.type === 'Polygon') agregar(forma.coordinates)
    else if (forma.type === 'MultiPolygon') forma.coordinates.forEach(agregar)
  }
  return salida
}

/**
 * Devuelve `[lat, lon]` para Leaflet, o `null` si la geometria no sirve.
 *
 * @param {object} geometria rasgo o coleccion GeoJSON, en grados
 */
export function anclaDeEtiqueta(geometria) {
  const anillos = anillosDe(geometria)
  if (anillos.length === 0) return null

  let sur = Infinity
  let norte = -Infinity
  for (const anillo of anillos) {
    for (const [, lat] of anillo) {
      if (lat < sur) sur = lat
      if (lat > norte) norte = lat
    }
  }
  if (!Number.isFinite(sur) || norte === sur) return null

  let mejor = null
  for (let i = 1; i < LINEAS; i += 1) {
    const lat = sur + ((norte - sur) * i) / LINEAS
    const cruces = []
    for (const anillo of anillos) {
      for (let j = 0; j < anillo.length - 1; j += 1) {
        const [x1, y1] = anillo[j]
        const [x2, y2] = anillo[j + 1]
        if (y1 === y2) continue
        if (lat < Math.min(y1, y2) || lat >= Math.max(y1, y2)) continue
        cruces.push(x1 + ((lat - y1) / (y2 - y1)) * (x2 - x1))
      }
    }
    cruces.sort((uno, otro) => uno - otro)
    for (let k = 0; k + 1 < cruces.length; k += 2) {
      const ancho = cruces[k + 1] - cruces[k]
      if (!mejor || ancho > mejor.ancho) {
        mejor = { ancho, lon: (cruces[k] + cruces[k + 1]) / 2, lat }
      }
    }
  }
  return mejor ? [mejor.lat, mejor.lon] : null
}
