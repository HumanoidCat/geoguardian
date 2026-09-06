import { ORIGEN_API } from '../datos/cliente'

/**
 * La pastilla de la cabecera: que son los datos y por donde llegaron.
 *
 * Historia H5.9. Son los dos campos de D-23, `modo` y `origen`, dichos en una
 * linea. La banda de AvisoModoSimulado sigue existiendo y la exige el contrato;
 * esto no la reemplaza: es el resumen que se ve sin bajar la vista.
 *
 * El punto verde solo aparece con datos reales por la API. Cualquier otra
 * combinacion va en ambar, igual que el resto de los avisos sobre la procedencia
 * del dato: el rojo esta reservado para riesgo alto.
 */
export default function EstadoDatos({ salud }) {
  if (!salud) {
    return (
      <div className="estado-datos estado-datos-cargando" aria-live="polite">
        <span className="estado-punto" aria-hidden="true" />
        <span>Conectando con la API...</span>
      </div>
    )
  }

  const porApi = salud.origen === ORIGEN_API
  const real = salud.modo === 'real'
  const clase = porApi && real ? 'estado-datos estado-datos-real' : 'estado-datos estado-datos-aviso'
  const que = real ? 'Datos reales' : 'Datos simulados'
  const camino = porApi ? 'API' : 'respaldo estatico'

  return (
    <div className={clase} title={`modo: ${salud.modo} · origen: ${salud.origen}`}>
      <span className="estado-punto" aria-hidden="true" />
      <span>
        <strong>{que}</strong>
        <span className="estado-datos-detalle"> · {camino}</span>
        {salud.version_contratos && (
          <span className="estado-datos-detalle"> · contratos {salud.version_contratos}</span>
        )}
      </span>
    </div>
  )
}
