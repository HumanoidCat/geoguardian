/**
 * El historial de eventos: lectura, filtrado y exportacion.
 *
 * Vive aparte del componente a proposito. Filtrar y exportar son funciones
 * puras sobre listas, y una funcion pura se puede probar sin montar React ni
 * abrir un navegador; dentro del componente solo se podrian comprobar mirando
 * la pantalla, que es la clase de comprobacion que este proyecto ya decidio que
 * no alcanza.
 *
 * H7.3. Rubrica de Computacion Grafica, CG-2.
 */

// `?.` y no `import.meta.env.BASE_URL` a secas.
//
// `import.meta.env` lo inyecta Vite y en Node no existe, asi que la version
// directa lanza `TypeError` **al importar el modulo**, antes de llegar a
// ninguna funcion. Con la guarda, `verificar_h73.mjs` puede importar `filtrar`,
// `aCsv` y `nombreDeArchivo` y **ejecutarlas de verdad** en lugar de buscar
// cadenas en el fuente, que es lo que dejo pasar I-27 y lo que el verificador de
// H7.2 tiene que declarar de dos de sus criterios.
//
// El valor solo lo usa `obtenerHistorial`, que en Node no se llama nunca.
const BASE = import.meta.env?.BASE_URL ?? '/'

/**
 * El paquete que escribe `frontend/herramientas/generar_historial.py`.
 *
 * **No pasa por la API y no es un respaldo.** Es un archivo estatico, como los
 * indices de H5.5: el catalogo de H4.3 no vive en ninguna tabla -
 * `RepositorioPostgres.listar_eventos` lanza `TablaPendiente` y
 * `analitico.evento` no existe en ninguna migracion- asi que no hay backend del
 * que pudiera venir. Es el CA-7: funciona con la API apagada porque nunca le
 * pregunta nada.
 *
 * Si el archivo no esta, se devuelve `null` y la pantalla lo dice. No es un
 * error: quien no corrio el generador no tiene el archivo, y eso es distinto de
 * una falla.
 */
export async function obtenerHistorial() {
  try {
    const respuesta = await fetch(`${BASE}historial/eventos.json`)
    if (!respuesta.ok) return null
    return await respuesta.json()
  } catch {
    return null
  }
}

export const FILTROS_VACIOS = { tipo: '', distrito: '', desde: '', hasta: '' }

/**
 * Los eventos que pasan los filtros, en orden de fecha descendente.
 *
 * Mas reciente primero: quien abre un historial casi siempre quiere saber que
 * paso ultimo, no que paso en 1970. El orden se aplica aca y no en el
 * componente para que lo que se exporta y lo que se ve sean la misma lista en
 * el mismo orden.
 *
 * LAS FECHAS SE COMPARAN COMO TEXTO, Y ESO ES CORRECTO AQUI.
 *
 * `fecha_inicio` viene en ISO-8601 (`AAAA-MM-DD`) del contrato, y en ese formato
 * el orden alfabetico **es** el orden cronologico. Convertir a `Date` no daria
 * nada a cambio y traeria el problema de la zona horaria: `new Date('2017-10-05')`
 * es medianoche UTC, que en UTC-6 es el 4 de octubre a las 18:00, y un rango
 * "desde el 5" dejaria fuera al evento del 5. Ese defecto ya se pago una vez en
 * este proyecto con las fechas del selector.
 */
export function filtrar(eventos, filtros) {
  const { tipo, distrito, desde, hasta } = { ...FILTROS_VACIOS, ...filtros }
  return eventos
    .filter((evento) => {
      if (tipo && evento.tipo_evento !== tipo) return false
      if (distrito && evento.codigo_distrito !== distrito) return false
      if (desde && evento.fecha_inicio < desde) return false
      if (hasta && evento.fecha_inicio > hasta) return false
      return true
    })
    .sort((a, b) => b.fecha_inicio.localeCompare(a.fecha_inicio))
}

export function hayFiltros(filtros) {
  return Object.values({ ...FILTROS_VACIOS, ...filtros }).some((valor) => valor !== '')
}

/**
 * Los filtros activos en palabras, para el CA-4.
 *
 * Una pantalla vacia sin esto se lee como un fallo. Con esto se lee como lo que
 * es: una pregunta que el catalogo contesta con cero. Por eso la lista de
 * filtros acompana al mensaje en vez de quedarse solo en los controles, que
 * pueden estar fuera de la pantalla en el telefono.
 */
