/**
 * Banda de aviso de modo simulado.
 *
 * No es una decision de diseno: la exige el contrato. Ver
 * contratos/enums.py linea 55 y contratos/esquemas.py linea 208.
 *
 * Solo se muestra si el modo es simulado. Cuando la API sirva datos reales
 * desaparece sola, sin tocar este componente.
 */
export default function AvisoModoSimulado({ salud }) {
  if (!salud || salud.modo !== 'simulado') {
    return null
  }

  return (
    <div className="aviso-simulado trama-simulado" role="status">
      <strong>Modo simulado</strong>
      <span>
        Los datos que se muestran no son reales y no deben usarse para tomar
        ninguna decision. Las geometrias son marcadores de posicion y se
        reemplazan con la capa oficial del SNIT en la historia H1.3.
      </span>
      <span className="aviso-simulado-version">contratos v{salud.version_contratos}</span>
    </div>
  )
}
