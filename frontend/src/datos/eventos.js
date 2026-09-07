/**
 * Los tres eventos que el sistema estima, con el umbral que define su nivel.
 *
 * Salen del contrato, contratos/enums.py. El vocabulario esta cerrado: esta
 * lista no se amplia sin cambiar el contrato primero.
 *
 * Los umbrales acompanan a cada evento a proposito. Quien lee el mapa tiene que
 * poder saber que significa "alto" sin salir de la pantalla, y de donde sale ese
 * corte. Ninguno lo definio el equipo salvo el de incendio, que se declara como
 * criterio propio.
 *
 * Vive en su propio archivo y no dentro del componente para que la recarga en
 * caliente de Vite siga funcionando: un archivo que exporta componentes no debe
 * exportar tambien constantes.
 */

export const EVENTOS = [
  {
    id: 'sequia',
    nombre: 'Sequia',
    umbral:
      'Indice SPI-3. Alto si el SPI es menor o igual a -1.5. Cortes de McKee et al. (1993), adoptados por la OMM.',
    // Por que la sequia nunca trae nivel, dicho en la pantalla y no solo en la
    // bitacora. D-34 (2026-09-01): contados a nivel canton, hay 13 episodios de
    // sequia en toda la serie y el pliegue mas pobre entrena con 2; ningun
    // modelo ni linea base supera el piso trivial, asi que nadie escribe
    // analitico.riesgo para sequia. Un distrito en trama sin esta frase se lee
    // como un fallo del sistema; con ella, como lo que es: un resultado.
    ausencia:
      'La sequia no se estima: en toda la serie historica hubo 13 episodios en el canton, muy pocos para entrenar o validar un modelo (D-34). Se muestra sin nivel a proposito.',
  },
  {
    id: 'incendio',
    nombre: 'Incendio forestal',
    // El umbral anterior era por percentiles del conteo: bajo si 0, medio si
    // 1 <= n <= P90, alto si n > P90. Se retiro por SC-05 y D-25 al medirlo: con
    // 242 focos en 24 anios, el P90 vale 0,0 en los ocho distritos, asi que la
    // condicion del nivel medio —entre 1 y 0— estaba vacia. No producia tres
    // clases, producia dos, y fallaba asi desde el primer dia.
    //
    // El alcance queda acotado a Santa Rosa, Libano y Tierras Morenas, que
    // concentran 213 de los 242 focos. Arenal y Cabeceras tienen un foco en
    // veinticuatro anios y se reportan como sin datos suficientes.
    umbral:
      'Focos de calor FIRMS en ventana de 7 dias. Alto si hay al menos un foco; bajo si no hay ninguno. El nivel medio no existe para este evento. No hay estandar internacional: es criterio del equipo, pendiente de validar con los actores locales.',
  },
  {
    id: 'lluvia_intensa',
    nombre: 'Lluvia intensa',
    // La version anterior citaba los indices R95p y R99p del ETCCDI. Estaba mal
    // atribuida: el R95p se calcula sobre la precipitacion diaria de los dias
    // humedos, y nuestro corte sobre el acumulado de 72 h. Medidos sobre 30
    // anios, el umbral diario del ETCCDI declararia riesgo alto 934 dias contra
    // los 110 del acumulado: ocho veces y media mas. El umbral no cambia, cambia
    // como se nombra. Ver D-08 y la medicion de H2.7.
    umbral:
      'Precipitacion acumulada en 72 h por distrito. Alto por encima del percentil 99 de su propia serie historica, periodo base 1991-2020. El corte sigue el criterio de percentiles extremos del ETCCDI, pero no es el indice R95p, que se define sobre lluvia diaria.',
  },
]

/**
 * Version corta del umbral, para donde no cabe el texto completo.
 *
 * La larga sigue estando disponible en `umbral` y se muestra al pasar el cursor.
 * Acortar no es esconder: el corte tiene que estar a la vista aunque sea
 * abreviado, porque es lo que permite entender que significa "alto".
 */
export const UMBRAL_CORTO = {
  sequia: 'Alto: SPI-3 ≤ -1.5',
  incendio: 'Alto: al menos 1 foco en 7 dias',
  lluvia_intensa: 'Alto: acumulado 72 h > P99',
}

export function nombreDeEvento(id) {
  return EVENTOS.find((evento) => evento.id === id)?.nombre ?? null
}

export const IDS_EVENTOS = EVENTOS.map((evento) => evento.id)