export function describirFiltros(filtros, nombreDeDistrito, nombreDeTipo) {
  const { tipo, distrito, desde, hasta } = { ...FILTROS_VACIOS, ...filtros }
  const partes = []
  if (tipo) partes.push(`tipo: ${nombreDeTipo(tipo) ?? tipo}`)
  if (distrito) partes.push(`distrito: ${nombreDeDistrito(distrito) ?? distrito}`)
  if (desde && hasta) partes.push(`entre ${desde} y ${hasta}`)
  else if (desde) partes.push(`desde ${desde}`)
  else if (hasta) partes.push(`hasta ${hasta}`)
  return partes
}

const COLUMNAS_EXPORTADAS = [
  ['distrito', (evento, nombreDeDistrito) => nombreDeDistrito(evento.codigo_distrito) ?? ''],
  ['codigo_distrito', (evento) => evento.codigo_distrito],
  ['tipo_evento', (evento) => evento.tipo_evento],
  ['fecha_inicio', (evento) => evento.fecha_inicio],
  ['fecha_fin', (evento) => evento.fecha_fin],
  ['severidad', (evento) => evento.severidad],
  ['fuente', (evento) => evento.fuente],
  ['descripcion', (evento) => evento.descripcion],
]

/** Separador de lista. Ver el comentario de `aCsv`. */
export const SEPARADOR = ';'

/**
 * Una celda con las comillas de CSV bien puestas.
 *
 * Las descripciones del catalogo traen comas, punto y coma y comillas dobles
 * -son textos de fichas de DesInventar-, asi que esto no es una precaucion
 * teorica: sin comillar, la primera descripcion parte la fila en dos.
 */
function celda(valor) {
  const texto = String(valor ?? '')
  if (texto.includes('"') || texto.includes(SEPARADOR) || texto.includes('\n')) {
    return `"${texto.replaceAll('"', '""')}"`
  }
  return texto
}

/**
 * Los eventos filtrados como CSV que Excel abre sin pelear. Es el CA-5.
 *
 * TRES DECISIONES, CADA UNA POR UN MODO DE FALLO CONCRETO:
 *
 * **BOM al principio.** Sin el, Excel en Windows lee el archivo como cp1252 y
 * las tildes de las descripciones salen como `Ã³`. El BOM es lo que le dice que
 * es UTF-8.
 *
 * **Punto y coma como separador.** En una configuracion regional donde la coma
 * es el separador decimal -la de Costa Rica en Windows- el separador de lista de
 * Excel es el punto y coma, y un CSV con comas se abre entero en la columna A.
 *
 * **Saltos de linea CRLF.** Es lo que pide el formato, y lo que evita que una
 * descripcion con salto de linea se lea como varias filas.
 *
 * ESTO ESTA AFIRMADO Y NO COMPROBADO hasta que alguien lo abra en el Excel de
 * verdad, que es lo que el CA-5 pide y lo que no se puede hacer desde aca. Si
 * abriera mal, lo que cambia es `SEPARADOR`, una constante de este archivo.
 *
 * **Exporta lo filtrado, no el catalogo entero.** Si exportara todo, el filtro
 * seria decorativo: quien filtro sequia y exporto se llevaria las 46 filas sin
 * enterarse.
 */
export function aCsv(eventos, nombreDeDistrito) {
  const cabecera = COLUMNAS_EXPORTADAS.map(([nombre]) => nombre).join(SEPARADOR)
  const filas = eventos.map((evento) =>
    COLUMNAS_EXPORTADAS.map(([, leer]) => celda(leer(evento, nombreDeDistrito))).join(SEPARADOR),
  )
  return `\ufeff${[cabecera, ...filas].join('\r\n')}\r\n`
}

/**
 * Nombre del archivo exportado, con la fecha y los filtros que lo produjeron.
 *
 * Quien exporta tres veces con tres filtros distintos termina con tres archivos
 * en Descargas, y `eventos.csv (1)` no dice cual era cual. El nombre lleva el
 * filtro por la misma razon que el mensaje de vacio lo lleva: el archivo tiene
 * que poder explicarse solo una semana despues.
 */
export function nombreDeArchivo(filtros, hoy = new Date()) {
  const { tipo, distrito, desde, hasta } = { ...FILTROS_VACIOS, ...filtros }
  const partes = ['eventos-tilaran']
  if (tipo) partes.push(tipo)
  if (distrito) partes.push(distrito)
  if (desde || hasta) partes.push(`${desde || 'inicio'}_${hasta || 'hoy'}`)
  partes.push(hoy.toISOString().slice(0, 10))
  return `${partes.join('-')}.csv`
}
