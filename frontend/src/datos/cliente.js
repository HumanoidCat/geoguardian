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
 * visor, para H6.6 y para H7.2.
 *
 * H7.2 agrega `obtenerMediciones`. Va aqui y no en el componente por la misma
 * razon que todo lo demas: la serie diaria tiene DOS origenes, y negociar el
 * origen en dos lugares es el defecto que este archivo existe para evitar.
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

/**
 * Los indices NDVI y NDWI de H5.5.
 *
 * **No pasan por la API y no son un respaldo.** Son un producto que se genera
 * con `frontend/herramientas/generar_indices.py` a partir de una escena de
 * Sentinel-2 y queda versionado en `public/`, para que el visor funcione desde
 * `docker compose up` sin credenciales de Copernicus.
 *
 * Si el archivo no esta, la capa simplemente no se ofrece. No es un error: quien
 * no corrio el guion no tiene los PNG, y eso es distinto de una falla.
 */
export async function obtenerIndices() {
  try {
    const respuesta = await fetch(`${BASE}indices/indices.json`)
    if (!respuesta.ok) return null
    return await respuesta.json()
  } catch {
    return null
  }
}

/**
 * Lo que el arbol construido espera de la API, para que H12.2 pueda contrastarlo.
 *
 * Lo genera `frontend/herramientas/generar_esperado.py` desde
 * `contratos/__init__.py`, y queda versionado en `public/` igual que los indices.
 * **No pasa por la API**: preguntarle a la API que version espera el arbol seria
 * preguntarle al examinado por su propia nota.
 *
 * VIVE ACA Y NO EN EL COMPONENTE, Y ESA ES LA LECCION
 *
 * La primera version hacia este `fetch` dentro de `PanelMonitoreo.jsx`, y el
 * verificador de **H6.6** lo rechazo con dos criterios: «los componentes siguen
 * sin saber de la API» y «ningun componente hace su propio fetch». Tenia razon: si
 * cada pantalla busca lo suyo, el dia que cambie de donde sale el dato hay que
 * tocar todas. El acceso a datos vive en este archivo, sin excepciones.
 *
 * Si el archivo no esta, se devuelve `null` y la pantalla lo declara. No es un
 * error: quien no corrio el guion no lo tiene.
 */
export async function obtenerEsperado() {
  try {
    const respuesta = await fetch(`${BASE}estado/esperado.json`)
    if (!respuesta.ok) return null
    return await respuesta.json()
  } catch {
    return null
  }
}

