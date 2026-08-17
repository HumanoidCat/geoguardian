/**
 * Ficha del distrito seleccionado.
 *
 * Regla que atraviesa este componente: lo que no se sabe se dice, no se
 * rellena. Un guion o un cero en lugar de "sin dato" convierte una ausencia en
 * una afirmacion.
 */

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

export default function PanelDistrito({ distrito }) {
  if (!distrito) {
    return (
      <aside className="panel">
        <p className="panel-vacio">
          Hace clic en un distrito del mapa para ver su ficha.
        </p>
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

      <div className="panel-estimacion">
        <span className="cuadro-leyenda trama-sin-dato" aria-hidden="true" />
        <div>
          <p className="panel-estimacion-titulo">Sin estimacion de riesgo</p>
          <p className="panel-estimacion-detalle">
            Todavia no hay un modelo entrenado, asi que ningun distrito tiene
            nivel de riesgo calculado. No es un riesgo bajo: es la ausencia de
            una medicion.
          </p>
        </div>
      </div>

      {simulada && (
        <p className="panel-nota">
          La forma de este distrito es un marcador de posicion, no su limite
          real. Se reemplaza en la historia H1.3 con la capa del SNIT.
        </p>
      )}
    </aside>
  )
}
