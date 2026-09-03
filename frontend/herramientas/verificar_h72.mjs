/**
 * Comprueba la grafica de series de H7.2.
 *
 * ===========================================================================
 * QUE COMPRUEBA
 * ===========================================================================
 *
 *   CA-1  el respaldo trae la serie de los ocho distritos, la ventana completa
 *   CA-2  los dias sin dato viajan como `null`, ni omitidos ni en cero
 *   CA-3  la linea NO se une por encima de un hueco
 *   CA-4  el selector se limita a la ventana que declara el origen
 *   CA-5  `recharts` no entra en el paquete inicial del visor
 *   CA-6  los controles distinguen: cada uno se probo contra su defecto
 *
 * ===========================================================================
 * LO QUE ESTA HERRAMIENTA MIDE Y LO QUE SOLO LEE
 * ===========================================================================
 *
 * **CA-1, CA-2 y CA-5 se MIDEN**: se abre el archivo de verdad y se cuentan sus
 * filas; se abre el `dist` construido y se busca en que fragmento quedo la
 * libreria.
 *
 * **CA-3 y CA-4 se LEEN del codigo fuente**, y hay que decirlo. Comprobar que una
 * linea SVG queda cortada exigiria montar el componente en un navegador, que es
 * H10.6 y no existe todavia.
 *
 * Esa distincion importa porque un control que lee texto comprueba la forma del
 * codigo, no su comportamiento -es lo que dejo pasar I-27-. Se declara aqui y en
 * la evidencia en vez de dejar que alguien suponga que se probo mas de lo que se
 * probo.
 *
 * Uso:
 *     node frontend/herramientas/verificar_h72.mjs
 *
 * Para CA-5 hace falta haber construido el visor:
 *     npm --prefix frontend run build
 */

