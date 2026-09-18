/**
 * Comprueba el panel de normales de H7.4.
 *
 * ===========================================================================
 * QUE COMPRUEBA
 * ===========================================================================
 *
 *   CA-1  el archivo declara periodo, cobertura y resolucion de cada variable
 *   CA-2  un mes con normal debil se marca, y el control sabe distinguirlo
 *   CA-3  la comparacion devuelve direccion y magnitud, no un color
 *   CA-4  los tres periodos existen y solo los completos llevan porcentaje
 *   CA-5  la salida es coherente con lo que declara de si misma
 *   CA-6  sin dato se devuelve una ausencia declarada, nunca un cero
 *
 * ===========================================================================
 * LO QUE ESTA HERRAMIENTA MIDE Y LO QUE NO PUEDE MEDIR
 * ===========================================================================
 *
 * **Todo lo de arriba se MIDE**: se abre el archivo de verdad y se importan y
 * ejecutan `compararPeriodo`, `mesesDelPeriodo`, `agregarMes` y `diasDelMes`
 * desde `frontend/src/datos/normales.js`.
 *
 * **Lo que NO se puede medir desde aqui es que la normal salga de la base.** La
 * fuente de H7.4 es `crudo.medicion_diaria`, una tabla, no un archivo que se
 * pueda resumir con una huella como hizo H7.3 con su CSV. Asi que el CA-5 se
 * parte en dos: lo que este control comprueba es que el archivo sea coherente
 * con lo que declara -periodo de 30 anios, doce meses por serie, ningun mes con
 * mas anios que el periodo, la resolucion que corresponde a cada variable, y un
 * volumen de filas compatible con ocho distritos por treinta anios-. Que esos
 * numeros salgan de la base se comprueba **volviendo a correr el generador**, y
 * eso queda en la evidencia con su salida.
 *
 * Decirlo importa: un control que afirmara «la normal sale de la base» mirando
 * solo el JSON estaria afirmando mas de lo que mide, que es I-58.
 *
 * Uso:
 *     node frontend/herramientas/verificar_h74.mjs
 *
 * Antes hay que generar el archivo, con la base levantada:
 *     docker compose up -d db
 *     python frontend/herramientas/generar_normales.py
 */

import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..', '..')
const ARCHIVO = join(RAIZ, 'frontend', 'public', 'normales', 'normales.json')
const MODULO = join(RAIZ, 'frontend', 'src', 'datos', 'normales.js')

const fallos = []

function comprobar(descripcion, condicion, detalle = '') {
  console.log(`  ${condicion ? 'OK  ' : 'FALLO'}  ${descripcion}`)
  if (!condicion) {
    fallos.push(descripcion)
    if (detalle) console.log(`        ${detalle}`)
  }
}

/** Filas diarias fabricadas: `valor` cada dia del mes pedido. */
function diasDe(anio, mes, valor, cuantos) {
  const filas = []
  for (let d = 1; d <= cuantos; d += 1) {
    filas.push({
      fecha: `${anio}-${String(mes).padStart(2, '0')}-${String(d).padStart(2, '0')}`,
      precipitacion_mm: valor,
      temp_max_c: 31,
    })
  }
  return filas
}

