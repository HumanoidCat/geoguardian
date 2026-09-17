/**
 * La normal climatologica 1991-2020 y la comparacion contra el periodo actual.
 *
 * Funciones puras sobre listas, aparte del componente y por la misma razon que
 * `historial.js`: una funcion pura se prueba sin montar React ni abrir un
 * navegador. `verificar_h74.mjs` las importa y las ejecuta.
 *
 * H7.4. Rubrica de Computacion Grafica, CG-2.
 */

// `?.` porque `import.meta.env` lo inyecta Vite y en Node no existe. Ver la nota
// de `historial.js`: es lo que permite que el verificador mida en vez de leer.
const BASE = import.meta.env?.BASE_URL ?? '/'

/**
 * La normal que escribe `frontend/herramientas/generar_normales.py`.
 *
 * Archivo estatico, como los indices de H5.5 y el historial de H7.3. La normal
 * sale de `crudo.medicion_diaria` y **no hay ruta de la API que la sirva**:
 * `analitico.indice` no existe y `obtener_indices` lanza `TablaPendiente`. Es el
 * camino de D-53, calcular y publicar en vez de almacenar.
 */
export async function obtenerNormales() {
  try {
    const respuesta = await fetch(`${BASE}normales/normales.json`)
    if (!respuesta.ok) return null
    return await respuesta.json()
  } catch {
    return null
  }
}

/**
 * Cuantos dias tiene un mes, sin construir `Date` y sin zona horaria.
 *
 * `new Date('2026-02-01')` es medianoche UTC, que en UTC-6 cae el 31 de enero.
 * Este proyecto ya pago ese error una vez con las fechas del selector, asi que
 * aca la aritmetica de calendario se hace con enteros.
 */
export function diasDelMes(anio, mes) {
  const bisiesto = (anio % 4 === 0 && anio % 100 !== 0) || anio % 400 === 0
  return [31, bisiesto ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1]
}

/**
 * Agrega las filas diarias de un mes, con la MISMA regla que el generador.
 *
 * `suma` para la lluvia y `media` para el resto. Si las dos puntas no usaran la
 * misma regla, la comparacion seria contra otra magnitud y el porcentaje no
 * significaria nada. Por eso la regla viaja en el propio archivo de la normal,
 * en `variables[x].agregacion`, y no se vuelve a escribir aca.
 *
 * Devuelve `null` si el mes no tiene ningun dia con dato: un mes sin dato no es
 * un mes con cero (D-07).
 */
export function agregarMes(filas, campo, agregacion) {
  const valores = filas.map((f) => f[campo]).filter((v) => v !== null && v !== undefined)
  if (valores.length === 0) return null
  const total = valores.reduce((a, b) => a + b, 0)
  return {
    valor: agregacion === 'suma' ? total : total / valores.length,
    dias: valores.length,
  }
}

/**
 * Los periodos que el panel ofrece comparar. Es el CA-4.
 *
 * EL MES EN CURSO NO LLEVA PORCENTAJE, Y ESA ES LA DECISION DEL DISENO.
 *
 * Hoy es 16: el mes lleva 16 de 30 dias. Sumar esos 16 dias de lluvia y
 * dividirlos entre la normal del mes completo daria «47 % por debajo de lo
 * normal», que se lee como sequia y es puro artefacto del calendario. Prorratear
 * la normal tampoco sirve: la lluvia no se reparte pareja dentro del mes.
 *
 * Asi que el mes en curso se muestra **acumulado y con su cuenta de dias**, sin
 * porcentaje, y el porcentaje se reserva para los periodos que si son
 * comparables punta a punta:
 *
 *   mes_en_curso     parcial, sin porcentaje, declara cuantos dias lleva
 *   ultimo_completo  el ultimo mes cerrado, comparacion punta a punta
 *   anio_en_curso    enero a ultimo mes cerrado, contra la suma de esas normales
 *
 * El CA-4 pide al menos el mes y el anio, y permite declarar si solo se puede
 * uno. Se pueden los tres; lo que se declara es cual admite porcentaje.
 */
export const PERIODOS = [
  { id: 'mes_en_curso', nombre: 'Mes en curso', parcial: true },
  { id: 'ultimo_completo', nombre: 'Ultimo mes completo', parcial: false },
  { id: 'anio_en_curso', nombre: 'Anio en curso', parcial: false },
]

/** Los meses que cada periodo abarca, como [{anio, mes}], y si viene completo. */
export function mesesDelPeriodo(periodo, hoy) {
  const anio = hoy.getFullYear()
  const mes = hoy.getMonth() + 1
  const anterior = mes === 1 ? { anio: anio - 1, mes: 12 } : { anio, mes: mes - 1 }

  if (periodo === 'mes_en_curso') return [{ anio, mes }]
  if (periodo === 'ultimo_completo') return [anterior]
  // Enero a ultimo mes cerrado. En enero no hay ningun mes cerrado del anio.
  return Array.from({ length: mes - 1 }, (_, i) => ({ anio, mes: i + 1 }))
}

