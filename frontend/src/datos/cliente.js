/**
 * Unico modulo que sabe de donde vienen los datos.
 *
 * Historia H6.6. Hasta el 20 de agosto de 2026 leia los archivos estaticos que
 * genera frontend/herramientas/exportar_simulados.py, segun la decision D-14.
 * Ahora habla con la API de H6.1 y deja esos archivos como respaldo.
 *
 * D-14 prometia que el cambio seria "la URL del fetch, en un solo modulo". El
 * modulo si es uno solo y ningun componente cambio. Pero no fue una URL: la API
 * devuelve listas de objetos del contrato y el visor espera un FeatureCollection
 * y un mapa indexado por codigo. Esa traduccion es lo que ocupa la mitad de abajo
 * de este archivo, y su lugar es este por la misma razon por la que existe el
 * archivo. Ver D-23.
 *
 * SOBRE LA PROPIEDAD DE ESTE ARCHIVO
 *
 * frontend/ es de Avril. La excepcion de docs/07-propiedad-archivos.md autoriza a
 * Alejandro a tocar unicamente este archivo y la configuracion de entorno del
 * visor, para H6.6 y nada mas.
 */

/**
 * Ruta de la API. Relativa a proposito: nunca un origen absoluto.
 *
 * En desarrollo la reenvia el proxy de vite.config.js; en el despliegue, el mismo
 * servidor que sirve el visor. Asi el navegador siempre hace peticiones del mismo
 * origen y no hace falta CORS en backend/api/, que ademas es carpeta de Cesar.
 *
 * VITE_API_URL solo existe para apuntar a otra maquina en una prueba puntual.
 */
const RUTA_API = import.meta.env.VITE_API_URL ?? '/api'

/**
 * Los archivos de D-14. Ya no son el origen: son la degradacion.
 *
 * LAS RUTAS CUELGAN DE `BASE_URL`, Y NO SON ABSOLUTAS DE RAIZ
 *
 * Vite reescribe solo lo que aparece en `index.html` y en los `import`. Estas son
 * cadenas que se arman en tiempo de ejecucion, asi que **no las toca nadie**: lo
 * que se escriba aqui es literalmente lo que va a pedir el navegador.
 *
 * Escritas como `/simulados/...` funcionan mientras el visor viva en la raiz del
 * dominio. Publicado en GitHub Pages vive en `/geoguardian/`, y entonces
 * `/simulados/salud.json` apunta a `humanoidcat.github.io/simulados/salud.json`,
 * que no existe.
 *
 * Medido antes de arreglarlo, sirviendo el `dist` desde un subdirectorio:
 *
 *     /geoguardian/simulados/salud.json  ->  404
 *
 * Y en el sitio publicado **el respaldo es el unico origen que hay**, porque no
 * hay API. El visor se quedaba sin datos y sin error visible.
 *
 * `import.meta.env.BASE_URL` vale `/` en desarrollo y `./` en la construccion,
 * asi que la misma linea sirve en los dos sitios y en cualquier subdirectorio.
 *
 * Ver H11.5, criterio CA-2, y docs/07-propiedad-archivos.md.
 */
const BASE = import.meta.env.BASE_URL

const RESPALDO = {
  salud: `${BASE}simulados/salud.json`,
  distritos: `${BASE}simulados/distritos.geojson`,
  riesgos: (evento) => `${BASE}simulados/riesgos-${evento}.json`,
}

/**
 * Cuanto se espera a la API antes de darla por caida.
 *
 * Sin limite, una API colgada —no caida: colgada— dejaria el visor en "Cargando"
 * para siempre, que es peor que declarar el respaldo. Tres segundos es de sobra
 * para una consulta local y poco para que alguien se quede mirando.
 */
const LIMITE_MS = 3000

export const ORIGEN_API = 'api'
export const ORIGEN_ESTATICO = 'estatico'

// --------------------------------------------------------------------------- //
// Resolucion del origen                                                         //
// --------------------------------------------------------------------------- //

/**
 * Promesa memorizada de la negociacion. Se resuelve UNA sola vez.
 *
 * Es lo que impide que los distritos vengan de la API y los riesgos del respaldo.
 * Hoy los dos origenes coinciden, porque salen del mismo RepositorioSimulado con
 * la misma semilla, asi que una mezcla seria invisible. Cuando H6.2 traiga PostgreSQL
 * dejaran de coincidir y la mezcla pintaria los riesgos de un mundo sobre los
 * distritos de otro sin que nada fallara.
 *
 * Ademas resuelve una carrera real: App.jsx pide la salud y los distritos con un
 * Promise.all, o sea a la vez. Si cada llamada decidiera su propio origen, la de
 * distritos podria decidir antes de que la de salud terminara.
 */
let negociacion = null

