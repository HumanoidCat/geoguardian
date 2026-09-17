/**
 * Comprueba el historial de eventos de H7.3.
 *
 * ===========================================================================
 * QUE COMPRUEBA
 * ===========================================================================
 *
 *   CA-1  el JSON del visor corresponde al CSV de hoy, fila por fila
 *   CA-3  los filtros filtran, y el de distrito es legitimo
 *   CA-4  una combinacion sin resultados da cero y se sabe decir cual
 *   CA-5  el CSV exportado lleva BOM, punto y coma, comillas, y es LO FILTRADO
 *   CA-6  todos los eventos traen fuente
 *   CA-7  el historial no le pide nada a la API
 *
 * ===========================================================================
 * LO QUE ESTA HERRAMIENTA MIDE Y LO QUE SOLO LEE
 * ===========================================================================
 *
 * **CA-1, CA-3, CA-4, CA-5 y CA-6 se MIDEN.** Se abre el CSV de verdad, se abre
 * el JSON de verdad, y se importan y ejecutan `filtrar`, `describirFiltros` y
 * `aCsv` desde `frontend/src/datos/historial.js`. No se busca ninguna cadena en
 * el fuente para estos.
 *
 * Eso se pudo hacer porque ese modulo se escribio importable desde Node: su
 * unica atadura a Vite, `import.meta.env.BASE_URL`, lleva `?.`. El verificador
 * de H7.2 tiene que declarar que dos de sus criterios los lee del fuente porque
 * el modulo que miran no se puede ejecutar fuera del navegador; aca esa
 * limitacion se quito en vez de declararla.
 *
 * **Una parte del CA-5 y todo el CA-7 se LEEN del fuente**, y hay que decirlo.
 * La del CA-5 es que el componente le pase a `aCsv` la lista filtrada y no el
 * catalogo entero: eso pasa en el componente, y una llamada directa a `aCsv` no
 * puede verlo por mucho que la descripcion lo sugiera.
 * Comprobar de verdad que la
 * pantalla funciona con la API apagada exige levantarla con la API apagada, que
 * es la evidencia que pide el criterio -`docker compose stop api`- y no cabe en
 * un guion de Node. Lo que si se mide aca es la condicion que lo hace posible:
 * que el modulo no importe el cliente de la API ni nombre su ruta.
 *
 * **CA-2 y CA-8 no estan aca.** CA-2 -romper el CSV y que el generador se
 * detenga- es del lado de Python y va en la evidencia con su corrida. CA-8
 * -leerse a 390 px, alcanzarse con teclado- se comprueba mirando, y por eso el
 * criterio pide capturas a tres anchos reales.
 *
 * Uso:
 *     node frontend/herramientas/verificar_h73.mjs
 *
 * Antes hay que generar el archivo:
 *     python frontend/herramientas/generar_historial.py
 */

