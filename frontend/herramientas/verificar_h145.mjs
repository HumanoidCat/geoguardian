/**
 * Comprueba la tarjeta de sequia de H14.5: dice el indice medido, no un nivel.
 *
 * ===========================================================================
 * QUE COMPRUEBA, EJECUTANDO
 * ===========================================================================
 *
 *   CA-2  el bloque de CSS de la tarjeta no usa ni un token de la rampa de riesgo
 *   CA-4  las palabras: la categoria sale de la tabla publicada del indice, y el
 *         numero se escribe con un decimal, coma y signo tipografico
 *   CA-9  con dato simulado o sin origen, el cliente NO devuelve indice y dice
 *         por que; con la API real devuelve el ultimo mes CON valor y su fecha
 *
 * Se importan y ejecutan `categoriaDeSequia`, `indiceEnPalabras` y
 * `SEQUIA_MEDIDA` de `palabras.js`, y `obtenerIndiceDeSequia` de `cliente.js`
 * con un `fetch` de mentira que registra lo que se pidio.
 *
 * ===========================================================================
 * LO QUE NO PUEDE MEDIR
 * ===========================================================================
 *
 * Que el numero que llega sea el SPI-6 correcto: eso es del backend y de
 * `backend/api/test_indices.py`. Que la tarjeta se lea a 390 px: eso es una
 * captura, y esta en la evidencia. Aqui se mide lo que corre en el navegador
 * antes de dibujar.
 *
 * SOBRE `import.meta.env`. `cliente.js` lo lee al cargar, y en Node no existe:
 * el modulo revienta al importarlo. Se copia el archivo a una carpeta temporal
 * con esas dos lecturas sustituidas por constantes y se importa la copia. Es una
 * sustitucion textual de dos expresiones, declarada aqui, y no un doble del
 * modulo: el codigo que se ejecuta es el de `cliente.js`.
 *
 * Uso:
 *     node frontend/herramientas/verificar_h145.mjs
 */

import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { pathToFileURL, fileURLToPath } from 'node:url'

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const PALABRAS = join(RAIZ, 'frontend', 'src', 'datos', 'palabras.js')
const CLIENTE = join(RAIZ, 'frontend', 'src', 'datos', 'cliente.js')
const CSS = join(RAIZ, 'frontend', 'src', 'index.css')

const fallos = []

function comprobar(descripcion, condicion, detalle = '') {
  console.log(`  ${condicion ? 'OK  ' : 'FALLO'}  ${descripcion}`)
  if (!condicion) {
    fallos.push(descripcion)
    if (detalle) console.log(`        ${detalle}`)
  }
}

async function importarCliente() {
  const fuente = readFileSync(CLIENTE, 'utf8')
  const sustituido = fuente
    .replaceAll('import.meta.env.VITE_API_URL', "'/api'")
    .replaceAll('import.meta.env.BASE_URL', "'/'")
  if (sustituido.includes('import.meta.env')) {
    throw new Error('cliente.js lee import.meta.env en un lugar que este control no conoce')
  }
  const carpeta = mkdtempSync(join(tmpdir(), 'h145-'))
  const copia = join(carpeta, 'cliente.js')
  writeFileSync(copia, sustituido)
  return import(pathToFileURL(copia).href)
}

/** Un `fetch` de mentira: responde por ruta y anota cada peticion. */
function fetchFalso(respuestas) {
  const pedidas = []
  const funcion = async (url) => {
    const texto = String(url)
    pedidas.push(texto)
    for (const [patron, cuerpo] of respuestas) {
      if (texto.includes(patron)) {
        if (cuerpo instanceof Error) throw cuerpo
        return { ok: true, status: 200, json: async () => cuerpo }
      }
    }
    return { ok: false, status: 404, json: async () => ({}) }
  }
  return { funcion, pedidas }
}

