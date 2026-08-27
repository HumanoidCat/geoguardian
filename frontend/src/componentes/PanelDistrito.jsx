/**
 * Ficha del distrito seleccionado.
 *
 * Regla que atraviesa este componente: lo que no se sabe se dice, no se
 * rellena. Un guion o un cero en lugar de "sin dato" convierte una ausencia en
 * una afirmacion.
 *
 * Cuando hay nivel de riesgo, la ficha muestra tambien de que modelo salio. Con
 * el simulado esa version es "simulado-0.0.0", que es la tercera vez que el
 * visor declara que el dato no es real: la banda de arriba, el aviso de la
 * leyenda y esta linea.
 */
import { CRTM05, aCRTM05, formatearCRTM05, formatearGrados } from '../datos/proyeccion'

const NOMBRE_POR_NIVEL = {
  bajo: 'Bajo',
  medio: 'Medio',
  alto: 'Alto',
}

function Dato({ etiqueta, valor, unidad, ausente }) {
  return (
    <div className="dato">
      <dt>{etiqueta}</dt>
      <dd>
        {valor === null || valor === undefined ? (
          <span className="valor-ausente">{ausente ?? 'Sin dato'}</span>
        ) : (
          <>
            {valor}
            {unidad ? <span className="unidad"> {unidad}</span> : null}
          </>
        )}
      </dd>
    </div>
  )
}

/**
 * Las dos coordenadas del mismo punto.
 *
 * Se muestran juntas y no una u otra: los grados sirven para pegar en un mapa
 * web, y los metros de CRTM05 para **decirlos**, que es para lo que existe H5.6.
 * Quien pasa una posicion por radio no dicta grados decimales.
 *
 * Si no hay punto no se dibuja nada. Una coordenada dudosa rotulada como la
 * ubicacion del distrito es peor que la ausencia.
 */
function BloqueUbicacion({ titulo, punto }) {
  if (!punto) return null

  return (
    <div className="panel-ubicacion">
      <h3 className="panel-ubicacion-titulo">{titulo}</h3>
      <p className="panel-ubicacion-reticula">
        {formatearCRTM05(aCRTM05(punto.longitud, punto.latitud))}
      </p>
      <p className="panel-ubicacion-grados">
        {formatearGrados(punto.longitud, punto.latitud)}
      </p>
    </div>
  )
}

function BloqueRiesgo({ riesgo, nombreEvento }) {
  const nivel = riesgo?.nivel ?? null

  if (!nivel) {
    return (
      <div className="panel-estimacion">
        <span className="cuadro-leyenda trama-sin-dato cuadro-sin-dato" aria-hidden="true" />
        <div>
          <p className="panel-estimacion-titulo">Sin estimacion de riesgo</p>
          <p className="panel-estimacion-detalle">
            No hay nivel calculado para este distrito. No es un riesgo bajo: es
            la ausencia de una medicion.
          </p>
        </div>
      </div>
    )
  }

  const probabilidad =
    riesgo.probabilidad === null || riesgo.probabilidad === undefined
      ? null
      : `${Math.round(riesgo.probabilidad * 100)} %`

  return (
    <div className="panel-estimacion">
      <span className={`cuadro-leyenda cuadro-riesgo-${nivel}`} aria-hidden="true" />
      <div>
        <p className="panel-estimacion-titulo">
          Riesgo {NOMBRE_POR_NIVEL[nivel].toLowerCase()} de {nombreEvento?.toLowerCase()}
        </p>
        <dl className="panel-riesgo-datos">
          <Dato etiqueta="Probabilidad" valor={probabilidad} ausente="No calculada" />
          <Dato etiqueta="Modelo" valor={riesgo.version_modelo} ausente="Sin modelo" />
        </dl>
      </div>
    </div>
  )
}

export default function PanelDistrito({ distrito, riesgo, nombreEvento, ubicacion, puntoClic }) {
  if (!distrito) {
    return (
      <aside className="panel">
        <p className="panel-vacio">Hace clic en un distrito del mapa para ver su ficha.</p>
      </aside>
    )
  }

  const { codigo, nombre, area_km2: area, poblacion, geometria_simulada: simulada } = distrito


  return (
    <aside className="panel">
      <h2 className="panel-titulo">{nombre}</h2>
      <p className="panel-codigo">Codigo {codigo}</p>

      <dl className="panel-datos">
        <Dato etiqueta="Area" valor={area} unidad="km2" />
        <Dato etiqueta="Poblacion" valor={poblacion} ausente="Sin dato censal" />
      </dl>

      {/* El sistema se nombra una sola vez, no en cada bloque: repetirlo dos
          veces sugiere que podrian ser distintos. */}
      <p className="panel-ubicacion-sistema">
        Coordenadas en {CRTM05.nombre}, EPSG:{CRTM05.epsg}
      </p>
      <BloqueUbicacion titulo="Ubicacion del distrito" punto={ubicacion} />
      <BloqueUbicacion titulo="Donde hiciste clic" punto={puntoClic} />

      <BloqueRiesgo riesgo={riesgo} nombreEvento={nombreEvento} />

      {/* Desde el 24 de agosto la geometria es la real del SNIT y esta nota no
          se muestra nunca: `verificar_h115.py` no deja publicar un dist con
          `geometria_simulada` en true.

          No se borra igual. Es la red debajo del verificador: si algun dia
          vuelve a entrar geometria de relleno, la pantalla lo dice. Fue el
          defecto I-10, donde el dato traia su propia confesion escrita y el
          problema era que nadie la leia. */}
      {simulada && (
        <p className="panel-nota">
          La forma de este distrito es aproximada y no corresponde a su limite
          oficial.
        </p>
      )}
    </aside>
  )
}
