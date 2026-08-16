/**
 * Unico modulo que sabe de donde vienen los datos.
 *
 * Hoy lee los archivos estaticos que genera
 * frontend/herramientas/exportar_simulados.py, porque la API todavia no existe:
 * segun el roadmap llega en la semana 6.
 *
 * Cuando exista, se cambian las constantes de abajo por las rutas de la API y
 * ningun componente se entera. Ese es el motivo de que todo pase por aca en vez
 * de que cada componente haga su propio fetch.
 */

const ORIGEN_DISTRITOS = '/simulados/distritos.geojson'
const ORIGEN_SALUD = '/simulados/salud.json'

async function leerJson(ruta, queEs) {
  let respuesta
  try {
    respuesta = await fetch(ruta)
  } catch (causa) {
    throw new Error(`No se pudo contactar el origen de ${queEs} (${ruta}).`, {
      cause: causa,
    })
  }

  if (!respuesta.ok) {
    throw new Error(
      `El origen de ${queEs} respondio ${respuesta.status} (${ruta}). ` +
        'Si es 404, falta correr python frontend/herramientas/exportar_simulados.py',
    )
  }

  return respuesta.json()
}

/**
 * Estado de la fuente de datos. El visor lo consulta al arrancar para saber si
 * tiene que mostrar el aviso de modo simulado.
 */
export async function obtenerSalud() {
  return leerJson(ORIGEN_SALUD, 'estado del sistema')
}

/**
 * Los ocho distritos del canton como FeatureCollection listo para Leaflet.
 *
 * No se normaliza ni se completa nada: lo que el origen no trae, no se inventa.
 * Si `poblacion` viene null, sigue siendo null al llegar al componente.
 */
export async function obtenerDistritos() {
  const coleccion = await leerJson(ORIGEN_DISTRITOS, 'los distritos')

  if (coleccion?.type !== 'FeatureCollection' || !Array.isArray(coleccion.features)) {
    throw new Error('El origen de los distritos no devolvio un FeatureCollection valido.')
  }

  if (coleccion.features.length === 0) {
    throw new Error('El origen de los distritos devolvio una coleccion vacia.')
  }

  return coleccion
}