async function main() {
  console.log('\nTarjeta de sequia: el indice medido, H14.5\n')

  // ------------------------------------------------------------ CA-4 palabras
  const { SEQUIA_MEDIDA, categoriaDeSequia, indiceEnPalabras } = await import(
    pathToFileURL(PALABRAS).href
  )

  console.log('CA-4, la categoria sale de la tabla publicada del indice:')
  const casos = [
    [-2.0, 'extremadamente seco'],
    [-2.7, 'extremadamente seco'],
    [-1.5, 'severamente seco'],
    [-1.99, 'severamente seco'],
    [-1.0, 'moderadamente seco'],
    [-1.49, 'moderadamente seco'],
    [-0.99, 'dentro de lo normal'],
    [0, 'dentro de lo normal'],
    [0.99, 'dentro de lo normal'],
    [1.0, 'mas humedo que lo normal'],
    [2.4, 'mas humedo que lo normal'],
  ]
  for (const [valor, esperada] of casos) {
    const categoria = categoriaDeSequia(valor)
    comprobar(
      `${valor} es «${esperada}»`,
      categoria?.palabra === esperada,
      `salio «${categoria?.palabra}»`,
    )
  }
  comprobar('sin valor no hay categoria', categoriaDeSequia(null) === null)
  comprobar('NaN no es un valor', categoriaDeSequia(Number.NaN) === null)
  comprobar(
    'cada categoria tiene su frase con el nombre del distrito',
    SEQUIA_MEDIDA.categorias.every((c) => c.frase('Libano').includes('Libano')),
  )

  console.log('\nCA-4, el numero se escribe con un decimal, coma y signo tipografico:')
  const MENOS = '−'
  comprobar('-1,34 sale «−1,3»', indiceEnPalabras(-1.34) === `${MENOS}1,3`)
  comprobar('-1,36 sale «−1,4»', indiceEnPalabras(-1.36) === `${MENOS}1,4`)
  comprobar('0,5 sale «+0,5»', indiceEnPalabras(0.5) === '+0,5')
  comprobar('-0,04 sale «0,0» y no «−0,0»', indiceEnPalabras(-0.04) === '0,0')
  comprobar('el signo menos no es el guion', !indiceEnPalabras(-1.3).includes('-'))
  comprobar('sin valor no hay texto', indiceEnPalabras(null) === null)

  // ------------------------------------------------------------ CA-9 cliente
  console.log('\nCA-9, el cliente no devuelve indice sobre dato simulado ni sin origen:')
  const cliente = await importarCliente()
  const original = globalThis.fetch

  // 1 · API real, con dos meses sin valor al final: el ultimo CON valor manda.
  const listaReal = [
    { codigo_distrito: '50805', fecha: '2026-05-31', spi_6m: -0.2 },
    { codigo_distrito: '50805', fecha: '2026-06-30', spi_6m: 0.81 },
    { codigo_distrito: '50805', fecha: '2026-07-31', spi_6m: -1.31 },
    { codigo_distrito: '50805', fecha: '2026-08-31', spi_6m: null },
    { codigo_distrito: '50805', fecha: '2026-09-30', spi_6m: null },
  ]
  {
    const { funcion, pedidas } = fetchFalso([
      ['/api/salud', { modo: 'real', base_datos_conectada: true, version_contratos: '1.5.0' }],
      ['/api/distritos/50805/indices', listaReal],
    ])
    globalThis.fetch = funcion
    const indice = await cliente.obtenerIndiceDeSequia('50805')
    comprobar('con la API real devuelve el ultimo mes con valor', indice.valor === -1.31)
    comprobar('y la fecha es la del dato, no la de hoy', indice.fecha === '2026-07-31')
    comprobar('sin motivo de ausencia', indice.motivo === null)
    comprobar(
      'pidio el indice por la ruta nueva, con rango',
      pedidas.some((p) => p.includes('/indices?desde=') && p.includes('&hasta=')),
      pedidas.join(' | '),
    )
  }

  // La negociacion del origen se memoriza en el modulo: para cada escenario se
  // importa una copia nueva, que es lo mismo que abrir el visor de nuevo.
  {
    const { funcion, pedidas } = fetchFalso([
      ['/api/salud', { modo: 'simulado', base_datos_conectada: false }],
      ['/api/distritos/50805/indices', listaReal],
    ])
    globalThis.fetch = funcion
    const indice = await (await importarCliente()).obtenerIndiceDeSequia('50805')
    comprobar('con dato simulado NO hay indice', indice.valor === null && indice.fecha === null)
    comprobar('y dice que es por el simulado', indice.motivo === 'simulado')
    comprobar(
      'ni siquiera pide la ruta: no hay nada que mostrar',
      !pedidas.some((p) => p.includes('/indices')),
    )
  }

  {
    const { funcion, pedidas } = fetchFalso([
      ['/api/salud', new Error('la API no esta')],
      ['/simulados/salud.json', { modo: 'simulado' }],
    ])
    globalThis.fetch = funcion
    const indice = await (await importarCliente()).obtenerIndiceDeSequia('50805')
    comprobar('sobre el respaldo estatico NO hay indice', indice.valor === null)
    comprobar('y dice que es por el origen', indice.motivo === 'sin_origen')
    comprobar('no pide la ruta al respaldo', !pedidas.some((p) => p.includes('/indices')))
  }

  {
    const { funcion } = fetchFalso([
      ['/api/salud', { modo: 'real', base_datos_conectada: true }],
      ['/api/distritos/50808/indices', listaReal.map((f) => ({ ...f, spi_6m: null }))],
    ])
    globalThis.fetch = funcion
    const indice = await (await importarCliente()).obtenerIndiceDeSequia('50808')
    comprobar('con todos los meses sin valor, dice sin_dato', indice.motivo === 'sin_dato')
  }
  globalThis.fetch = original

  comprobar(
    'los tres motivos tienen su frase en palabras',
    ['sin_origen', 'simulado', 'sin_dato'].every(
      (m) => typeof SEQUIA_MEDIDA.sinIndice[m] === 'string' && SEQUIA_MEDIDA.sinIndice[m].length > 20,
    ),
  )

  // ------------------------------------------------------------ CA-2 css
  console.log('\nCA-2, el bloque de la tarjeta no usa la rampa de riesgo:')
  const css = readFileSync(CSS, 'utf8')
  const inicio = css.indexOf('.tarjeta-hoy-medida {')
  const fin = css.indexOf('.circulo-nivel.sin-nivel {')
  comprobar('el bloque existe', inicio > 0 && fin > inicio)
  const bloque = css.slice(inicio, fin)
  comprobar('sin --riesgo-* en el bloque', !bloque.includes('--riesgo'))
  comprobar('sin --texto-sobre-* en el bloque', !bloque.includes('--texto-sobre'))
  comprobar('el numero va en la tipografia de datos', bloque.includes('--fuente-datos'))

  console.log()
  if (fallos.length) {
    console.log(`${fallos.length} comprobaciones fallaron:`)
    for (const f of fallos) console.log(`  - ${f}`)
    process.exit(1)
  }
  console.log('Todas las comprobaciones pasaron.')
}

main().catch((error) => {
  console.error(error)
  process.exit(1)
})