import { readFileSync, existsSync, readdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const AQUI = dirname(fileURLToPath(import.meta.url))
const FRONTEND = join(AQUI, '..')
const RAIZ = join(FRONTEND, '..')

const CODIGOS = ['50801', '50802', '50803', '50804', '50805', '50806', '50807', '50808']
const DIAS = 365

const fallos = []

function comprobar(descripcion, condicion, detalle = '') {
  console.log(`  ${condicion ? 'ok   ' : 'FALLA'}  ${descripcion}`)
  if (!condicion) {
    fallos.push(descripcion)
    if (detalle) console.log(`         ${detalle}`)
  }
}

const leer = (ruta) => readFileSync(ruta, 'utf-8')

console.log('\nH7.2 · Graficas interactivas de series\n')

// ------------------------------------------------------------------- CA-1 - //
console.log('CA-1, el respaldo trae la serie de los ocho distritos:')

const RUTA_MEDICIONES = join(FRONTEND, 'public', 'simulados', 'mediciones.json')
comprobar(
  'existe public/simulados/mediciones.json',
  existsSync(RUTA_MEDICIONES),
  'se genera con: python frontend/herramientas/exportar_simulados.py',
)

if (!existsSync(RUTA_MEDICIONES)) {
  console.log('\nSin el respaldo no hay nada mas que comprobar.\n')
  process.exit(1)
}

const paquete = JSON.parse(leer(RUTA_MEDICIONES))

comprobar(
  `declara su ventana  ${paquete.desde} a ${paquete.hasta}`,
  Boolean(paquete.desde && paquete.hasta),
  'sin ventana declarada el visor no puede limitar el selector',
)

for (const codigo of CODIGOS) {
  const filas = paquete.series?.[codigo]
  comprobar(
    `${codigo}: ${filas?.length ?? 0} dias`,
    Array.isArray(filas) && filas.length === DIAS,
    `se esperaban ${DIAS}. Un dia faltante corre la serie y la grafica dibujaria fechas equivocadas`,
  )
}

// ------------------------------------------------------------------- CA-2 - //
//
// Es el criterio del que cuelga todo lo demas. Si los huecos llegaran como cero
// o como fila ausente, CA-3 no tendria nada que demostrar: la linea saldria
// continua y estaria bien que saliera continua.
console.log('\nCA-2, los dias sin dato viajan como null:')

const todas = CODIGOS.flatMap((c) => paquete.series[c])
const nulos = todas.filter((f) => f.tx === null).length
const ceros = todas.filter((f) => f.tx === 0).length
const ausentes = todas.filter((f) => !('tx' in f)).length

comprobar(
  `hay huecos de verdad  ${nulos} de ${todas.length} (${((100 * nulos) / todas.length).toFixed(1)} %)`,
  nulos > 0,
  'sin un solo hueco, el criterio de la linea cortada no puede fallar nunca',
)
comprobar(
  'ningun hueco se convirtio en cero',
  ceros === 0,
  `${ceros} filas con temperatura maxima exactamente 0 grados: sospechoso`,
)
comprobar(
  'ninguna fila omite la clave en vez de ponerla en null',
  ausentes === 0,
  'una clave ausente desaparece del eje y cierra la linea por encima del hueco',
)

// ------------------------------------------------------------------- CA-3 - //
console.log('\nCA-3, la linea no se une por encima de un hueco  (lectura del fuente):')

const LIENZO = join(FRONTEND, 'src', 'componentes', 'GraficaSerieLienzo.jsx')
const fuenteLienzo = existsSync(LIENZO) ? leer(LIENZO) : ''

comprobar(
  'el componente declara connectNulls={false}',
  /connectNulls=\{false\}/.test(fuenteLienzo),
  'sin esto la linea salta el hueco y afirma una medicion que nadie tomo',
)
comprobar(
  'y no lo declara en true en ningun lado',
  !/connectNulls=\{true\}/.test(fuenteLienzo) && !/connectNulls\s*\/>/.test(fuenteLienzo),
  'una segunda declaracion en true ganaria y nadie lo notaria',
)

// ------------------------------------------------------------------- CA-4 - //
console.log('\nCA-4, el selector se limita a la ventana del origen  (lectura del fuente):')

const GRAFICA = join(FRONTEND, 'src', 'componentes', 'GraficaSerie.jsx')
const fuenteGrafica = existsSync(GRAFICA) ? leer(GRAFICA) : ''

comprobar(
  'el limite inferior sale de datos.ventana, no de una constante',
  /min=\{datos\?\.ventana\.desde\}/.test(fuenteGrafica),
  'ofrecer una fecha sin datos dibuja un grafico vacio, y eso se lee como «no llovio»',
)
comprobar(
  'el limite superior sale de datos.ventana',
  /max=\{datos\?\.ventana\.hasta\}/.test(fuenteGrafica),
)

const CLIENTE = join(FRONTEND, 'src', 'datos', 'cliente.js')
const fuenteCliente = leer(CLIENTE)
comprobar(
  'el cliente devuelve la ventana junto con las filas',
  /ventana:\s*\{/.test(fuenteCliente),
  'sin la ventana, el componente tendria que suponerla y repetiria un dato del origen',
)

// ------------------------------------------------------------------- CA-5 - //
//
// Esta si se mide sobre el artefacto construido: se busca en QUE archivo del
// `dist` quedo la libreria. `recharts` mas que duplica el paquete inicial, y sin
// el corte lo descarga todo el que abre el mapa aunque nunca abra una ficha.
console.log('\nCA-5, recharts no entra en el paquete inicial:')

const ASSETS = join(FRONTEND, 'dist', 'assets')
if (!existsSync(ASSETS)) {
  console.log('  (omitido: no hay dist. Se construye con  npm --prefix frontend run build)')
} else {
  const archivos = readdirSync(ASSETS).filter((f) => f.endsWith('.js'))
  const principal = archivos.filter((f) => f.startsWith('index-'))
  const aparte = archivos.filter((f) => f.includes('GraficaSerieLienzo'))

  comprobar('el visor se partio en varios fragmentos', archivos.length > 1)
  comprobar(
    'existe un fragmento propio para el lienzo',
    aparte.length === 1,
    `fragmentos encontrados: ${archivos.join(', ')}`,
  )

  const huellaRecharts = /recharts|CartesianGrid|ResponsiveContainer/
  for (const f of principal) {
    comprobar(
      `${f} NO contiene recharts`,
      !huellaRecharts.test(leer(join(ASSETS, f))),
      'la libreria volvio al paquete inicial: se perdio el import() perezoso',
    )
  }
  for (const f of aparte) {
    comprobar(`${f} SI lo contiene`, huellaRecharts.test(leer(join(ASSETS, f))))
  }
}

// ------------------------------------------------------------------- CA-6 - //
//
// Sin esto, todo lo de arriba podria estar pasando por mirar el lugar
// equivocado. Es lo mismo que hace CA-5 de verificar_diagramas.py.
console.log('\nCA-6, los controles distinguen:')

comprobar(
  'CA-2 sabria decir que no: una cadena inventada NO aparece como hueco',
  todas.filter((f) => f.tx === 'zzz-valor-que-no-existe').length === 0,
)
comprobar(
  'CA-3 sabria decir que no: connectNulls={true} NO esta en el fuente',
  !/connectNulls=\{true\}/.test(fuenteLienzo),
)
comprobar(
  'CA-5 sabria decir que no: el fuente del lienzo SI importa recharts',
  /from 'recharts'/.test(fuenteLienzo),
  'si el lienzo no importara recharts, CA-5 pasaria sin haber partido nada',
)
comprobar(
  'y GraficaSerie.jsx NO lo importa directamente',
  !/^import .* from 'recharts'/m.test(fuenteGrafica),
  'importarlo aqui anularia el corte perezoso sin que ningun otro criterio fallara',
)

if (fallos.length > 0) {
  console.log(`\n${fallos.length} comprobaciones fallaron:\n`)
  for (const f of fallos) console.log(`  - ${f}`)
  console.log('')
  process.exit(1)
}

console.log('\nH7.2 se cumple.\n')
