/**
 * Lo que la pantalla «Hoy en tu distrito» le dice a una persona.
 *
 * Historia H14.2. Las siete reglas de tono estan en el documento de publico y
 * mensaje; aca estan aplicadas, y algunas son comprobables por el verificador de
 * frases.
 *
 * POR QUE ESTE ARCHIVO EXISTE
 *
 * El visor sabe decir «riesgo alto de lluvia intensa, percentil 99 del acumulado
 * de 72 horas». Eso es correcto y no le sirve a la senora de Libano. La
 * traduccion no es un detalle de presentacion: es la historia. Vive en un archivo
 * propio, y no repartida por los componentes, para que se pueda leer entera,
 * corregir sin tocar React y comprobar con un guion.
 *
 * LAS REGLAS QUE SE APLICAN ACA
 *
 *  - Segunda persona y siempre un verbo. «Revisa el camino», no «se recomienda
 *    precaucion».
 *  - Tres palabras que ya existen en la calle: tranquilo, atento, cuidado. La
 *    palabra va SIEMPRE junto al color; el color solo nunca dice el nivel.
 *  - Ninguna sigla. CHIRPS, POWER, FIRMS, SPI, P99 y los nombres de algoritmo
 *    viven un nivel mas abajo.
 *  - Cuando no se sabe, se dice, y se dice por que en una linea.
 *  - Nada de «tiempo real» salvo donde el dato lo sea.
 *
 * LO QUE NO SE DICE, Y ES DELIBERADO
 *
 * La tarjeta de incendio **no dice cuantos focos hay**. Por el contrato, `alto`
 * significa «al menos un foco en los ultimos siete dias» y no existe nivel medio
 * para este evento; el conteo no sale por ninguna ruta de la API. Decir «hay dos
 * focos» seria inventarlo, y seria la misma incidencia que ya se registro dos
 * veces: un conteo que no dice contra que base se pregunto.
 */

/**
 * Las tres palabras, cada una con su termino tecnico al lado.
 *
 * NO ES UN REEMPLAZO, ES UN PAR, Y ESO ES DELIBERADO
 *
 * «Riesgo alto» y «cuidado» son el mismo dato en dos registros: uno es lenguaje
 * de escala y el otro es lenguaje de persona. Doña Marta no piensa «mi distrito
 * esta en nivel alto», piensa «hay que tener cuidado esta semana».
 *
 * Pero dos vocabularios sueltos para lo mismo serian justo la incoherencia que
 * hay que evitar. Por eso la pantalla muestra los dos juntos: la palabra grande
 * y el termino tecnico debajo, chiquito. Quien vive en el distrito lee el
 * primero; el Comite de Emergencias y quien evalua leen el segundo, y la
 * traduccion entre ambos queda a la vista en vez de escondida en el codigo.
 *
 * El mapa **no cambia**: ahi sigue diciendo «Alto». Es la vista tecnica, y
 * ademas su evidencia esta archivada y cerrada.
 */
export const NIVELES = {
  bajo: {
    palabra: 'tranquilo',
    tecnico: 'riesgo bajo',
    significado: 'Lo normal para la epoca del ano.',
  },
  medio: {
    palabra: 'atento',
    tecnico: 'riesgo medio',
    significado: 'Algo fuera de lo normal puede pasar. Fijate y avisa.',
  },
  alto: {
    palabra: 'cuidado',
    tecnico: 'riesgo alto',
    significado:
      'Es probable que pase algo que ya causo danos antes en tu distrito. Preparate y no te arriesgues.',
  },
}

/** Cuando el nivel es `alto` la tarjeta muestra la salida a lo oficial. */
export const NIVEL_QUE_EXIGE_SALIDA_OFICIAL = 'alto'

