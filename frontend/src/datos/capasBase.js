/**
 * Capas base del visor. Son excluyentes entre si: solo una se ve a la vez.
 *
 * Ninguna es relleno para llegar a un numero de capas. Cada una responde a un
 * uso concreto:
 *
 *   - OpenStreetMap da contexto general. Es la que sirve para ubicarse: caminos,
 *     poblados, rios, nombres de lugar.
 *
 *   - OpenTopoMap muestra relieve y curvas de nivel. La pendiente y la elevacion
 *     gobiernan tanto la propagacion del fuego como la retencion de humedad en
 *     el suelo, asi que es la capa que permite entender por que dos distritos
 *     vecinos se comportan distinto.
 *
 *   - Sin capa base deja el fondo neutro. Es la que se usa para imprimir: en el
 *     cartel academico y en las capturas del documento IEEE las teselas ensucian
 *     y compiten con la escala de riesgo.
 *
 * Las dos fuentes de teselas son gratuitas y no requieren clave. La condicion de
 * uso es mantener visible la atribucion, que se declara en cada una.
 */

export const CAPAS_BASE = [
  {
    id: 'osm',
    nombre: 'OpenStreetMap',
    descripcion: 'Caminos, poblados y rios',
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    atribucion:
      '&copy; colaboradores de <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    zoomMaximo: 19,
  },
  {
    id: 'topo',
    nombre: 'Relieve',
    descripcion: 'Curvas de nivel y elevacion',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    atribucion:
      'Mapa: &copy; colaboradores de <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>, SRTM | ' +
      'Estilo: &copy; <a href="https://opentopomap.org/">OpenTopoMap</a> (CC-BY-SA)',
    zoomMaximo: 17,
  },
  {
    id: 'ninguna',
    nombre: 'Sin capa base',
    descripcion: 'Fondo neutro, para imprimir',
    url: null,
    atribucion: null,
    zoomMaximo: 19,
  },
]

export const CAPA_BASE_INICIAL = 'osm'

/**
 * Capas superpuestas. Son independientes: cada una se enciende y se apaga sola.
 */
export const CAPAS_SUPERPUESTAS = [
  {
    id: 'riesgo',
    nombre: 'Riesgo por distrito',
    descripcion: 'Coropleta con la escala de tres niveles',
    conOpacidad: true,
  },
  // El mapa de calor se retiro el 2026-08-26 por D-28. Interpolar por distancia
  // inversa entre los centroides de ocho poligonos produce valores donde no hay
  // ninguna medicion: el riesgo se estima POR DISTRITO, un valor por poligono, y
  // un degradado continuo comunica una resolucion espacial que el dato no tiene.
  //
  // Es el mismo criterio por el que I-05 y D-15 descartaron a NASA POWER para
  // precipitacion: si su celda no permitia hablar por distrito, un mapa de calor
  // que sugiere variacion DENTRO del distrito afirma todavia mas.
  //
  // No se arreglo ni se etiqueto, se quito: el problema no era que faltara el
  // aviso, era que se mostraba. H5.4 queda cerrada, con nota de revision.
  {
    id: 'limites',
    nombre: 'Limites distritales',
    descripcion: 'Solo el contorno, sin relleno',
    conOpacidad: false,
  },
  {
    id: 'etiquetas',
    nombre: 'Nombres de distrito',
    descripcion: 'Etiqueta sobre cada poligono',
    conOpacidad: false,
  },
]

export const CAPAS_INICIALES = {
  riesgo: true,
  limites: false,
  etiquetas: false,
}

// Las constantes del exponente de la interpolacion salieron con la capa, por
// D-28. No quedan sin uso: una constante exportada que nadie consume es una
// invitacion a reconstruir lo que se acaba de decidir retirar.