async function main() {
  console.log('\nPanel contra la normal historica, H7.4\n')

  if (!existsSync(ARCHIVO)) {
    console.log('  FALLO  falta frontend/public/normales/normales.json')
    console.log('         se genera con la base levantada:')
    console.log('         python frontend/herramientas/generar_normales.py\n')
    return 1
  }

  const n = JSON.parse(readFileSync(ARCHIVO, 'utf8'))
  const m = await import(`file://${MODULO}`)

  // ------------------------------------------------------------------ CA-1 - #
  console.log('CA-1, el archivo declara de donde sale y que cubre:')

  const anios =
    Number(n.periodo.hasta.slice(0, 4)) - Number(n.periodo.desde.slice(0, 4)) + 1
  comprobar(`el periodo es ${n.periodo.desde} a ${n.periodo.hasta}, ${anios} anios`, anios === 30)
  comprobar('declara la fuente', n.fuente === 'crudo.medicion_diaria', `dice ${n.fuente}`)
  comprobar(
    `declara el minimo de la OMM (${n.minimo_anios_omm}) y la cobertura del mes (${n.cobertura_minima_del_mes})`,
    n.minimo_anios_omm > 0 && n.cobertura_minima_del_mes > 0,
  )
  comprobar(
    'cada variable declara etiqueta, unidad, agregacion y resolucion',
    Object.values(n.variables).every(
      (v) => v.etiqueta && v.unidad && v.agregacion && v.resolucion,
    ),
  )

  // ------------------------------------------------------------------ CA-5 - #
  console.log('\nCA-5, la salida es coherente con lo que declara:')

  const esperadas = 8 * 365 * 30
  comprobar(
    `${n.filas_leidas} filas leidas, compatible con ${n.distritos_esperados} distritos por ${anios} anios`,
    n.filas_leidas > esperadas * 0.9,
    `por debajo de ${Math.round(esperadas * 0.9)} sugiere una base cargada a medias`,
  )

  for (const [id, v] of Object.entries(n.variables)) {
    const series = Object.values(v.normales)
    comprobar(
      `${id}: ${series.length} serie(s), resolucion ${v.resolucion}`,
      v.resolucion === 'distrito'
        ? series.length === n.distritos_esperados
        : series.length === 1 && 'canton' in v.normales,
    )
    comprobar(
      `${id}: doce meses, y ningun mes con mas de ${anios} anios`,
      series.every(
        (s) =>
          Object.keys(s.normal).length === 12 &&
          Object.values(s.anios).every((a) => a > 0 && a <= anios),
      ),
    )
  }

  comprobar(
    'solo la precipitacion se agrega sumando',
    Object.entries(n.variables).every(
      ([id, v]) => (v.agregacion === 'suma') === (id === 'precipitacion_mm'),
    ),
    'promediar la lluvia daria mm por dia, que es otra magnitud',
  )

  // ------------------------------------------------------------------ CA-3 - #
  //
  // El nucleo del criterio: la comparacion tiene que usar la normal DEL DISTRITO
  // pedido. Se mide con el mismo acumulado contra tres distritos distintos: si
  // los tres dieran lo mismo, estaria leyendo una serie fija.
  console.log('\nCA-3, la comparacion dice direccion y magnitud, del distrito correcto:')

  const hoy = new Date(2026, 2, 10) // 10 de marzo: febrero es el ultimo completo
  const filas = diasDe(2026, 2, 2, 28) // 56 mm en febrero
  const base = { filas, normales: n, variable: 'precipitacion_mm', hoy, minimoAnios: 30 }

  const porDistrito = ['50805', '50801', '50807'].map((codigoDistrito) =>
    m.compararPeriodo({ ...base, periodo: 'ultimo_completo', codigoDistrito }),
  )
  for (const [i, codigo] of ['50805', '50801', '50807'].entries()) {
    const c = porDistrito[i]
    comprobar(
      `${codigo}: 56 mm contra normal ${c.normal.toFixed(0)} = ${c.porcentaje > 0 ? '+' : ''}${c.porcentaje.toFixed(0)} %`,
      Number.isFinite(c.porcentaje) && typeof c.desviacion === 'number',
    )
  }
  const distintos = new Set(porDistrito.map((c) => Math.round(c.normal)))
  comprobar(
    `las tres normales son distintas (${[...distintos].join(', ')} mm)`,
    distintos.size === 3,
    'si fueran iguales, la comparacion estaria usando una serie fija y no la del distrito',
  )

  // ------------------------------------------------------------------ CA-4 - #
  console.log('\nCA-4, los periodos, y el porcentaje solo donde es comparable:')

  comprobar(`hay ${m.PERIODOS.length} periodos`, m.PERIODOS.length >= 2)

  const parcial = m.compararPeriodo({
    ...base,
    filas: diasDe(2026, 2, 2, 16),
    periodo: 'mes_en_curso',
    hoy: new Date(2026, 1, 16),
    codigoDistrito: '50801',
  })
  comprobar(
    `el mes en curso no lleva porcentaje (${parcial.dias} de ${parcial.diasPosibles} dias)`,
    parcial.porcentaje === null && parcial.parcial === true,
    'un mes a medias contra una normal completa daria un deficit de calendario',
  )
  comprobar(
    'y aun asi trae el acumulado y su cuenta de dias',
    parcial.actual > 0 && parcial.dias === 16 && parcial.diasPosibles === 28,
  )
  comprobar(
    'el ultimo mes completo si lleva porcentaje',
    porDistrito[1].porcentaje !== null && porDistrito[1].parcial === false,
  )

  // ------------------------------------------------------------------ CA-6 - #
  console.log('\nCA-6, la ausencia se declara y nunca es un cero:')

  const casos = [
    ['un distrito que la normal no trae', { ...base, periodo: 'ultimo_completo', codigoDistrito: '99999' }],
    ['sin filas del mes', { ...base, filas: [], periodo: 'ultimo_completo', codigoDistrito: '50801' }],
    [
      'enero, cuando no hay ningun mes cerrado',
      { ...base, periodo: 'anio_en_curso', hoy: new Date(2026, 0, 9), codigoDistrito: '50801' },
    ],
  ]
  for (const [nombre, args] of casos) {
    const r = m.compararPeriodo(args)
    comprobar(
      `${nombre}: devuelve motivo «${r?.motivo}», no una cifra`,
      Boolean(r?.motivo) && r.actual === undefined,
    )
  }

  // ------------------------------------------------------------------ CA-2 - #
  console.log('\nCA-2, una normal debil se marca:')

  comprobar(
    'con el minimo real de la OMM, la normal de hoy no es debil',
    m.compararPeriodo({ ...base, periodo: 'ultimo_completo', codigoDistrito: '50801' })
      .normalDebil === false,
  )
  comprobar(
    'y el control distingue: exigiendo mas anios de los que hay, la marca se enciende',
    m.compararPeriodo({
      ...base,
      periodo: 'ultimo_completo',
      codigoDistrito: '50801',
      minimoAnios: anios + 1,
    }).normalDebil === true,
    'si no se enciende, la marca no esta mirando la cobertura',
  )

  // Aritmetica de calendario, que es de donde salen los dias posibles.
  console.log('\nCalendario:')
  comprobar('2024 bisiesto: febrero 29', m.diasDelMes(2024, 2) === 29)
  comprobar('2026 no bisiesto: febrero 28', m.diasDelMes(2026, 2) === 28)
  comprobar('2000 bisiesto (divisible entre 400)', m.diasDelMes(2000, 2) === 29)
  comprobar('1900 NO bisiesto (divisible entre 100)', m.diasDelMes(1900, 2) === 28)

  if (fallos.length > 0) {
    console.log(`\n${fallos.length} comprobaciones fallaron:\n`)
    for (const f of fallos) console.log(`  - ${f}`)
    console.log('\nSe regenera con la base levantada:\n')
    console.log('    python frontend/herramientas/generar_normales.py\n')
    return 1
  }

  console.log(`\nLa normal ${n.periodo.desde.slice(0, 4)}-${n.periodo.hasta.slice(0, 4)} es coherente y la comparacion usa la serie del distrito.\n`)
  return 0
}

process.exit(await main())