function resolverOrigen() {
  if (!negociacion) negociacion = negociar()
  return negociacion
}

async function negociar() {
  try {
    const respuesta = await fetch(`${RUTA_API}/salud`, {
      signal: AbortSignal.timeout(LIMITE_MS),
    })
    if (!respuesta.ok) {
      throw new Error(`la API respondio ${respuesta.status}`)
    }
    return { origen: ORIGEN_API, salud: await respuesta.json(), motivo: null }
  } catch (causa) {
    // Que la API no este no es un error del visor: es el escenario que la
    // historia pide sostener. Se cae al respaldo y se DECLARA por que.
    const salud = await leerJson(RESPALDO.salud, 'estado del sistema')
    return { origen: ORIGEN_ESTATICO, salud, motivo: causa.message }
  }
}

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
 * El dia de hoy en hora local, no en UTC.
 *
 * `toISOString()` devuelve UTC. Costa Rica es UTC-6, asi que a partir de las 18:00
 * el visor pediria el riesgo de manana, todas las noches, y la API no tendria nada
 * que devolver.
 *
 * Se exporta desde H5.7 porque ahora hay tres lugares que necesitan la misma
 * cuenta: la consulta a la API, el tope superior del selector de fecha y la
 * leyenda, que declara si la estimacion es de hoy. Antes habia dos definiciones
 * de "hoy en hora local" en el proyecto y basta que una cambie para que el visor
 * se contradiga a si mismo.
 */
export function fechaDeHoy() {
  const ahora = new Date()
  const mes = String(ahora.getMonth() + 1).padStart(2, '0')
  const dia = String(ahora.getDate()).padStart(2, '0')
  return `${ahora.getFullYear()}-${mes}-${dia}`
}

// --------------------------------------------------------------------------- //
// Traduccion de la forma de la API a la que esperan los componentes             //
// --------------------------------------------------------------------------- //

/**
 * `list[Distrito]` a FeatureCollection.
 *
 * No se agrega `geometria_simulada`, que el archivo estatico si trae. La API no
 * dice si la geometria es de marcador de posicion, y deducirlo del modo seria
 * inventar un dato que nadie afirmo. Ningun componente lo lee.
 */
function aColeccion(distritos) {
  return {
    type: 'FeatureCollection',
    name: 'distritos_tilaran',
    features: distritos.map((distrito) => ({
      type: 'Feature',
      geometry: distrito.geometria,
      properties: {
        codigo: distrito.codigo,
        nombre: distrito.nombre,
        area_km2: distrito.area_km2,
        // null sigue siendo null. Un distrito sin dato censal no tiene cero
        // habitantes: no se sabe cuantos. Es la regla D-07.
        poblacion: distrito.poblacion,
      },
    })),
  }
}

/**
 * `list[Riesgo]` al paquete indexado por codigo que consumen los componentes.
 *
 * Los distritos que la API no devuelve se completan con una entrada explicita sin
 * estimacion. La API solo manda los que tienen: con el simulado siempre son los
 * ocho, pero con datos reales van a faltar, y un distrito ausente del mapa no lo
 * contaria la leyenda. Ocho distritos sin estimacion tienen que verse como ocho
 * sin estimacion, no como una pantalla a medio cargar.
 */
function aPaquete(lista, evento, fecha, codigosConocidos, simulado) {
  const riesgos = {}
  for (const codigo of codigosConocidos) {
    riesgos[codigo] = { nivel: null, probabilidad: null, algoritmo: null, version_modelo: null }
  }
  for (const riesgo of lista) {
    riesgos[riesgo.codigo_distrito] = riesgo
  }

  return { tipo_evento: evento, fecha, simulado, riesgos }
}

// --------------------------------------------------------------------------- //
// Lo que consume App.jsx. Estas tres firmas no cambiaron.                       //
// --------------------------------------------------------------------------- //

/**
 * Estado de la fuente de datos, mas de donde llego.
 *
 * `modo` dice QUE son los datos: simulado o real. Lo decide la API segun que
 * implementacion del repositorio respondio, asi que no puede mentir.
 *
 * `origen` dice POR DONDE llegaron: la API o el respaldo estatico. Son dos ejes
 * distintos y hay que declararlos por separado, porque el dia que la API sirva
 * dato real y se caiga, el respaldo servira dato simulado viejo. Ese es el caso
 * peligroso, y con un solo campo se veria igual que el normal.
 */
export async function obtenerSalud() {
  const { origen, salud, motivo } = await resolverOrigen()
  return { ...salud, origen, motivo_respaldo: motivo }
}

/**
 * Los ocho distritos del canton como FeatureCollection listo para Leaflet.
 *
 * Memorizado: el territorio no cambia durante una sesion, y `obtenerRiesgos` lo
 * necesita para saber que codigos completar. Memorizarlo evita una segunda
 * peticion y evita una carrera entre los dos efectos de App.jsx.
 */
