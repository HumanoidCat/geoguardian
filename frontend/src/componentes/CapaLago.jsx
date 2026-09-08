import { useEffect, useState } from 'react'
import { GeoJSON, useMap } from 'react-leaflet'
import L from 'leaflet'
import { anclaDeEtiqueta } from '../datos/anclaEtiqueta'
import { obtenerLago, RUTA_LAGO } from '../datos/lago'

/**
 * El Lago Arenal, dibujado como agua sobre la coropleta.
 *
 * Historia H14.3. Rubrica de Computacion Grafica, CG-1.
 *
 * POR QUE EXISTE ESTA CAPA
 *
 * Los limites distritales del SNIT incluyen el espejo de agua: 88 km2 del
 * embalse caen dentro del canton. **Medido el 2026-09-08 con 122 puntos dentro
 * del agua: 109 caen sobre Tilaran, uno sobre Arenal, uno sobre Tronadora y 11
 * fuera del canton** -la parte del embalse que es de San Carlos-. O sea que el
 * distrito mas afectado es Tilaran, no los dos que llevan el lago en el nombre.
 * Sin esta capa la coropleta pinta
 * el lago con el nivel de riesgo del distrito, y el visor termina diciendo que
 * el agua tiene riesgo alto de lluvia intensa.
 *
 * SE DIBUJA ENCIMA; NO SE RECORTA EL DISTRITO
 *
 * Restarle el lago a la geometria de los distritos cambiaria el limite
 * oficial y rompería la suma de verificacion de H1.3. Seria I-14 otra vez:
 * darle al mapa una forma que la fuente no dice. El limite se queda como el
 * SNIT lo publica y el agua va encima.
 *
 * Y "encima" TIENE QUE SER UN PANEL PROPIO, NO EL ORDEN DE MONTAJE.
 *
 * Todas las capas vectoriales de Leaflet comparten un solo <svg> en
 * `overlayPane`, y ahi el que se dibuja ultimo es el que queda arriba. Como
 * esta capa pide su geometria con `fetch`, el orden depende de si la respuesta
 * llego antes o despues de que se pintaran los ocho distritos: en una recarga
 * en frio el lago quedaba de ultimo -bien- y con el archivo en cache quedaba
 * de primero, o sea DEBAJO de la coropleta. Se veia solo el pedazo del embalse
 * que cae fuera del canton, del lado de San Carlos, y el resto del lago
 * desaparecia bajo el color de riesgo. Medido el 2026-09-08: `lagoIndex 0` de
 * 9 caminos en el SVG.
 *
 * Por eso el agua va en su propio panel con `zIndex` fijo (450): encima de
 * `overlayPane` (400, las coropletas) y debajo de `markerPane` (600, los focos
 * de calor). El orden deja de depender de la red.
 *
 * NO ES INTERACTIVA, Y ESO ES UN CRITERIO
 *
 * `interactive={false}` deja pasar el clic al distrito de abajo y mantiene la
 * capa fuera del recorrido de tabulacion. Un lago que se pueda seleccionar
 * competiria con los ocho distritos, que son el dato.
 *
 * SI NO CARGA, EL MAPA SIGUE
 *
 * Es contexto geografico, no el dato principal: un fallo al traer el archivo
 * se registra y no se propaga. La procedencia de la geometria esta en
 * `public/geo/procedencia-lago-arenal.md`.
 */


/** Panel propio para el agua. 400 es `overlayPane` y 600 es `markerPane`. */
const PANEL = 'agua'
const PANEL_Z = 450

// LA ORILLA SON DOS TRAZOS, Y ESO NO ES ADORNO
//
// Bajo protanopia el rojo de 'alto' se ve casi negro y 'bajo' sigue siendo
// amarillo palido: entre esos dos fondos hay 6,0:1, asi que un unico color de
// borde necesitaria 9:1 para llegar a 3:1 contra los dos. Se busco en el cubo
// sRGB completo y no existe. La solucion es la misma que ya usa la marca del
// distrito seleccionado: un par, donde basta que una de las dos partes cumpla
// en cada fondo. Peor caso de los 16 pares: 4,04:1, medido en
// `verificar_escala.py`.
//
// El halo va debajo y lleva el relleno; la linea va encima y no rellena, para
// no taparlo. Los dos son hermanos del mismo render, sin `fetch` en medio, asi
// que su orden entre si es el del JSX y no depende de la red -que es justo lo
// que si pasaba entre esta capa y los distritos-.
//
// Los colores viven en `tokens.css`; Leaflet no lee variables CSS en las
// opciones de estilo, asi que las clases hacen el trabajo y los hex de aca son
// solo el respaldo por si la hoja no cargo.

const ESTILO_HALO = {
  className: 'lago-halo',
  color: '#f5fbfd',
  weight: 3.4,
  fillColor: '#aad3df',
  fillOpacity: 1,
}

const ESTILO = {
  className: 'lago',
  color: '#08202d',
  weight: 1.2,
  fill: false,
}

/**
 * El nombre del lago sobre el agua.
 *
 * CA-4: el lago lleva su nombre en el mapa y nada mas. No entra en la leyenda ni
 * lleva la trama de ausencia de D-07, porque el agua no es un dato que falte.
 * Va en `markerPane` -600-, igual que las etiquetas de distrito, o sea encima
 * del agua y de la coropleta, y no es interactiva ni tabulable.
 *
 * El punto sale de `anclaDeEtiqueta`, que busca el tramo de agua abierta mas
 * ancho: el centro de la caja envolvente caeria en tierra, porque el embalse es
 * un arco curvo.
 */
function EtiquetaLago({ geometria }) {
  const mapa = useMap()

  useEffect(() => {
    const ancla = anclaDeEtiqueta(geometria)
    if (!ancla) return undefined

    const marca = L.marker(ancla, {
      interactive: false,
      keyboard: false,
      icon: L.divIcon({
        className: 'etiqueta-lago',
        html: '<span>Lago Arenal</span>',
        iconSize: null,
      }),
    }).addTo(mapa)

    return () => {
      marca.remove()
    }
  }, [geometria, mapa])

  return null
}

export default function CapaLago() {
  const mapa = useMap()
  const [geometria, setGeometria] = useState(null)

  // El panel se crea antes de que haya geometria que dibujar, porque Leaflet
  // exige que exista cuando se instancia la capa.
  useEffect(() => {
    if (mapa.getPane(PANEL)) return
    const panel = mapa.createPane(PANEL)
    panel.style.zIndex = String(PANEL_Z)
    panel.style.pointerEvents = 'none'
  }, [mapa])

  useEffect(() => {
    let vigente = true
    obtenerLago()
      .then((datos) => {
        if (vigente) setGeometria(datos)
      })
      .catch((causa) => {
        // Deliberado: el mapa se dibuja igual sin el lago.
        console.warn(`No se pudo cargar el Lago Arenal desde ${RUTA_LAGO}:`, causa.message)
      })
    return () => {
      vigente = false
    }
  }, [])

  if (!geometria) return null
  return (
    <>
      <GeoJSON data={geometria} style={ESTILO_HALO} interactive={false} pane={PANEL} />
      <GeoJSON data={geometria} style={ESTILO} interactive={false} pane={PANEL} />
      <EtiquetaLago geometria={geometria} />
    </>
  )
}
