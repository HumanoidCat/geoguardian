/**
 * Transformacion de WGS84 a CRTM05, la retícula nacional de Costa Rica.
 *
 * Historia H5.6. Rubrica de Computacion Grafica, criterio CG-1.
 *
 * ---------------------------------------------------------------------------
 * PARA QUE SIRVE
 * ---------------------------------------------------------------------------
 *
 * Para **comunicar una ubicacion**. Alguien del Comite Municipal de Emergencias
 * que tiene que pasar por radio o por escrito donde esta un punto lo dice en
 * metros de la reticula nacional, no en grados decimales.
 *
 * No se exporta a otro sistema, no se cruza con cartografia en papel y no se
 * guarda en la base. Si alguna de esas hiciera falta seria otra historia.
 *
 * ---------------------------------------------------------------------------
 * POR QUE LAS FORMULAS Y NO UNA BIBLIOTECA
 * ---------------------------------------------------------------------------
 *
 * La historia pide la transformacion **"verificada con puntos de control"**: la
 * comprobacion es entregable tanto como la transformacion. Con una biblioteca la
 * verificacion seguiria siendo obligatoria y probaria menos —que una biblioteca
 * conocida funciona—.
 *
 * Y estas formulas son de 1927, estan en el manual del USGS y **no cambian
 * nunca**. Una dependencia hay que mantenerla, auditarla y actualizarla;
 * cincuenta lineas con una comprobacion al lado, no.
 *
 * Lo comprueba `frontend/herramientas/verificar_proyeccion.py` contra `pyproj`,
 * que es una implementacion independiente.
 *
 * ---------------------------------------------------------------------------
 * POR QUE EPSG:8908 Y NO 5367
 * ---------------------------------------------------------------------------
 *
 * 8908 es el `DefaultCRS` de la capa del SNIT de donde salen las geometrias, asi
 * que medir ahi evita cualquier transformacion de datum. La decision es de H1.3
 * y usar otro sistema seria introducir una segunda verdad en el proyecto.
 *
 * ---------------------------------------------------------------------------
 * POR QUE NO HAY DESPLAZAMIENTO DE DATUM
 * ---------------------------------------------------------------------------
 *
 * PROJ **no aplica ninguno** entre EPSG:4326 y EPSG:8908: CR-SIRGAS esta
 * alineado con el marco global. Lo unico que difiere son los elipsoides:
 *
 *     WGS 84    a = 6 378 137,0    1/f = 298,257223563
 *     GRS 1980  a = 6 378 137,0    1/f = 298,257222101
 *
 * Mismo semieje mayor; el aplanamiento difiere en 1,5 x 10^-9. Medido contra
 * pyproj, la diferencia queda en **milesimas de milimetro**.
 *
 * Eso invierte la comprobacion, y para mejor: no hay que medir un desfase y
 * declararlo, hay que **exigir que no exista**. Cualquier diferencia por encima
 * de un milimetro es un defecto en estas formulas, no una propiedad de la
 * geodesia.
 */

/** Parametros de EPSG:8908, CR-SIRGAS / CRTM05. Verificados contra pyproj. */
export const CRTM05 = {
  epsg: 8908,
  nombre: 'CR-SIRGAS / CRTM05',
  meridianoCentral: -84,
  factorEscala: 0.9999,
  falsoEste: 500000,
  falsoNorte: 0,
  // GRS 1980. El elipsoide del sistema, que no es exactamente el de WGS84.
  semiejeMayor: 6378137.0,
  aplanamientoInverso: 298.257222101,
}

const RAD = Math.PI / 180

/**
 * Proyecta un punto geografico a CRTM05.
 *
 * Serie de Transversa de Mercator de Snyder, USGS Professional Paper 1395,
 * paginas 60 a 64. Es la misma serie que usa PROJ para `tmerc`.
 *
 * La serie pierde precision al alejarse del meridiano central, pero el cantón
 * esta a menos de 1,1 grados de el: la comprobacion mide cuanto, en vez de
 * suponerlo.
 *
 * @param {number} longitud grados decimales, positivo al este
 * @param {number} latitud  grados decimales, positivo al norte
 * @returns {{este: number, norte: number}} metros
 */
export function aCRTM05(longitud, latitud) {
  const { semiejeMayor: a, aplanamientoInverso, meridianoCentral, factorEscala } = CRTM05
  const f = 1 / aplanamientoInverso
  const e2 = 2 * f - f * f
  const ep2 = e2 / (1 - e2)

  const fi = latitud * RAD
  const dl = (longitud - meridianoCentral) * RAD

  const senFi = Math.sin(fi)
  const cosFi = Math.cos(fi)
  const tanFi = Math.tan(fi)

  const N = a / Math.sqrt(1 - e2 * senFi * senFi)
  const T = tanFi * tanFi
  const C = ep2 * cosFi * cosFi
  const A = dl * cosFi

  // Distancia sobre el meridiano desde el ecuador. `lat_0` es 0 en CRTM05, asi
  // que no hay que restar el arco del paralelo de origen.
  const M =
    a *
    ((1 - e2 / 4 - (3 * e2 * e2) / 64 - (5 * e2 * e2 * e2) / 256) * fi -
      ((3 * e2) / 8 + (3 * e2 * e2) / 32 + (45 * e2 * e2 * e2) / 1024) * Math.sin(2 * fi) +
      ((15 * e2 * e2) / 256 + (45 * e2 * e2 * e2) / 1024) * Math.sin(4 * fi) -
      ((35 * e2 * e2 * e2) / 3072) * Math.sin(6 * fi))

  const A2 = A * A
  const A3 = A2 * A
  const A4 = A3 * A
  const A5 = A4 * A
  const A6 = A5 * A

  const este =
    factorEscala * N * (A + ((1 - T + C) * A3) / 6 + ((5 - 18 * T + T * T + 72 * C - 58 * ep2) * A5) / 120) +
    CRTM05.falsoEste

  const norte =
    factorEscala *
      (M +
        N *
          tanFi *
          (A2 / 2 +
            ((5 - T + 9 * C + 4 * C * C) * A4) / 24 +
            ((61 - 58 * T + T * T + 600 * C - 330 * ep2) * A6) / 720)) +
    CRTM05.falsoNorte

  return { este, norte }
}

/**
 * Formato para leer en voz alta o anotar.
 *
 * Metros enteros y con separador de miles. El centimetro no aporta nada a quien
 * pasa una posicion por radio, y dos decimales de mas invitan a leer una
 * precision que la fuente no tiene: estas coordenadas salen de un poligono
 * distrital, no de un GPS.
 */
export function formatearCRTM05({ este, norte }) {
  const entero = (valor) => Math.round(valor).toLocaleString('es-CR')
  return `E ${entero(este)} · N ${entero(norte)}`
}

/** Grados decimales con cinco cifras, poco mas de un metro a esta latitud. */
export function formatearGrados(longitud, latitud) {
  return `${latitud.toFixed(5)}, ${longitud.toFixed(5)}`
}