let coleccionEnCurso = null

export function obtenerDistritos() {
  if (!coleccionEnCurso) coleccionEnCurso = pedirDistritos()
  return coleccionEnCurso
}

async function pedirDistritos() {
  const { origen } = await resolverOrigen()

  const coleccion =
    origen === ORIGEN_API
      ? aColeccion(await leerJson(`${RUTA_API}/distritos`, 'los distritos'))
      : await leerJson(RESPALDO.distritos, 'los distritos')

  if (coleccion?.type !== 'FeatureCollection' || !Array.isArray(coleccion.features)) {
    throw new Error('El origen de los distritos no devolvio un FeatureCollection valido.')
  }

  if (coleccion.features.length === 0) {
    throw new Error('El origen de los distritos devolvio una coleccion vacia.')
  }

  return coleccion
}

/**
 * Riesgo de un tipo de evento para todos los distritos.
 *
 * Devuelve el paquete completo, no solo el mapa de riesgos, porque trae la fecha y
 * la marca de simulado que el visor necesita declarar en pantalla.
 *
 * `fecha` es opcional y por omision es hoy, que era el unico comportamiento
 * posible antes de H5.7. Si no hay estimacion para la fecha pedida, los ocho
 * distritos quedan sin estimacion y asi se muestra: **no se cae hacia atras a una
 * fecha anterior**. Ensenar la estimacion de otro dia rotulada con la fecha pedida
 * es un dato con forma valida y contenido falso, que es como empezo la incidencia
 * I-04.
 *
 * ---------------------------------------------------------------------------
 * EL RESPALDO ESTATICO IGNORA LA FECHA, Y ESO SE DECLARA HACIA ARRIBA
 * ---------------------------------------------------------------------------
 *
 * Los archivos de respaldo tienen **una sola fecha**, la que llevaban al
 * exportarse. No hay forma de servir otra desde ahi.
 *
 * El paquete que devuelve el respaldo trae su propia `fecha`, no la pedida, y por
 * eso el visor puede notar la diferencia y bloquear el selector en vez de
 * ofrecer una eleccion que no existe. Devolver el paquete rotulado con la fecha
 * pedida seria el defecto de I-04 otra vez, en otra capa.
 *
 * Un distrito puede venir con `nivel` en null: el contrato lo permite mientras no
 * exista un modelo entrenado. Eso no se corrige aca, se muestra como ausencia de
 * estimacion.
 */
export async function obtenerRiesgos(evento, fechaPedida = null) {
  const { origen, salud } = await resolverOrigen()

  if (origen !== ORIGEN_API) {
    const paquete = await leerJson(RESPALDO.riesgos(evento), `los riesgos de ${evento}`)
    if (!paquete?.riesgos || typeof paquete.riesgos !== 'object') {
      throw new Error(`El origen de los riesgos de ${evento} no devolvio un mapa de riesgos.`)
    }
    return paquete
  }

  const fecha = fechaPedida ?? fechaDeHoy()
  const consulta = new URLSearchParams({ fecha, tipo_evento: evento })
  const lista = await leerJson(`${RUTA_API}/riesgos?${consulta}`, `los riesgos de ${evento}`)

  if (!Array.isArray(lista)) {
    throw new Error(`El origen de los riesgos de ${evento} no devolvio una lista.`)
  }

  const coleccion = await obtenerDistritos()
  const codigos = coleccion.features.map((rasgo) => rasgo.properties.codigo)

  // `simulado` se DERIVA de /salud en vez de leerse escrito dentro del paquete.
  // El archivo estatico lo trae en duro como true, y ese true seguiria diciendo
  // true el dia que los datos fueran reales.
  return aPaquete(lista, evento, fecha, codigos, salud.modo === 'simulado')
}

/**
 * Riesgo de varios eventos a la vez, indexado por evento.
 *
 * El mapa muestra un evento por vez; el semaforo de H7.1 muestra los tres
 * juntos, que es justamente lo que el mapa no puede.
 *
 * Se piden en paralelo y no en serie: son tres consultas independientes y
 * encadenarlas triplicaria la espera sin ninguna ventaja.
 *
 * Si una falla, falla la llamada entera. Devolver dos eventos de tres y no
 * decirlo dejaria una columna vacia que se leeria como "sin riesgo" en vez de
 * "no se pudo consultar".
 */
export async function obtenerRiesgosDeVariosEventos(eventos, fechaPedida = null) {
  const paquetes = await Promise.all(
    eventos.map((evento) => obtenerRiesgos(evento, fechaPedida)),
  )
  return Object.fromEntries(eventos.map((evento, indice) => [evento, paquetes[indice]]))
}
