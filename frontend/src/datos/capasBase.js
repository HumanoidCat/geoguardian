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
  {
    id: 'mapaCalor',
    nombre: 'Mapa de calor',
    descripcion: 'Probabilidad interpolada entre los ocho distritos',
    conOpacidad: false,
    conExponente: true,
  },
  {
    id: 'ndvi',
    nombre: 'Vegetacion (NDVI)',
    descripcion: 'Indice por pixel de 20 m, de una fecha concreta',
    conOpacidad: true,
  },
  {
    id: 'ndwi',
    nombre: 'Humedad y agua (NDWI)',
    descripcion: 'Indice por pixel de 20 m, de una fecha concreta',
    conOpacidad: true,
  },
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
  mapaCalor: false,
  // Los indices arrancan apagados a proposito. Son de **una fecha concreta** -la
  // de la escena de satelite- y el resto del visor muestra la fecha que se pide
  // en el selector. Encendidos por omision, el mapa mezclaria dos fechas sin
  // que nadie lo notara.
  ndvi: false,
  ndwi: false,
  limites: false,
  etiquetas: false,
}

/**
 * Exponente de la interpolacion por distancia inversa.
 *
 * Decide cuanto pesa la cercania. Con 1 la superficie queda casi plana, un
 * promedio general del canton. Con 4 cada distrito domina su entorno y aparecen
 * "islas" con bordes marcados, que es engañoso porque sugiere una frontera que
 * el dato no tiene.
 *
 * 2 es el valor convencional y el que se usa por defecto. Se deja ajustable
 * porque la eleccion del exponente cambia la lectura del mapa, y esconderla
 * seria presentar una decision como si fuera un hecho.
 */
export const EXPONENTE_IDW_INICIAL = 2
export const EXPONENTE_IDW_MINIMO = 1
export const EXPONENTE_IDW_MAXIMO = 4
