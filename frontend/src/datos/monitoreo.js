/**
 * La lectura del estado del sistema: que significa cada campo de `Salud`.
 *
 * Historia H12.2. Rubrica Troubleshoot.
 *
 * POR QUE ESTA SEPARADO DE LA VISTA
 *
 * Todo lo de aca son funciones puras sobre datos: no tocan React ni el DOM. Eso
 * permite comprobarlas sin navegador, que es la mitad de lo que CA-1, CA-3 y CA-4
 * piden. La vista queda con una sola responsabilidad: dibujar lo que estas
 * funciones deciden.
 *
 * LO QUE ESTE MODULO NO HACE, Y ES DELIBERADO
 *
 * No dice «todo bien». Devuelve, por cada campo, **que valor tiene y cual es el
 * esperado**; quien lee saca la conclusion. Un panel que resume el estado en un
 * semaforo verde es una fuente que informa sobre si misma, que es el patron de
 * I-25, I-39 e I-41 y lo que este panel existe para no repetir.
 */

import { ORIGEN_API } from './cliente'

/** Un dia en milisegundos. */
const DIA_MS = 86_400_000
const HORA_MS = 3_600_000

/**
 * Cuantas horas puede tener la ultima ingesta antes de que valga la pena mirarla.
 *
 * No es un umbral de fallo: es el punto donde la antiguedad deja de ser rutina.
 * La ingesta no corre sola todavia -no hay quien la dispare-, asi que un valor
 * viejo aca es lo normal hoy y el panel lo dice con esas palabras en vez de
 * pintarlo de rojo.
 */
export const HORAS_INGESTA_FRESCA = 48

/**
 * De donde vienen los datos y en que entorno se esta mirando.
 *
 * **Se deriva, no se escribe.** El sabotaje de CA-1 es apagar la API y comprobar
 * que esto cambia: si devolviera lo mismo en los dos casos estaria leyendo una
 * constante y no el estado.
 *
 * @param {{origen: string}|null} salud
 * @param {string} host  normalmente `window.location.hostname`
 */
export function describirEntorno(salud, host = '') {
  if (!salud) return null

  const porApi = salud.origen === ORIGEN_API
  const local = host === 'localhost' || host === '127.0.0.1' || host === '[::1]'
  const paginas = host.endsWith('github.io')

  if (porApi && local) {
    return {
      clave: 'local',
      nombre: 'Local',
      detalle: 'El visor habla con una API que corre en esta maquina.',
    }
  }

  if (porApi) {
    return {
      clave: 'publicado',
      nombre: 'Publicado',
      detalle: 'El visor habla con la API desplegada. Es el sitio que se ve en la defensa.',
    }
  }

  if (paginas) {
    return {
      clave: 'respaldo',
      nombre: 'Respaldo en GitHub Pages',
      detalle:
        'No hay API en este origen. El visor sirve el respaldo estatico, y sus datos son simulados.',
    }
  }

  return {
    clave: 'respaldo',
    nombre: 'Respaldo estatico',
    detalle:
      'La API no respondio y el visor cayo al respaldo. Lo que se ve no viene de la base de datos.',
  }
}

/**
 * La antiguedad de una fecha, en palabras.
 *
 * Una fecha sin su antiguedad no dice si el dato sigue vivo: `2026-09-13` obliga
 * a hacer la cuenta, «hace 3 dias» no. Es lo que pide CA-3.
 *
 * Devuelve `null` cuando no hay fecha, para que la vista **declare la ausencia**
 * en vez de inventar un cero o un guion (D-07).
 */
export function describirAntiguedad(fechaIso, ahora = new Date()) {
  if (!fechaIso) return null

  const fecha = new Date(fechaIso)
  if (Number.isNaN(fecha.getTime())) return null

  const ms = ahora.getTime() - fecha.getTime()
  if (ms < 0) {
    // Una fecha futura no es un dato viejo: es un reloj desalineado, y decirlo
    // sirve mas que mostrar «hace -2 horas».
    return { texto: 'con fecha futura', horas: 0, fresca: false, anomala: true }
  }

  const horas = ms / HORA_MS
  const dias = Math.floor(ms / DIA_MS)

  let texto
  if (horas < 1) texto = 'hace menos de una hora'
  else if (horas < 24) texto = `hace ${Math.floor(horas)} h`
  else if (dias === 1) texto = 'hace 1 dia'
  else texto = `hace ${dias} dias`

  return { texto, horas, fresca: horas <= HORAS_INGESTA_FRESCA, anomala: false }
}

/**
 * Contrasta lo que la API dice ser contra lo que el arbol construido esperaba.
 *
 * ES LA UNICA COMPROBACION QUE ACOTA LO QUE D-43 ACEPTA.
 *
 * D-43 decide que el sitio publico se construye desde el repositorio y no desde
 * las imagenes que el CI probo, y **lo escribe sin disimularlo**: «el binario que
 * corre en el sitio publico no es el que el CI construyo y probo». La perdida se
 * acota comparando versiones: si no coinciden, se desplego otro arbol, que es el
 * error que importa.
 *
 * `esperado` sale de `frontend/public/estado/esperado.json`, que genera
 * `frontend/herramientas/generar_esperado.py` leyendo `contratos/__init__.py`.
 * **No hay ninguna version escrita a mano en el visor**: ese era el defecto de
 * I-41 y no se repite aca.
 */
