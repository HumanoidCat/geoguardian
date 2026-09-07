/**
 * Resumen de un paquete de riesgos, para decirlo en palabras.
 *
 * Historia H5.9, criterio CA-8: la pagina tiene que decir cual es el riesgo de
 * la fecha mostrada sin que haya que leer el mapa. Todo lo que sale de aca se
 * DERIVA del paquete; ninguna frase se escribe a mano con un numero adentro.
 *
 * Vive en su propio archivo porque lo usan dos componentes -el titular y el
 * selector de evento- y porque no depende de React: se puede probar con Node a
 * secas.
 */

/** De mayor a menor severidad. Es el orden en que se recorre para hallar el maximo. */
export const NIVELES = ['alto', 'medio', 'bajo']

/**
 * Cuenta los distritos de un paquete por nivel.
 *
 * Devuelve `total` (distritos en el paquete), `porNivel` (codigos por nivel, en
 * el orden en que vienen), `sinEstimacion` (codigos con nivel null) y
 * `nivelMaximo` (el mas severo con al menos un distrito, o null si ninguno).
 * Con un paquete null devuelve el resumen vacio, no lanza: el que no llego se
 * describe como ausencia.
 */
export function resumirPaquete(paquete) {
  const porNivel = { alto: [], medio: [], bajo: [] }
  const sinEstimacion = []
  const entradas = Object.entries(paquete?.riesgos ?? {})

  for (const [codigo, riesgo] of entradas) {
    if (riesgo?.nivel && porNivel[riesgo.nivel]) porNivel[riesgo.nivel].push(codigo)
    else sinEstimacion.push(codigo)
  }

  const nivelMaximo = NIVELES.find((nivel) => porNivel[nivel].length > 0) ?? null
  return { total: entradas.length, porNivel, sinEstimacion, nivelMaximo }
}

/**
 * El mismo resumen para varios eventos, indexado por evento.
 * `paquetes` es lo que devuelve `obtenerRiesgosDeVariosEventos`; puede ser null.
 */
export function resumirPaquetes(ids, paquetes) {
  return Object.fromEntries(ids.map((id) => [id, resumirPaquete(paquetes?.[id])]))
}

/**
 * "Santa Rosa y Libano", "Tilaran, Quebrada Grande y Cabeceras". Sin coma antes
 * de la "y", que es como se escribe en espanol. Los codigos que no tengan nombre
 * salen como codigo, no se omiten: omitirlos cambiaria la cuenta que se afirma.
 */
export function enumerar(codigos, nombres) {
  const lista = codigos.map((codigo) => nombres?.[codigo] ?? codigo)
  if (lista.length <= 1) return lista.join('')
  return `${lista.slice(0, -1).join(', ')} y ${lista[lista.length - 1]}`
}

/**
 * "2026-09-06" -> "domingo 6 de setiembre de 2026", en la zona local. Se
 * construye la fecha con sus tres partes y no con `new Date('2026-09-06')`, que
 * la interpreta en UTC y en Costa Rica cae en el dia anterior.
 */
export function fechaEnPalabras(fechaIso) {
  const [anio, mes, dia] = (fechaIso ?? '').split('-').map(Number)
  if (!anio || !mes || !dia) return fechaIso ?? ''
  const fecha = new Date(anio, mes - 1, dia)
  const texto = new Intl.DateTimeFormat('es-CR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(fecha)
  return texto.charAt(0).toUpperCase() + texto.slice(1).replace(',', '')
}
