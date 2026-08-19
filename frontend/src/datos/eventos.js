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
  },
  {
    id: 'incendio',
    nombre: 'Incendio forestal',
    umbral:
      'Focos de calor FIRMS en ventana de 7 dias. Alto por encima del percentil 90 historico del distrito. No hay estandar internacional: es criterio del equipo, pendiente de validar con los actores locales.',
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

export function nombreDeEvento(id) {
  return EVENTOS.find((evento) => evento.id === id)?.nombre ?? null
}
