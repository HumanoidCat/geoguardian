/**
 * La consulta del historico de incidencias.
 *
 * Historia H12.5. Rubrica Troubleshoot.
 *
 * Funciones puras sobre el paquete que genera
 * `frontend/herramientas/generar_incidentes.py`. Sin React y sin DOM, para que se
 * puedan comprobar sin navegador.
 *
 * LO QUE NO HACEN, Y ES EL CRITERIO CA-4
 *
 * **No resumen, no reescriben y no infieren.** Filtran y cuentan. El texto que
 * llega es el del documento y el que se muestra es el mismo. Una bitacora de
 * incidencias vale porque nadie la suavizo.
 */

/** Sin filtros. */
export const FILTROS_VACIOS = { texto: '', detecto: '' }

/** Si hay algo que filtrar. */
export function hayFiltros(filtros) {
  return Boolean(filtros.texto.trim() || filtros.detecto.trim())
}

function normalizar(valor) {
  return (valor ?? '')
    .toLowerCase()
    .normalize('NFD')
    // Se quitan los acentos para que «causa raiz» encuentre «causa raíz». El
    // documento mezcla las dos formas, y obligar a escribir el acento correcto
    // seria trasladarle al lector una inconsistencia que no es suya.
    .replace(/[̀-ͯ]/g, '')
}

/**
 * El texto completo de una incidencia, para buscar dentro.
 *
 * Incluye el identificador, el titulo y **todas** las secciones con su rotulo: si
 * alguien busca «barrido», tiene que encontrar I-58, que es la unica que usa esa
 * palabra como rotulo propio.
 */
function textoBuscable(incidente) {
  const partes = [incidente.id, incidente.titulo]
  for (const seccion of incidente.secciones ?? []) {
    partes.push(seccion.etiqueta)
    // Tambien el codigo: quien busca «ERR_CONNECTION_REFUSED» o «Seq Scan» lo
    // busca porque lo vio en una salida, no en un parrafo.
    for (const bloque of seccion.bloques ?? []) partes.push(bloque.texto)
  }
  return normalizar(partes.join(' '))
}

/** Las incidencias que pasan los filtros, en el orden en que venian. */
export function filtrar(incidentes, filtros) {
  const texto = normalizar(filtros.texto.trim())
  const detecto = normalizar(filtros.detecto.trim())

  return incidentes.filter((incidente) => {
    if (texto && !textoBuscable(incidente).includes(texto)) return false
    if (detecto && !normalizar(incidente.detecto).includes(detecto)) return false
    return true
  })
}

/**
 * Los filtros activos, en palabras, para decir que se esta viendo.
 *
 * Un contador que baja sin decir por que obliga a recordar que se escribio.
 */
export function describirFiltros(filtros) {
  const activos = []
  if (filtros.texto.trim()) activos.push(`texto «${filtros.texto.trim()}»`)
  if (filtros.detecto.trim()) activos.push(`detectada por «${filtros.detecto.trim()}»`)
  return activos
}

/**
 * La fecha en formato ISO que abre el campo `Fecha`, para la cabecera de la ficha.
 *
 * El campo completo es a veces una oracion —I-52 dice «2026-09-13, sobre hechos
 * del 2026-08-23 y del 2026-09-08»— y esa oracion **se conserva entera** en sus
 * secciones. Esto es solo para la columna de la cabecera, donde la oracion
 * completa empujaria el titulo fuera de la pantalla.
 *
 * Extraer no es interpretar: se toma la primera fecha tal cual, y si no hay
 * ninguna se devuelve `null` para que la pantalla lo declare.
 */
export function soloFecha(texto) {
  const hallazgo = /\d{4}-\d{2}-\d{2}/.exec(texto ?? '')
  return hallazgo ? hallazgo[0] : null
}

/**
 * Parte un texto en trozos de formato, para poder mostrarlo como fue escrito.
 *
 * El documento esta escrito en markdown: usa `**enfasis**` y `` `codigo` ``.
 * Insertarlo como texto plano deja los asteriscos y las comillas a la vista, que
 * es lo que se veia antes de esto.
 *
 * **No cambia una sola palabra.** Solo deja de mostrar los signos con los que se
 * marco el formato, y aplica ese formato. Un `**` que se muestra no es fidelidad,
 * es marcado sin interpretar.
 */
export function trozos(texto) {
  const partes = []
  const patron = /\*\*([^*]+)\*\*|`([^`]+)`/g
  let ultimo = 0
  let hallazgo

  while ((hallazgo = patron.exec(texto)) !== null) {
    if (hallazgo.index > ultimo) {
      partes.push({ tipo: 'texto', texto: texto.slice(ultimo, hallazgo.index) })
    }
    if (hallazgo[1] !== undefined) partes.push({ tipo: 'fuerte', texto: hallazgo[1] })
    else partes.push({ tipo: 'codigo', texto: hallazgo[2] })
    ultimo = patron.lastIndex
  }

  if (ultimo < texto.length) partes.push({ tipo: 'texto', texto: texto.slice(ultimo) })
  return partes
}

/**
 * La fecha de generacion, en palabras.
 *
 * CA-5: un historico sin fecha de corte no dice si esta al dia. Si el paquete no
 * la trae, se declara y no se inventa una.
 */
export function describirCorte(paquete, ahora = new Date()) {
  if (!paquete?.generado_en) return null

  const fecha = new Date(paquete.generado_en)
  if (Number.isNaN(fecha.getTime())) return null

  const dias = Math.floor((ahora.getTime() - fecha.getTime()) / 86_400_000)
  const cuando = dias <= 0 ? 'hoy' : dias === 1 ? 'hace 1 dia' : `hace ${dias} dias`

  return { iso: paquete.generado_en.slice(0, 10), cuando, dias }
}
