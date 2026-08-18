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
    umbral:
      'Precipitacion acumulada en 72 h. Alto por encima del percentil 99. Indices R95p y R99p del ETCCDI, adoptados por la OMM.',
  },
]

export function nombreDeEvento(id) {
  return EVENTOS.find((evento) => evento.id === id)?.nombre ?? null
}