export function contrastarVersiones(salud, esperado) {
  if (!salud) return null

  if (!esperado?.version_contratos) {
    return {
      estado: 'sin_referencia',
      declarada: salud.version_contratos ?? null,
      esperada: null,
      texto:
        'No hay con que comparar: falta estado/esperado.json. Se genera con ' +
        'python frontend/herramientas/generar_esperado.py',
    }
  }

  const declarada = salud.version_contratos ?? null
  const esperada = esperado.version_contratos

  if (!declarada) {
    return {
      estado: 'sin_dato',
      declarada: null,
      esperada,
      texto: `La API no declaro su version de contratos. El arbol construido esperaba ${esperada}.`,
    }
  }

  if (declarada === esperada) {
    return {
      estado: 'coincide',
      declarada,
      esperada,
      texto: `Coincide con el arbol construido (${esperada}).`,
    }
  }

  return {
    estado: 'difiere',
    declarada,
    esperada,
    texto:
      `La API declara ${declarada} y el arbol construido esperaba ${esperada}. ` +
      'Se desplego un arbol distinto del que sirvio para construir este visor.',
  }
}

/**
 * Los cinco campos de `Salud`, cada uno con su lectura.
 *
 * La columna «que significa si no» sale de la seccion 2 de
 * `docs/20-manual-de-operacion.md`, y no se reescribe aca: **este panel automatiza
 * esa comprobacion, no inventa otra**. Si el manual cambia, esto tiene que
 * cambiar con el.
 */
export function leerCampos(salud, esperado, ahora = new Date()) {
  if (!salud) return []

  const antiguedad = describirAntiguedad(salud.ultima_ingesta, ahora)
  const versiones = contrastarVersiones(salud, esperado)
  const real = salud.modo === 'real'

  return [
    {
      clave: 'modo',
      etiqueta: 'modo',
      valor: salud.modo ?? null,
      esperado: 'real',
      bien: real,
      lectura: real
        ? 'La API esta sirviendo desde PostgreSQL.'
        : 'La API no llego a PostgreSQL y esta sirviendo el repositorio de relleno. ' +
          'No hay variable que forzar: hay una conexion que arreglar.',
    },
    {
      clave: 'base_datos_conectada',
      etiqueta: 'base_datos_conectada',
      valor: salud.base_datos_conectada === null ? null : String(salud.base_datos_conectada),
      // Lo esperado depende del modo, y por eso no es la cadena 'true' a secas:
      // en modo simulado, `false` es la respuesta correcta.
      esperado: real ? 'true' : 'false, con modo simulado',
      // No se marca cuando coincide con lo que el modo implica. Marcar una fila
      // que el propio panel declara coherente seria decir dos cosas distintas
      // sobre el mismo campo: una en el texto y otra en el color.
      bien: real ? salud.base_datos_conectada === true : salud.base_datos_conectada === false,
      lectura:
        salud.base_datos_conectada === true
          ? 'La conexion responde.'
          : real
            ? 'Contradice a modo: dos preguntas al mismo proceso dan respuestas incompatibles. ' +
              'Desde I-41 los dos se derivan, asi que ya no puede ser un valor viejo.'
            : 'Coherente con modo simulado.',
    },
    {
      clave: 'ultima_ingesta',
      etiqueta: 'ultima_ingesta',
      valor: salud.ultima_ingesta ?? null,
      esperado: `una fecha de menos de ${HORAS_INGESTA_FRESCA} h`,
      bien: Boolean(antiguedad?.fresca),
      ausente: antiguedad === null,
      lectura:
        antiguedad === null
          ? 'Nunca se ejecuto la ingesta, o la API no pudo leerlo. No se muestra una fecha ' +
            'en su lugar.'
          : antiguedad.anomala
            ? 'La fecha esta en el futuro. No es un dato viejo: es un reloj desalineado.'
            : `${antiguedad.texto}. La ingesta no corre sola todavia, asi que una fecha vieja ` +
              'aca es lo normal hoy.',
      antiguedad,
    },
    {
      clave: 'version_contratos',
      etiqueta: 'version_contratos',
      valor: salud.version_contratos ?? null,
      esperado: versiones?.esperada ?? 'sin referencia',
      bien: versiones?.estado === 'coincide',
      lectura: versiones?.texto ?? '',
    },
    {
      clave: 'version_api',
      etiqueta: 'version_api',
      valor: salud.version_api ?? null,
      esperado: 'acompana a la de contratos',
      bien: Boolean(salud.version_api),
      lectura: salud.version_api
        ? 'Sirve para saber que arbol esta desplegado, junto con la de contratos.'
        : 'La API no declaro su version.',
    },
  ]
}

/**
 * Lo que este panel NO vigila, dicho en la pantalla.
 *
 * CA-5. Un panel de monitoreo que calla lo que no mira es el defecto de I-25,
 * I-39 e I-41 otra vez. No se muestra un recuadro vacio ni un «proximamente»: se
 * nombra el hueco y de que depende cerrarlo.
 */
export const LO_QUE_NO_SE_VIGILA = [
  {
    que: 'Las corridas de CI y CD',
    porque:
      'La API no expone control.bitacora_etl, y pedirselo a api.github.com desde el ' +
      'navegador seria una peticion a otro dominio, que rompe D-23 y el CA-3 de H11.6.',
    depende: 'La parte 2 de H12.2, especificada en sus criterios de aceptacion.',
  },
  {
    que: 'El dominio, de forma automatica',
    porque:
      'Esta pantalla muestra; no avisa. Las alertas de H12.3 escuchan corridas de ' +
      'GitHub Actions, no el dominio: un CI en verde con el visor caido no dispara nada.',
    depende: 'Sigue haciendo falta que alguien abra esta pantalla. Reduce el costo de mirar, no lo elimina.',
  },
]
