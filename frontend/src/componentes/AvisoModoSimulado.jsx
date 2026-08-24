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
 *   simulado  api        Una banda: datos de demostracion
 *   simulado  estatico   La misma banda, sola
 *   real      api        Nada. Es el estado normal del sistema terminado
 *   real      estatico   Aviso de dato desactualizado. Es el caso peligroso
 *
 * El segundo caso mostraba las DOS bandas hasta el 24 de agosto. Se junto en
 * una: las dos advertian sobre la confiabilidad del dato y apiladas ocupaban
 * un sexto de la pantalla antes de que apareciera el mapa. Una advertencia que
 * siempre esta encendida ensena a ignorar las advertencias, y en el sitio
 * publicado el respaldo es permanente y esperado -no hay API que desplegar
 * hasta H11.1, que depende de H6.0-.
 *
 * Lo que NO se toco es que el aviso exista: lo exigen contratos/enums.py y
 * contratos/esquemas.py, y es el criterio CA-7 de H11.5. Es una pagina publica
 * de riesgo climatico. Lo que cambio es cuanto ocupa y en que idioma habla.
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
function AvisoRespaldo({ motivo }) {
  return (
    <div className="aviso-respaldo" role="alert" title={motivo ?? undefined}>
      <strong>Datos desactualizados</strong>
      <span>
        No hay conexion con el servidor. Lo que se ve puede no reflejar el estado
        actual.
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
        <div
          className="aviso-simulado trama-simulado"
          role="status"
          title={`contratos v${salud.version_contratos}`}
        >
          <strong>Datos de demostracion</strong>
          <span>
            Los niveles de riesgo son de prueba y no representan riesgo real.
          </span>
        </div>
      )}

      {/* El aviso de respaldo se calla cuando ya se dijo que el dato es de
          prueba: dos bandas apiladas para advertir lo mismo se leen como una
          pared de texto y entrenan a ignorarlas. En el sitio publicado no hay
          API, asi que el respaldo es permanente y esperado, no una averia.

          El caso que si importa es `real` + `estatico`: dato de verdad pero
          viejo. Ese sigue avisando, y es el unico que queda. */}
      {esRespaldo && !esSimulado && <AvisoRespaldo motivo={salud.motivo_respaldo} />}
    </>
  )
}