const RESPALDO = {
  salud: `${BASE}simulados/salud.json`,
  distritos: `${BASE}simulados/distritos.geojson`,
  riesgos: (evento) => `${BASE}simulados/riesgos-${evento}.json`,
  mediciones: `${BASE}simulados/mediciones.json`,
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
 * Un distrito puede venir con `nivel` en null: el contrato lo permite cuando no
 * hay estimacion para ese evento y esa fecha. Sequia no la tiene nunca, por
 * D-34; incendio solo en fechas con focos registrados. Eso no se corrige aca, se
 * muestra como ausencia de estimacion.
 *
 * ---------------------------------------------------------------------------
 * UNA CONSULTA POR EVENTO Y FECHA, AUNQUE LA PIDAN DOS (H5.9, CA-3)
 * ---------------------------------------------------------------------------
 *
 * App.jsx pide los riesgos por dos caminos: el del evento que muestra el mapa y
 * el del semaforo, que pide los tres. Medido en el sitio publicado el
 * 2026-09-05, una carga limpia hacia CUATRO peticiones a /api/riesgos para tres
 * eventos: el evento del mapa se pedia dos veces. Los dos efectos eran correctos
 * por separado.
 *
 * Es el mismo patron que `negociacion` y `coleccionEnCurso`: la promesa se
 * memoriza por clave `evento|fecha` y quien llegue segundo recibe la misma. Si
 * la peticion falla, la clave se suelta, para que el siguiente intento vuelva a
 * pedir en vez de heredar el error para siempre.
 */
const riesgosEnCurso = new Map()

export function obtenerRiesgos(evento, fechaPedida = null) {
  const clave = `${evento}|${fechaPedida ?? fechaDeHoy()}`
  if (!riesgosEnCurso.has(clave)) {
    const promesa = pedirRiesgos(evento, fechaPedida).catch((causa) => {
      riesgosEnCurso.delete(clave)
      throw causa
    })
    riesgosEnCurso.set(clave, promesa)
  }
  return riesgosEnCurso.get(clave)
}

async function pedirRiesgos(evento, fechaPedida) {
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

// --------------------------------------------------------------------------- //
// Serie diaria de un distrito. Historia H7.2                                    //
// --------------------------------------------------------------------------- //

/**
 * Las siete variables que la grafica puede dibujar.
 *
 * El orden importa: es el que se ofrece en el selector, y va de lo que la gente
 * busca primero -lluvia- a lo que casi nadie mira.
 *
 * `clave` es el nombre corto del respaldo estatico; `campo`, el del contrato que
 * devuelve la API. Estan los dos porque los dos origenes existen y ninguno es el
 * canonico: traducir en un solo sentido dejaria el otro adivinando.
 */
export const VARIABLES = [
  { clave: 'p', campo: 'precipitacion_mm', etiqueta: 'Precipitacion', unidad: 'mm' },
  { clave: 'tx', campo: 'temp_max_c', etiqueta: 'Temperatura maxima', unidad: '°C' },
  { clave: 'tn', campo: 'temp_min_c', etiqueta: 'Temperatura minima', unidad: '°C' },
  { clave: 'tm', campo: 'temp_media_c', etiqueta: 'Temperatura media', unidad: '°C' },
  { clave: 'h', campo: 'humedad_relativa_pct', etiqueta: 'Humedad relativa', unidad: '%' },
  { clave: 'v', campo: 'viento_ms', etiqueta: 'Viento', unidad: 'm/s' },
  { clave: 'r', campo: 'radiacion_mj_m2', etiqueta: 'Radiacion', unidad: 'MJ/m²' },
]

/**
 * El respaldo entero, memorizado.
 *
 * Son 239 KB y los ocho distritos vienen en el mismo archivo. Sin memorizar, abrir
 * la ficha de cuatro distritos lo descargaria cuatro veces. Se guarda la PROMESA y
 * no el resultado, para que dos fichas abiertas a la vez no disparen dos descargas.
 */
let respaldoMediciones = null

function leerRespaldoMediciones() {
  if (!respaldoMediciones) {
    respaldoMediciones = leerJson(RESPALDO.mediciones, 'las series diarias')
  }
  return respaldoMediciones
}

/**
 * Serie diaria de un distrito, con la ventana que el origen puede cubrir.
 *
 * Devuelve `{ filas, ventana, origen }`:
 *
 *   filas    [{ fecha, precipitacion_mm, temp_max_c, ... }], una por dia, en orden.
 *            Un dia sin medir viene con la variable en `null`.
 *   ventana  { desde, hasta } que el origen puede servir DE VERDAD.
 *   origen   'api' o 'estatico'.
 *
 * POR QUE SE DEVUELVE LA VENTANA Y NO SOLO LAS FILAS
 *
 * La API acepta cualquier rango; el respaldo estatico tiene 365 dias y se acabo.
 * Si el visor ofreciera elegir fuera de esa ventana, la grafica saldria vacia y
 * eso se lee como «no llovio», no como «no hay datos». Devolver la ventana deja
 * que el selector se limite a lo que existe, en vez de mentir por omision.
 *
 * Es el mismo criterio que `obtenerRiesgos` aplica con la fecha: el paquete viene
 * rotulado con la fecha que el origen pudo servir, no con la que se pidio.
 *
 * LOS `null` NO SE FILTRAN
 *
 * Un dia sin medir llega como `null` y asi se queda. Quitar la fila la haria
 * desaparecer del eje de tiempo y la linea se cerraria por encima del hueco:
 * dibujaria una continuidad que nadie observo. Ver el criterio CA-3 de H7.2.
 */
export async function obtenerMediciones(codigo, desde, hasta) {
  const { origen, salud } = await resolverOrigen()

  if (origen !== ORIGEN_API) {
    const paquete = await leerRespaldoMediciones()
    const serie = paquete?.series?.[codigo]
    if (!Array.isArray(serie)) {
      throw new Error(`El respaldo no trae la serie del distrito ${codigo}.`)
    }

    // La ventana del respaldo manda: se recorta lo pedido contra lo que hay.
    const inicio = desde > paquete.desde ? desde : paquete.desde
    const fin = hasta < paquete.hasta ? hasta : paquete.hasta

    const filas = serie
      .filter((f) => f.f >= inicio && f.f <= fin)
      .map((f) => {
        const fila = { fecha: f.f }
        for (const { clave, campo } of VARIABLES) fila[campo] = f[clave] ?? null
        return fila
      })

    return {
      filas,
      ventana: { desde: paquete.desde, hasta: paquete.hasta },
      origen,
      simulado: salud.modo === 'simulado',
    }
  }

  const consulta = new URLSearchParams({ desde, hasta })
  const lista = await leerJson(
    `${RUTA_API}/distritos/${codigo}/mediciones?${consulta}`,
    `las mediciones del distrito ${codigo}`,
  )

  if (!Array.isArray(lista)) {
    throw new Error(`El origen de las mediciones de ${codigo} no devolvio una lista.`)
  }

  const filas = lista.map((m) => {
    const fila = { fecha: m.fecha }
    for (const { campo } of VARIABLES) fila[campo] = m[campo] ?? null
    return fila
  })

  // LA VENTANA LA DECLARAN LOS DIAS CON DATO, NO LAS FILAS DEVUELTAS.
  //
  // Aqui decia «contra la API la ventana pedida ES la que se puede servir: no hay
  // tope», y devolvia `{ desde, hasta }`, o sea la pregunta como si fuera la
  // respuesta. **Era falso y se veia en el sitio publicado.**
  //
  // `GraficaSerie` hace su primera consulta con 1900-01-01 a 2100-01-01
  // justamente para que el origen declare que tiene -lo dice su propio
  // comentario-. Con el eco, la ventana declarada era 1900 a 2100, el encuadre
  // inicial caia en los ultimos noventa dias de esa ventana, y la ficha de cada
  // distrito abria en **octubre de 2099 con noventa dias sin dato**, bajo un pie
  // que afirmaba «Datos disponibles del 2099-10-04 al 2100-01-01».
  //
  // Nunca se vio en desarrollo porque local servia el respaldo estatico, que si
  // declara su ventana de verdad. Se vio al poner la API en modo real. I-60.
  //
  // Y NO BASTA CON MIRAR LA PRIMERA Y LA ULTIMA FILA. Ese fue el primer intento
  // de arreglo y **tampoco servia**, por una razon que estaba a la vista en el
  // SQL: `SQL_MEDICIONES` usa `generate_series` con un LEFT JOIN, o sea que
  // **devuelve una fila por cada dia pedido**, tenga medicion o no. El contrato
  // lo exige -«el consumidor necesita ver los huecos»-, asi que el tramo de las
  // filas devueltas es, letra por letra, el tramo pedido. Derivar la ventana de
  // ahi era el mismo eco con otro disfraz.
  //
  // Lo que declara el tramo real son los dias que traen **alguna** medicion.
  const conDato = filas.filter((f) => VARIABLES.some(({ campo }) => f[campo] !== null))

  // Sin ningun dia con dato la ventana es nula y no se inventa: quien la consuma
  // tiene que distinguir «no hay mediciones» de «hay mediciones de 1900 a 2100».
  const ventana = conDato.length
    ? { desde: conDato[0].fecha, hasta: conDato[conDato.length - 1].fecha }
    : { desde: null, hasta: null }

  return { filas, ventana, origen, simulado: salud.modo === 'simulado' }
}

// --------------------------------------------------------------------------- //
// El indice de sequia, medido (H14.5)                                          //
// --------------------------------------------------------------------------- //

/** Cuantos meses hacia atras se pide el indice. Con seis alcanza; se piden mas por la latencia. */
const MESES_DE_INDICE = 14

/**
 * `meses` meses antes de una fecha ISO, al primer dia de ese mes.
 *
 * Aritmetica sobre los numeros y no sobre `Date`: `toISOString` esta prohibido
 * en este archivo (H6.6, la fecha en hora local) y un `Date` con meses restados
 * arrastra el dia -del 31 al 3 del mes siguiente-. El primer dia del mes no
 * tiene ese problema y para un rango de indices mensuales es el borde natural.
 */
function haceMeses(iso, meses) {
  const [anio, mes] = iso.split('-').map(Number)
  const total = anio * 12 + (mes - 1) - meses
  const nuevoAnio = Math.floor(total / 12)
  const nuevoMes = (total % 12) + 1
  return `${nuevoAnio}-${String(nuevoMes).padStart(2, '0')}-01`
}

/**
 * El ultimo SPI-6 con valor de un distrito, o por que no lo hay.
 *
 * Devuelve `{ valor, fecha, motivo }`:
 *
 *   valor    numero, o `null`.
 *   fecha    ultimo dia del mes que resume el indice, o `null`. NO es la fecha
 *            de la consulta: con CHIRPS el ultimo mes cerrado puede estar a 21 a
 *            51 dias de distancia (D-40), y un indice sin su fecha parece de hoy.
 *   motivo   `null` si hay valor; si no, una de tres razones, para que la
 *            tarjeta diga por que dibuja la ausencia (D-07) y no un guion:
 *              'sin_origen'   el visor esta sobre el respaldo estatico, que no
 *                             trae indices;
 *              'simulado'     la API sirve dato simulado. Un indice sobre lluvia
 *                             inventada es un indice inventado y no se muestra
 *                             (CA-9 de H14.5, la misma regla que H7.4);
 *              'sin_dato'     la API respondio y ningun mes del rango tiene
 *                             serie completa para calcularlo.
 *
 * ES UNA MEDICION, NO UNA ESTIMACION. La ruta `/indices` no trae nivel ni
 * probabilidad, y esta funcion no los inventa: D-34 dice que la sequia no se
 * modela, y D-53 que el indice se calcula al pedirlo con la lluvia que ya cayo.
 *
 * Un fallo de red o un 500 se propaga como excepcion, igual que en
 * `obtenerMediciones`: quien llama decide como lo dice.
 */
export async function obtenerIndiceDeSequia(codigo) {
  const { origen, salud } = await resolverOrigen()

  if (origen !== ORIGEN_API) return { valor: null, fecha: null, motivo: 'sin_origen' }
  if (salud?.modo === 'simulado') return { valor: null, fecha: null, motivo: 'simulado' }

  const hasta = fechaDeHoy()
  const consulta = new URLSearchParams({ desde: haceMeses(hasta, MESES_DE_INDICE), hasta })
  const lista = await leerJson(
    `${RUTA_API}/distritos/${codigo}/indices?${consulta}`,
    `el indice de sequia del distrito ${codigo}`,
  )

  if (!Array.isArray(lista)) {
    throw new Error(`El origen del indice de ${codigo} no devolvio una lista.`)
  }

  // El ultimo mes CON valor. Los meses que la fuente no entrego viajan con
  // `spi_6m: null` y no se omiten; aca se los salta para encontrar el ultimo
  // que si se pudo calcular, y su fecha es la que se muestra.
  let ultimo = null
  for (const fila of lista) {
    if (typeof fila?.spi_6m === 'number' && fila.fecha) ultimo = fila
  }

  if (!ultimo) return { valor: null, fecha: null, motivo: 'sin_dato' }
  return { valor: ultimo.spi_6m, fecha: ultimo.fecha, motivo: null }
}