/**
 * Compara el periodo contra su normal.
 *
 * Devuelve `null` cuando no hay con que comparar, en vez de un cero o un guion:
 * la ausencia se declara (D-07). Los casos son distintos y el panel los dice con
 * palabras distintas, por eso viaja `motivo`.
 */
export function compararPeriodo({
  filas,
  normales,
  variable,
  periodo,
  hoy,
  minimoAnios,
  codigoDistrito,
}) {
  const info = normales?.variables?.[variable]
  if (!info) return null

  // LA SERIE DEL DISTRITO PEDIDO, NO LA PRIMERA QUE APAREZCA.
  //
  // La primera version hacia `Object.values(info.normales)[0]`, que para la
  // lluvia devolvia siempre Tilaran. No es un detalle: medido sobre 1991-2020,
  // **la normal de febrero va de 10 mm en Libano a 84 en Arenal, un factor de
  // 8,6**. Comparar el acumulado de Libano contra la normal de Tilaran daria un
  // superavit inventado del tamano del dato.
  //
  // En octubre el factor es 1,4 y el error habria pasado desapercibido, que es
  // justo lo que lo hacia peligroso: un defecto que solo se nota en la estacion
  // seca y el visor se mira en la lluviosa.
  const serie =
    info.resolucion === 'distrito' ? info.normales[codigoDistrito] : info.normales.canton
  if (!serie) {
    return { motivo: 'sin_normal', detalle: `la normal no trae el distrito ${codigoDistrito}` }
  }
  const meses = mesesDelPeriodo(periodo, hoy)
  if (meses.length === 0) {
    return { motivo: 'sin_meses', detalle: 'todavia no hay ningun mes cerrado este anio' }
  }

  const porFecha = new Map()
  for (const fila of filas) porFecha.set(fila.fecha, fila)

  let actual = 0
  let normal = 0
  let dias = 0
  let diasPosibles = 0
  let aniosMinimos = Infinity

  for (const { anio, mes } of meses) {
    const prefijo = `${anio}-${String(mes).padStart(2, '0')}-`
    const delMes = filas.filter((f) => f.fecha.startsWith(prefijo))
    const agregado = agregarMes(delMes, variable, info.agregacion)
    const normalDelMes = serie.normal[String(mes)]
    if (agregado === null || normalDelMes === undefined) {
      return { motivo: 'sin_dato', detalle: `falta el dato de ${prefijo.slice(0, 7)}` }
    }
    actual += info.agregacion === 'suma' ? agregado.valor : agregado.valor / meses.length
    normal += info.agregacion === 'suma' ? normalDelMes : normalDelMes / meses.length
    dias += agregado.dias
    diasPosibles += diasDelMes(anio, mes)
    aniosMinimos = Math.min(aniosMinimos, serie.anios[String(mes)] ?? 0)
  }

  const parcial = PERIODOS.find((p) => p.id === periodo)?.parcial ?? false
  return {
    actual,
    normal,
    dias,
    diasPosibles: parcial ? diasDelMes(meses[0].anio, meses[0].mes) : diasPosibles,
    parcial,
    anios: aniosMinimos,
    // El porcentaje SOLO para periodos comparables punta a punta. Ver PERIODOS.
    porcentaje: parcial || normal === 0 ? null : ((actual - normal) / normal) * 100,
    desviacion: actual - normal,
    // CA-2: un mes cuya normal sale de pocos anios se marca, no se esconde.
    normalDebil: aniosMinimos < minimoAnios,
    resolucion: info.resolucion,
    unidad: info.unidad,
    etiqueta: info.etiqueta,
  }
}

// NO HAY TABLA DE EQUIVALENCIAS ENTRE LA NORMAL Y LAS MEDICIONES, Y ES A PROPOSITO.
//
// Hubo una: `campoDe(variable)`, que devolvia su argumento tal cual. Una funcion
// identidad con nombre de mapeo es peor que no tenerla, porque promete una
// traduccion que no hace y el dia que los nombres dejen de coincidir nadie la va
// a corregir: seguira compilando y devolviendo lo equivocado.
//
// Los nombres coinciden porque las dos puntas salen del mismo esquema:
// `crudo.medicion_diaria` define `precipitacion_mm`, `temp_max_c`,
// `temp_min_c`, `temp_media_c`, `humedad_relativa_pct` y `viento_ms`;
// `VARIABLES` de `generar_normales.py` usa esas llaves, y la tabla `campos` de
// `exportar_simulados.py` mapea a esos mismos nombres. Si algun dia divergen, lo
// correcto es una tabla de verdad, no una identidad que la finja.
