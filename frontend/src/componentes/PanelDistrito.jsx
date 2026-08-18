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

export default function PanelDistrito({ distrito, riesgo, nombreEvento }) {
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

      <BloqueRiesgo riesgo={riesgo} nombreEvento={nombreEvento} />

      {simulada && (
        <p className="panel-nota">
          La forma de este distrito es un marcador de posicion, no su limite
          real. Se reemplaza en la historia H1.3 con la capa del SNIT.
        </p>
      )}
    </aside>
  )
}
