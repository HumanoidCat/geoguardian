import { ImageOverlay } from 'react-leaflet'

/**
 * Un indice de vegetacion o humedad, superpuesto como imagen. Historia H5.5.
 *
 * ---------------------------------------------------------------------------
 * POR QUE UNA IMAGEN Y NO UNA COROPLETA
 * ---------------------------------------------------------------------------
 *
 * Cada pixel es una **medicion de 20 m del satelite**. Promediarlo por distrito
 * -que es como el visor pinta todo lo demas- tiraria casi toda la informacion
 * para parecerse al resto del sistema.
 *
 * Es lo contrario de los dos casos en que el proyecto dijo que no:
 *
 *   D-28/D-30  el mapa de calor interpolaba entre ocho centroides, o sea
 *              inventaba valores donde no habia medicion
 *   I-05       NASA POWER metia los ocho distritos en la misma celda, o sea el
 *              dato no distinguia entre ellos
 *
 * Aca hay medicion y hay resolucion. Decidido con el PM el 2026-09-03.
 *
 * ---------------------------------------------------------------------------
 * LO QUE ESTA CAPA **NO** ES, Y POR QUE LA LEYENDA IMPORTA TANTO
 * ---------------------------------------------------------------------------
 *
 * No es una estimacion de riesgo. Es lo que el satelite vio **un dia concreto**,
 * el de la escena, que no tiene por que ser la fecha elegida en el selector.
 *
 * Por eso arranca apagada y por eso `LeyendaIndice` escribe la fecha de la
 * escena en pantalla. Una capa de 20 m junto a una coropleta distrital puede
 * sugerir una precision que las estimaciones no tienen, y esa confusion se paga
 * en la leyenda, no quitando el detalle del dato.
 */
export default function CapaIndice({ id, paquete, opacidad }) {
  const indice = paquete?.indices?.[id]
  if (!indice || !paquete?.limites) return null

  // Los limites son del paquete y no de cada indice: los dos PNG se generan
  // sobre la misma rejilla, asi que compartirlos evita que puedan discrepar.
  const { limites } = paquete
  const esquinas = [
    [limites.sur, limites.oeste],
    [limites.norte, limites.este],
  ]

  return (
    <ImageOverlay
      url={`${import.meta.env.BASE_URL}${indice.archivo}`}
      bounds={esquinas}
      opacity={opacidad}
      // ENCIMA DE LA COROPLETA, Y ES DELIBERADO.
      //
      // La primera version la ponia debajo, razonando que el indice es contexto
      // y el riesgo es el dato principal. Ese razonamiento ya se probo y falla:
      // es exactamente lo que le pasa al mapa de calor, que se dibuja debajo de
      // una coropleta al 85 % de opacidad y **queda invisible aunque este
      // encendido**. El profesor lo señalo el 2026-08-27 -«mapa de calor debe
      // quedar arriba del riesgo»- y sigue sin corregirse.
      //
      // Una capa que se enciende y no se ve es peor que no tenerla: quien la
      // prende cree que hizo algo mal. Va arriba, y el equilibrio con la
      // coropleta se resuelve con el deslizador de opacidad, que esta capa
      // declara en `CAPAS_SUPERPUESTAS`.
      zIndex={500}
    />
  )
}
