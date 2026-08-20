/**
 * Avisos sobre la naturaleza y la procedencia de los datos que se estan viendo.
 *
 * Exigido por el contrato: contratos/enums.py y contratos/esquemas.py dicen que
 * el visor avisa de forma visible cuando el modo es SIMULADO. La parte del origen
 * completa el criterio CA-3 de H6.6.
 *
 * ---------------------------------------------------------------------------
 * SON DOS EJES, NO UNO
 * ---------------------------------------------------------------------------
 *
 *   `modo`   dice QUE son los datos: simulado o real. Lo decide la API segun que
 *            implementacion del repositorio respondio, asi que no puede mentir.
 *
 *   `origen` dice POR DONDE llegaron: la API, o los archivos estaticos que
 *            quedaron como respaldo cuando la API no contesta.
 *
 * Mezclarlos en un solo campo perderia el caso que importa. Hoy no se puede dar,
 * porque el respaldo se genera del mismo simulado que sirve la API. Pero el dia
 * que la API sirva dato real y se caiga, el respaldo va a servir dato simulado
 * viejo: datos falsos y desactualizados a la vez, y con un solo campo eso se
 * veria igual que una tarde normal.
 *
 * Los cuatro casos:
 *
 *   modo      origen     que se muestra
 *   --------  ---------  ------------------------------------------------
 *   simulado  api        Banda de modo simulado
 *   simulado  estatico   Banda de modo simulado + aviso de respaldo
 *   real      api        Nada. Es el estado normal del sistema terminado
 *   real      estatico   Solo el aviso de respaldo. Es el caso peligroso
 */

const ORIGEN_ESTATICO = 'estatico'

/**
 * Aviso de que los datos no vienen de la API sino de los archivos de respaldo.
 *
 * Va en ambar y no en rojo. El rojo esta reservado para riesgo alto: una banda
 * roja aqui se leeria como alerta climatica cuando lo que advierte es sobre la
 * procedencia del dato. Es el mismo criterio por el que la banda de modo simulado
 * es azul pizarra.
 *
 * `motivo` trae el texto crudo que devolvio el fetch, del tipo "fetch failed" o
 * "la API respondio 502". No es texto para el usuario, asi que va en el atributo
 * title: quien necesite diagnosticar lo encuentra, y quien no, no lo sufre.
 */
function AvisoRespaldo({ motivo, datosReales }) {
  return (
    <div className="aviso-respaldo" role="alert" title={motivo ?? undefined}>
      <strong>Sin conexion con la API</strong>
      <span>
        {datosReales
          ? 'Lo que se muestra viene de archivos de respaldo y puede estar desactualizado. No refleja el estado actual del sistema.'
          : 'La API no responde. Lo que se muestra viene de los archivos de respaldo.'}
      </span>
    </div>
  )
}

export default function AvisoModoSimulado({ salud }) {
  if (!salud) return null

  const esSimulado = salud.modo === 'simulado'
  const esRespaldo = salud.origen === ORIGEN_ESTATICO

  // Estado normal del sistema terminado: dato real servido por la API. Nada que
  // advertir, y una banda permanente que no dice nada entrena a ignorarlas.
  if (!esSimulado && !esRespaldo) return null

  return (
    <>
      {esSimulado && (
        <div className="aviso-simulado trama-simulado" role="status">
          <strong>Modo simulado</strong>
          <span>
            Los datos que se muestran no son reales y no deben usarse para tomar
            ninguna decision. Las geometrias son marcadores de posicion y se
            reemplazan con la capa oficial del SNIT en la historia H1.3.
          </span>
          <span className="aviso-simulado-version">
            contratos v{salud.version_contratos}
          </span>
        </div>
      )}

      {esRespaldo && (
        <AvisoRespaldo motivo={salud.motivo_respaldo} datosReales={!esSimulado} />
      )}
    </>
  )
}