const LLUVIA = {
  bajo: {
    frase: (distrito) => `Esta semana no se espera lluvia fuera de lo normal en ${distrito}.`,
    hacer: ['Segui con tu semana normal.'],
  },
  medio: {
    frase: (distrito) => `Puede llover mas de lo normal en ${distrito}.`,
    hacer: ['Fijate en el camino antes de salir.', 'Avisa si ves el rio crecido.'],
  },
  alto: {
    frase: (distrito) =>
      `Puede llover fuerte en ${distrito}, del tipo de lluvia que ya ha cortado caminos antes.`,
    hacer: [
      'Revisa el camino antes de salir.',
      'Compra lo que necesites antes.',
      'Evita salir de noche.',
    ],
  },
}

const INCENDIO = {
  bajo: {
    frase: (distrito) =>
      `No se vieron focos de calor en ${distrito} en los ultimos siete dias.`,
    hacer: ['Igual, no quemes basura ni charral.'],
  },
  medio: {
    // Por el contrato este nivel no existe para incendio. Si llegara, la pantalla
    // no se inventa una frase: dice lo unico que puede sostener.
    frase: (distrito) => `Hay senales de calor en ${distrito} esta semana.`,
    hacer: ['No quemes basura ni charral.'],
  },
  alto: {
    frase: (distrito) =>
      `Se vio al menos un foco de calor en ${distrito} en los ultimos siete dias.`,
    hacer: ['No quemes basura ni charral.', 'Si ves humo, llama al 9-1-1.'],
  },
}

/**
 * Los tres eventos, con el nombre que se usa hablando y su nota de honestidad.
 *
 * `ausencia` se muestra cuando no hay nivel. Para la sequia es permanente y por
 * decision tomada, no por un fallo: se explica en una linea y sin jerga.
 */
export const TARJETAS = [
  {
    id: 'lluvia_intensa',
    titulo: 'Lluvia fuerte',
    porNivel: LLUVIA,
    ausencia:
      'Esta semana no alcanzo el dato para estimar la lluvia de tu distrito. Preferimos decirtelo.',
  },
  {
    id: 'incendio',
    titulo: 'Incendio',
    porNivel: INCENDIO,
    // Regla: nada de «tiempo real» salvo donde el dato lo sea, y aca no lo es
    // todavia. La ventana es de siete dias y se dice.
    nota: 'Un foco de calor es lo que ve el satelite. No es un incendio confirmado.',
    ausencia: 'Esta semana no alcanzo el dato para estimar el riesgo de incendio en tu distrito.',
  },
  {
    id: 'sequia',
    titulo: 'Sequia',
    porNivel: {},
    ausencia:
      'No la estimamos. En treinta y cinco anos hubo trece sequias registradas en Tilaran: no alcanzan para aprender de ellas, y preferimos decirtelo que inventar un color.',
  },
]

/**
 * La frase y las acciones de una tarjeta, o `null` si no hay nivel.
 *
 * Devolver `null` no es un fallo: es el caso de la sequia todos los dias, y es
 * lo que hace que la pantalla pueda decir que no sabe.
 */
export function contenidoDeTarjeta(tarjeta, nivel, nombreDistrito) {
  const plantilla = nivel ? tarjeta.porNivel[nivel] : null
  if (!plantilla) return null
  return {
    palabra: NIVELES[nivel].palabra,
    tecnico: NIVELES[nivel].tecnico,
    frase: plantilla.frase(nombreDistrito),
    hacer: plantilla.hacer,
  }
}

/** Fecha larga en espanol, sin siglas y sin depender de la configuracion regional. */
const MESES = [
  'enero',
  'febrero',
  'marzo',
  'abril',
  'mayo',
  'junio',
  'julio',
  'agosto',
  'setiembre',
  'octubre',
  'noviembre',
  'diciembre',
]

export function fechaEnPalabras(iso) {
  if (!iso) return null
  const [anio, mes, dia] = iso.split('-').map(Number)
  if (!anio || !mes || !dia) return null
  return `${dia} de ${MESES[mes - 1]} de ${anio}`
}
