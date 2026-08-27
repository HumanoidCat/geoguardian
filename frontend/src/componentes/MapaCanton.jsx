import { useEffect, useMemo } from 'react'
import { GeoJSON, MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import { CAPAS_BASE } from '../datos/capasBase'

/**
 * Mapa del canton de Tilaran con sus ocho distritos, coloreados por nivel de
 * riesgo del evento seleccionado y con capas conmutables.
 *
 * Historias H5.1, H5.3 y H5.2. Rubrica de Computacion Grafica, CG-4 y CG-1.
 *
 * Decisiones que conviene no deshacer sin pensarlo:
 *
 * 1. El encuadre se calcula a partir de la geometria recibida, no se escribe a
 *    mano. Esa decision se cobro sola el 24 de agosto: las geometrias eran
 *    cuadrados de marcador de posicion y pasaron a ser los limites reales del
 *    SNIT sin que este componente cambiara una linea. Con las coordenadas fijas
 *    en el codigo, ese dia el mapa habria apuntado al lugar equivocado y nadie
 *    sabria por que. Ver I-10.
 *
 * 2. El relleno se resuelve por clase de CSS y no por opciones de Leaflet. Un
 *    color plano cabe en una opcion; una trama diagonal no. Como la ausencia de
 *    dato se representa con trama, los dos casos tienen que resolverse por el
 *    mismo camino o el codigo se parte en dos.
 *
 * 3. Un distrito sin nivel NO se pinta con el color mas claro de la rampa. Va
 *    con la trama de ausencia de dato. La diferencia entre "riesgo bajo" y
 *    "nadie lo midio" es la que evita que el mapa afirme lo que no sabe.
 *
 * 4. La opacidad de la coropleta viaja como variable CSS al contenedor, no como
 *    opcion de cada poligono. Asi el valor por defecto sigue viviendo en
 *    tokens.css y el deslizador solo lo sobrescribe mientras se usa: la decision
 *    de diseno no se duplica en dos lugares.
 */

// Centro provisional mientras se calcula el encuadre real. Solo se ve durante
// el primer cuadro de render: AjustarEncuadre lo reemplaza de inmediato.
const CENTRO_PROVISIONAL = [10.47, -84.97]
const ZOOM_PROVISIONAL = 11

const CLASE_POR_NIVEL = {
  bajo: 'distrito-riesgo-bajo',
  medio: 'distrito-riesgo-medio',
  alto: 'distrito-riesgo-alto',
}

const NOMBRE_POR_NIVEL = {
  bajo: 'riesgo bajo',
  medio: 'riesgo medio',
  alto: 'riesgo alto',
}

/**
 * Ajusta la vista para que quepan todos los distritos, sea cual sea su
 * geometria. Es un componente y no una llamada suelta porque useMap solo existe
 * dentro del arbol de MapContainer.
 *
 * ---------------------------------------------------------------------------
 * POR QUE ADEMAS LE DA FORMA AL CONTENEDOR
 * ---------------------------------------------------------------------------
 *
 * `fitBounds` encaja el recuadro del canton dentro del contenedor ajustando por
 * la dimension que aprieta, y deja el sobrante en la otra. Si las dos formas no
 * se parecen, ese sobrante es enorme.
 *
 * Medido sobre las geometrias del SNIT: el canton mide 31,2 km de ancho por
 * 37,5 km de alto, o sea que es **mas alto que ancho**, relacion 0,83. El
 * contenedor era al reves: toda la columna del mapa menos el panel, contra un
 * alto de rejilla. En pantalla ancha daba una relacion cercana a 2,7.
 *
 * Resultado: el recuadro del canton ocupaba **el 26 % del area del mapa** y los
 * poligonos el 19 %. El resto era Liberia, Bagaces, Canas y el Pacifico. Lo
 * senalo el profesor al ver el sitio publicado.
 *
 * El arreglo no es mover el encuadre: es **darle al contenedor la forma del
 * canton**, calculada del mismo recuadro que ya se usa para encuadrar. No hay
 * ninguna coordenada escrita a mano, y si las geometrias cambiaran otra vez, la
 * forma se recalcula sola.
 *
 * El alto lleva tope en el CSS, atado al alto de la ventana: antes de esto el
 * mapa ya salia de la pantalla y habia que desplazarse para verlo entero.
 */
function AjustarEncuadre({ coleccion }) {
  const mapa = useMap()

  useEffect(() => {
    if (!coleccion) return

    const limites = L.geoJSON(coleccion).getBounds()
    if (!limites.isValid()) return

    // La relacion de aspecto se mide sobre el recuadro PROYECTADO y no sobre
    // grados. Un grado de longitud y uno de latitud no miden lo mismo, y a la
    // latitud de Tilaran la diferencia es de un 9 %: usar grados deformaria el
    // contenedor justo en la direccion que estamos tratando de corregir.
    const suroeste = L.CRS.EPSG3857.project(limites.getSouthWest())
    const noreste = L.CRS.EPSG3857.project(limites.getNorthEast())
    const anchoCanton = Math.abs(noreste.x - suroeste.x)
    const altoCanton = Math.abs(noreste.y - suroeste.y)
    if (!(anchoCanton > 0) || !(altoCanton > 0)) return

    const aspecto = anchoCanton / altoCanton
    mapa.getContainer().style.setProperty('--mapa-aspecto', String(aspecto))

    // El contenedor del mapa todavia esta creciendo cuando este efecto corre.
    // Leaflet mide el tamano que hay en ese instante, y si es mas chico que el
    // final elige un zoom demasiado abierto: se ve medio pais en lugar del
    // canton. Esperar un cuadro de render no alcanza, porque el alto lo termina
    // de resolver la rejilla de CSS despues.
    //
    // Por eso se observa el contenedor. Pero se encuadra UNA SOLA VEZ, en cuanto
    // el contenedor tiene un tamano utilizable, y despues se deja de observar.
    //
    // La version anterior reencuadraba en cada cambio de tamano, y eso tenia dos
    // problemas. El visible: prender una capa hace crecer la columna del panel,
    // el mapa cambia de alto y se reencuadraba en mal momento, quedando abierto
    // sobre media provincia. El de fondo, peor: el mapa le peleaba a la persona.
    // Si alguien hacia zoom sobre un distrito y prendia una capa, la vista se
    // reseteaba sola. Una vista que el usuario eligio no se pisa.
    // CUANDO se encuadra. Tres versiones fallaron antes de esta, y cada una
    // enseno cual era de verdad la condicion.
    //
    // 1. Encuadrar al montar: el contenedor todavia no tiene tamano y Leaflet
    //    elige un zoom para un mapa de 0 px.
    // 2. Encuadrar al primer tamano utilizable: el contenedor crece por pasos
    //    mientras la rejilla de CSS resuelve ancho y alto, y encuadrar en el
    //    primer paso que supere un minimo deja el canton diminuto. Se vio: media
    //    Centroamerica en pantalla.
    // 3. Encuadrar cuando el tamano deja de cambiar por un rato: mejor, pero el
    //    contenedor sigue creciendo despues de ese rato -las teselas cargan, el
    //    panel de al lado cambia de alto, la rejilla recalcula- y el encuadre
    //    queda ajustado a un tamano que ya no existe. Medido: el canton ocupaba
    //    el 52 % del mapa en vez del 88 % que el contenedor permitia.
    //
    // La condicion correcta no es de tiempo ni de tamano: **es de quien manda la
    // vista.** Mientras nadie haya tocado el mapa, la vista es nuestra y se
    // reencuadra cada vez que el contenedor cambia. En cuanto la persona
    // arrastra, hace zoom o usa el teclado, la vista pasa a ser suya y no se
    // vuelve a tocar.
    //
    // Eso conserva la leccion de H5.1 -una vista que el usuario eligio no se
    // pisa- que la version original resolvia encuadrando una sola vez, sin notar
    // que el problema no era encuadrar dos veces sino encuadrar DESPUES de que
    // alguien eligio.
    const ESPERA_MS = 120

    const contenedor = mapa.getContainer()
    let laVistaEsDelUsuario = false
    let observador = null
    let plazo = null

    const encuadrar = () => {
      if (laVistaEsDelUsuario) return

      const { clientWidth, clientHeight } = contenedor
      if (clientWidth < 50 || clientHeight < 50) return

      mapa.invalidateSize()
      // 16 px y no 32: el margen ya no hace falta para compensar la diferencia
      // de forma entre el contenedor y el canton, y cada pixel de margen es
      // area que el canton no ocupa.
      mapa.fitBounds(limites, { padding: [16, 16] })
    }

    const reencuadrarPronto = () => {
      if (laVistaEsDelUsuario) return
      clearTimeout(plazo)
      plazo = setTimeout(encuadrar, ESPERA_MS)
    }

    // Eventos del DOM y no de Leaflet: `zoomstart` y `movestart` los dispara
    // tambien nuestro propio `fitBounds`, asi que la primera vez que
    // encuadraramos nos declarariamos usuario a nosotros mismos.
    const cederLaVista = () => {
      laVistaEsDelUsuario = true
      clearTimeout(plazo)
      observador?.disconnect()
      contenedor.removeEventListener('pointerdown', cederLaVista)
      contenedor.removeEventListener('wheel', cederLaVista)
      contenedor.removeEventListener('keydown', cederLaVista)
    }

    contenedor.addEventListener('pointerdown', cederLaVista)
    contenedor.addEventListener('wheel', cederLaVista, { passive: true })
    contenedor.addEventListener('keydown', cederLaVista)

    observador = new ResizeObserver(reencuadrarPronto)
    observador.observe(contenedor)
    reencuadrarPronto()

    return () => {
      observador?.disconnect()
      clearTimeout(plazo)
      contenedor.removeEventListener('pointerdown', cederLaVista)
      contenedor.removeEventListener('wheel', cederLaVista)
      contenedor.removeEventListener('keydown', cederLaVista)
    }
  }, [coleccion, mapa])

  return null
}

/**
 * Etiquetas con el nombre de cada distrito.
 *
 * Se dibujan con divIcon y no con marcadores normales para no depender de
 * ninguna imagen: el icono por defecto de Leaflet se carga por URL y se rompe
 * en la construccion de produccion. Un texto en un div no tiene ese problema.
 *
 * El punto donde se coloca es el centro de la caja envolvente del poligono. Con
 * los cuadrados actuales coincide con el centro real; con las geometrias del
 * SNIT sera aproximado, suficiente para una etiqueta.
 */
function CapaEtiquetas({ coleccion }) {
  const mapa = useMap()

  useEffect(() => {
    if (!coleccion) return

    const grupo = L.layerGroup().addTo(mapa)

    for (const rasgo of coleccion.features) {
      const centro = L.geoJSON(rasgo).getBounds().getCenter()
      L.marker(centro, {
        interactive: false,
        keyboard: false,
        icon: L.divIcon({
          className: 'etiqueta-distrito',
          html: `<span>${rasgo.properties.nombre}</span>`,
          iconSize: null,
        }),
      }).addTo(grupo)
    }

    return () => {
      grupo.remove()
    }
  }, [coleccion, mapa])

  return null
}

export default function MapaCanton({
  coleccion,
  riesgos,
  seleccionado,
  alSeleccionar,
  capaBase,
  superpuestas,
  opacidad,
}) {
  const base = CAPAS_BASE.find((capa) => capa.id === capaBase) ?? CAPAS_BASE[0]

  // Firma de lo que se va a pintar: un distrito y su nivel, por cada distrito.
  //
  // La clave describe EL RESULTADO, no la intencion. La version anterior dependia
  // de `evento`, y eso producia un defecto silencioso: `evento` cambia en el
  // instante del clic, pero los riesgos llegan despues, al terminar el fetch.
  // La capa se recreaba de inmediato con los riesgos viejos, y cuando llegaban
  // los nuevos la clave ya no cambiaba, asi que nadie la volvia a recrear. El
  // mapa quedaba pintando el evento anterior mientras la leyenda mostraba el
  // correcto.
  //
  // Con la firma, la capa se recrea exactamente cuando cambia lo que hay que
  // dibujar. Y si dos eventos dieran los mismos niveles no se recrea, que es lo
  // correcto: el dibujo seria identico.
  const firmaRiesgos = useMemo(
    () =>
      Object.entries(riesgos ?? {})
        .sort(([unCodigo], [otroCodigo]) => unCodigo.localeCompare(otroCodigo))
        .map(([codigo, riesgo]) => `${codigo}:${riesgo?.nivel ?? 'sin'}`)
        .join(','),
    [riesgos],
  )

  const clave = useMemo(
    () => `${firmaRiesgos}|${seleccionado ?? 'ninguno'}|${coleccion?.features?.length ?? 0}`,
    [firmaRiesgos, seleccionado, coleccion],
  )

  const nivelDe = (codigo) => riesgos?.[codigo]?.nivel ?? null

  const estilo = (rasgo) => {
    const { codigo } = rasgo.properties
    const nivel = nivelDe(codigo)
    const clases = ['distrito', nivel ? CLASE_POR_NIVEL[nivel] : 'distrito-sin-dato']
    if (codigo === seleccionado) clases.push('distrito-seleccionado')
    return { className: clases.join(' ') }
  }

  const porCadaDistrito = (rasgo, capa) => {
    const { codigo, nombre } = rasgo.properties
    const nivel = nivelDe(codigo)
    const descripcion = nivel ? NOMBRE_POR_NIVEL[nivel] : 'sin estimacion'

    // El halo de la seleccion se dibuja por fuera del poligono, asi que el
    // vecino que se pinte despues lo tapa. Sin esto, un distrito seleccionado se
    // ve resaltado por los lados que dan al exterior del canton y plano por los
    // que dan a otro distrito, que se lee como un defecto de dibujo.
    if (codigo === seleccionado) capa.bringToFront()

    capa.bindTooltip(`${nombre} (${codigo}) · ${descripcion}`, { sticky: true })

    capa.on('click', () => alSeleccionar(codigo))
    capa.on('keydown', (evt) => {
      if (evt.originalEvent.key === 'Enter' || evt.originalEvent.key === ' ') {
        evt.originalEvent.preventDefault()
        alSeleccionar(codigo)
      }
    })

    // Accesible por teclado. Un mapa que solo responde al mouse deja fuera a
    // quien navega con tabulador. La etiqueta dice el nivel en palabras: el
    // color no llega a un lector de pantalla.
    const elemento = capa.getElement()
    if (elemento) {
      elemento.setAttribute('tabindex', '0')
      elemento.setAttribute('role', 'button')
      elemento.setAttribute('aria-label', `Distrito ${nombre}, codigo ${codigo}, ${descripcion}`)
    }
  }

  return (
    <div
      className="contenedor-mapa"
      // La opacidad se inyecta como variable CSS. tokens.css sigue siendo el
      // dueno del valor por defecto; esto solo lo sobrescribe.
      style={{ '--riesgo-opacidad': opacidad }}
    >
      {/* Trama de ausencia de dato. Va en el documento para que los poligonos de
          Leaflet puedan referenciarla con fill: url(#patron-sin-dato). */}
      <svg width="0" height="0" aria-hidden="true" style={{ position: 'absolute' }}>
        <defs>
          <pattern
            id="patron-sin-dato"
            patternUnits="userSpaceOnUse"
            width="8"
            height="8"
            patternTransform="rotate(45)"
          >
            <rect width="8" height="8" style={{ fill: 'var(--sin-dato-fondo)', opacity: 0.55 }} />
            <line
              x1="0"
              y1="0"
              x2="0"
              y2="8"
              style={{ stroke: 'var(--sin-dato-trama)', strokeWidth: 2 }}
            />
          </pattern>
        </defs>
      </svg>

      <MapContainer
        center={CENTRO_PROVISIONAL}
        zoom={ZOOM_PROVISIONAL}
        // Leaflet redondea el zoom a niveles enteros, y `fitBounds` redondea
        // hacia abajo para no cortar nada. Entre un nivel y el siguiente hay un
        // factor de 2, asi que en el peor caso el canton queda a la mitad de
        // escala y sobra margen por los cuatro lados: medido en la captura de
        // antes, ocupaba el 54 % del mapa en vez del 88 % que permitia el
        // contenedor.
        //
        // Con 0.1 el redondeo cuesta como mucho un 7 % de escala. No se pone 0
        // -zoom continuo- porque las teselas se sirven por nivel entero y a
        // escalas arbitrarias el texto del mapa base se ve borroso.
        zoomSnap={0.1}
        scrollWheelZoom
        className="mapa"
      >
        {base.url && (
          <TileLayer
            key={base.id}
            attribution={base.atribucion}
            url={base.url}
            maxZoom={base.zoomMaximo}
          />
        )}

        {coleccion && (
          <>
            {superpuestas.riesgo && (
              <GeoJSON key={clave} data={coleccion} style={estilo} onEachFeature={porCadaDistrito} />
            )}

            {superpuestas.limites && (
              <GeoJSON
                key={`limites-${clave}`}
                data={coleccion}
                style={{ className: 'distrito-limite' }}
                interactive={false}
              />
            )}

            {superpuestas.etiquetas && <CapaEtiquetas coleccion={coleccion} />}

            <AjustarEncuadre coleccion={coleccion} />
          </>
        )}
      </MapContainer>
    </div>
  )
}