import { createHash } from 'node:crypto'
import { readFileSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const CSV = join(RAIZ, 'docs', 'investigacion', 'catalogo-eventos.csv')
const JSON_VISOR = join(RAIZ, 'frontend', 'public', 'historial', 'eventos.json')
const MODULO = join(RAIZ, 'frontend', 'src', 'datos', 'historial.js')
const COMPONENTE = join(RAIZ, 'frontend', 'src', 'componentes', 'HistorialEventos.jsx')

const fallos = []

function comprobar(descripcion, condicion, detalle = '') {
  console.log(`  ${condicion ? 'OK  ' : 'FALLO'}  ${descripcion}`)
  if (!condicion) {
    fallos.push(descripcion)
    if (detalle) console.log(`        ${detalle}`)
  }
}

/**
 * Lector de CSV con comillas. Cincuenta lineas en vez de una dependencia.
 *
 * Las descripciones del catalogo traen comas y comillas dobles dentro de campos
 * entrecomillados; partir por `,` daria filas de largo distinto y el control
 * saldria en rojo por el lector y no por el dato.
 */
function leerCsv(texto) {
  const filas = []
  let fila = []
  let campo = ''
  let entreComillas = false
  const limpio = texto.replace(/^﻿/, '').replace(/\r\n/g, '\n')

  for (let i = 0; i < limpio.length; i += 1) {
    const c = limpio[i]
    if (entreComillas) {
      if (c === '"' && limpio[i + 1] === '"') {
        campo += '"'
        i += 1
      } else if (c === '"') {
        entreComillas = false
      } else {
        campo += c
      }
    } else if (c === '"') {
      entreComillas = true
    } else if (c === ',') {
      fila.push(campo)
      campo = ''
    } else if (c === '\n') {
      fila.push(campo)
      filas.push(fila)
      fila = []
      campo = ''
    } else {
      campo += c
    }
  }
  if (campo !== '' || fila.length > 0) {
    fila.push(campo)
    filas.push(fila)
  }

  const [cabecera, ...cuerpo] = filas
  return cuerpo.map((valores) =>
    Object.fromEntries(cabecera.map((nombre, i) => [nombre, (valores[i] ?? '').trim()])),
  )
}

function huella(texto) {
  return createHash('sha256').update(texto.replace(/\r\n/g, '\n'), 'utf8').digest('hex')
}

async function main() {
  console.log('\nHistorial de eventos, H7.3\n')

  if (!existsSync(JSON_VISOR)) {
    console.log('  FALLO  falta frontend/public/historial/eventos.json')
    console.log('         se genera con: python frontend/herramientas/generar_historial.py\n')
    return 1
  }

  const textoCsv = readFileSync(CSV, 'utf8')
  const delCsv = leerCsv(textoCsv)
  const paquete = JSON.parse(readFileSync(JSON_VISOR, 'utf8'))
  const { filtrar, describirFiltros, aCsv, SEPARADOR } = await import(`file://${MODULO}`)

  // ------------------------------------------------------------------ CA-1 - #
  //
  // Tres comprobaciones y no una. La huella sola dice que el CSV no cambio desde
  // que se genero; no dice que el generador copiara bien. Contar las filas
  // tampoco: 46 filas equivocadas siguen siendo 46. Por eso ademas se compara
  // fila por fila el contenido que viaja.
  console.log('CA-1, el JSON del visor sale del CSV de hoy:')

  comprobar(
    'la huella registrada es la del CSV que hay ahora',
    paquete.huella === huella(textoCsv.replace(/^﻿/, '')),
    `registrada ${String(paquete.huella).slice(0, 16)}..., del CSV ` +
      `${huella(textoCsv.replace(/^﻿/, '')).slice(0, 16)}...`,
  )
  comprobar(
    `${delCsv.length} filas en el CSV y ${paquete.eventos.length} en el JSON`,
    delCsv.length === paquete.eventos.length,
  )

  const clave = (e) =>
    [e.codigo_distrito, e.tipo_evento, e.fecha_inicio, e.fecha_fin, e.severidad, e.fuente].join('|')
  const enCsv = new Set(delCsv.map(clave))
  const faltan = paquete.eventos.filter((e) => !enCsv.has(clave(e)))
  comprobar(
    'cada evento del JSON existe igual en el CSV',
    faltan.length === 0,
    faltan.length > 0 ? `${faltan.length} sin correspondencia, el primero: ${clave(faltan[0])}` : '',
  )

  // ------------------------------------------------------------------ CA-3 - #
  console.log('\nCA-3, los filtros filtran:')

  const eventos = paquete.eventos
  const tipo = paquete.tipos[0].id
  const porTipo = filtrar(eventos, { tipo })
  comprobar(
    `filtrar por tipo ${tipo} da ${porTipo.length} y todos son de ese tipo`,
    porTipo.length === paquete.tipos[0].eventos && porTipo.every((e) => e.tipo_evento === tipo),
  )

  const conEventos = paquete.distritos.find((d) => d.eventos > 0)
  const porDistrito = filtrar(eventos, { distrito: conEventos.codigo })
  comprobar(
    `filtrar por ${conEventos.nombre} da ${porDistrito.length}, y el paquete declara ${conEventos.eventos}`,
    porDistrito.length === conEventos.eventos,
  )

  const desde = '2017-01-01'
  const porFecha = filtrar(eventos, { desde })
  comprobar(
    `filtrar desde ${desde} deja fuera todo lo anterior`,
    porFecha.every((e) => e.fecha_inicio >= desde) &&
      porFecha.length === eventos.filter((e) => e.fecha_inicio >= desde).length,
  )

  comprobar(
    'el orden es de mas reciente a mas antiguo',
    porFecha.every((e, i) => i === 0 || porFecha[i - 1].fecha_inicio >= e.fecha_inicio),
  )

  // El criterio dice: distrito solo si el catalogo trae distrito en TODAS sus
  // filas. Filtrar por un campo que la mitad de las filas no tiene produce una
  // lista vacia que parece un defecto. Se mide en vez de darlo por hecho.
  comprobar(
    'ofrecer el filtro de distrito es legitimo: todas las filas traen distrito',
    eventos.every((e) => e.codigo_distrito),
    `${eventos.filter((e) => !e.codigo_distrito).length} filas sin distrito`,
  )

  // ------------------------------------------------------------------ CA-4 - #
  //
  // Se busca a proposito una combinacion imposible en el dato de verdad: el
  // distrito que el catalogo declara con cero eventos.
  console.log('\nCA-4, una combinacion sin resultados:')

  const vacio = paquete.distritos.find((d) => d.eventos === 0)
  comprobar(
    'el catalogo tiene al menos un distrito sin eventos, que es el caso a probar',
    Boolean(vacio),
    'si todos tuvieran eventos habria que fabricar el caso, y se diria',
  )

  if (vacio) {
    const filtros = { distrito: vacio.codigo, tipo }
    comprobar(
      `${vacio.nombre} con tipo ${tipo} da cero`,
      filtrar(eventos, filtros).length === 0,
    )
    const dicho = describirFiltros(
      filtros,
      (c) => paquete.distritos.find((d) => d.codigo === c)?.nombre,
      (t) => t,
    )
    comprobar(
      `la pantalla sabe nombrar los filtros que produjeron el vacio: ${dicho.join(' · ')}`,
      dicho.length === 2 && dicho.some((p) => p.includes(vacio.nombre)),
    )
  }

  // ------------------------------------------------------------------ CA-5 - #
  console.log('\nCA-5, el CSV exportado:')

  const nombreDeDistrito = (c) => paquete.distritos.find((d) => d.codigo === c)?.nombre ?? ''
  const exportado = aCsv(porTipo, nombreDeDistrito)

  comprobar('empieza con BOM, que es lo que le dice a Excel que es UTF-8', exportado.startsWith('﻿'))
  comprobar(`el separador es ${SEPARADOR}`, exportado.split('\n')[0].includes(SEPARADOR))
  comprobar('los saltos de linea son CRLF', exportado.includes('\r\n'))

  // LO IMPORTANTE DE ESTE CRITERIO: exporta lo filtrado, no el catalogo entero.
  //
  // Se mide contando filas, y se contrasta contra lo que saldria si exportara
  // todo. Sin el contraste, un exportador que ignora el filtro pasaria el dia
  // que el filtro no quite nada.
  const lineas = exportado.replace(/\r\n$/, '').split('\r\n')
  comprobar(
    `${lineas.length - 1} filas exportadas para ${porTipo.length} filtradas (el catalogo tiene ${eventos.length})`,
    lineas.length - 1 === porTipo.length && porTipo.length < eventos.length,
    'si exportara el catalogo entero el filtro seria decorativo',
  )

  // Las descripciones de DesInventar traen comas, punto y coma y comillas. Sin
  // comillar, una sola de ellas parte su fila en dos y el archivo se desalinea
  // entero a partir de ahi.
  //
  // Se comprueba sobre el catalogo ENTERO y no sobre lo filtrado: filtrando por
  // incendio queda una sola fila, y una comprobacion de entrecomillado sobre
  // cero celdas que lo necesiten pasa sin mirar nada. Es la leccion de I-58.
  const todas = aCsv(eventos, nombreDeDistrito)
  const lineasTodas = todas.replace(/\r\n$/, '').split('\r\n')
  const necesitanComillas = eventos.filter((e) =>
    [e.descripcion, e.fuente].some((t) => (t || '').includes(SEPARADOR) || (t || '').includes('"')),
  )
  comprobar(
    `${necesitanComillas.length} celdas del catalogo llevan ${SEPARADOR} o comillas, y ninguna desalinea su fila`,
    necesitanComillas.length > 0 && lineasTodas.length - 1 === eventos.length,
    necesitanComillas.length === 0
      ? 'ninguna celda lo necesita: esta comprobacion no estaria mirando nada'
      : `${lineasTodas.length - 1} filas para ${eventos.length} eventos`,
  )

  // Y ademas contra una celda fabricada, para que este control no dependa de que
  // el catalogo de hoy tenga celdas dificiles. Hoy tiene una sola; el dia que no
  // tenga ninguna, la comprobacion de arriba pasaria sin mirar nada.
  const dificil = [
    {
      codigo_distrito: '50801',
      tipo_evento: 'sequia',
      fecha_inicio: '2020-01-01',
      fecha_fin: '',
      severidad: '',
      fuente: `con ${SEPARADOR} y "comillas" adentro`,
      descripcion: `dos${SEPARADOR}campos${SEPARADOR}en uno`,
    },
  ]
  const conDificil = aCsv(dificil, nombreDeDistrito).replace(/\r\n$/, '').split('\r\n')
  comprobar(
    'una celda con separador y comillas dentro sigue siendo UNA fila',
    conDificil.length === 2 &&
      conDificil[1].includes('""comillas""') &&
      conDificil[1].split(SEPARADOR).length > 8,
    `salieron ${conDificil.length - 1} filas de 1 evento`,
  )

  // EL RIESGO DE VERDAD NO ESTA EN `aCsv`, ESTA EN QUIEN LA LLAMA.
  //
  // `aCsv` recibe una lista y exporta esa lista; probarla con la lista filtrada
  // solo demuestra que no inventa filas. El defecto que el CA-5 quiere impedir
  // -"si exporta todo, el filtro era decorativo"- ocurriria en el componente, si
  // le pasara `historial.eventos` en vez de `visibles`. Eso no lo puede ver una
  // llamada directa a `aCsv`, y decir que si lo ve seria afirmar mas de lo que se
  // mide, que es I-58.
  //
  // ESTO SE LEE DEL FUENTE, como CA-7. Medirlo exigiria montar el componente.
  const jsx = readFileSync(COMPONENTE, 'utf8')
  const llamada = jsx.match(/aCsv\(([^,]+),/)
  comprobar(
    `el componente exporta lo filtrado: aCsv(${llamada ? llamada[1].trim() : '?'}) [leido del fuente]`,
    Boolean(llamada) && llamada[1].trim() === 'visibles',
    'si el primer argumento fuera historial.eventos, el filtro seria decorativo',
  )

  // ------------------------------------------------------------------ CA-6 - #
  console.log('\nCA-6, procedencia:')

  const sinFuente = eventos.filter((e) => !e.fuente)
  comprobar(
    `los ${eventos.length} eventos traen fuente`,
    sinFuente.length === 0,
    `${sinFuente.length} sin fuente`,
  )
  comprobar(
    'la fuente viaja en el CSV exportado',
    exportado.split('\n')[0].includes('fuente'),
  )

  // ------------------------------------------------------------------ CA-7 - #
  //
  // ESTO SE LEE DEL FUENTE, no se ejecuta. Ver el encabezado.
  console.log('\nCA-7, sin API (leido del fuente, no medido):')

  const fuente = readFileSync(MODULO, 'utf8')
  comprobar(
    'historial.js no importa el cliente de la API',
    !/from\s+['"]\.\/cliente['"]/.test(fuente) && !/obtenerSalud|RUTA_API/.test(fuente),
  )
  comprobar(
    'y no nombra la ruta de la API',
    !fuente.includes("'/api'") && !fuente.includes('VITE_API_URL'),
  )

  if (fallos.length > 0) {
    console.log(`\n${fallos.length} comprobaciones fallaron:\n`)
    for (const f of fallos) console.log(`  - ${f}`)
    console.log('\nSe regenera con:\n')
    console.log('    python frontend/herramientas/generar_historial.py\n')
    return 1
  }

  console.log(`\nEl historial corresponde al catalogo: ${eventos.length} eventos.\n`)
  return 0
}

process.exit(await main())
