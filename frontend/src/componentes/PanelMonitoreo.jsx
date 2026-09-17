import { useEffect, useMemo, useState } from 'react'
import { LO_QUE_NO_SE_VIGILA, describirEntorno, leerCampos } from '../datos/monitoreo'

/**
 * La pantalla de monitoreo: que entorno se esta viendo y en que estado esta.
 *
 * Historia H12.2. Rubrica Troubleshoot.
 *
 * QUE AUTOMATIZA, Y POR QUE ESO ES LA HISTORIA
 *
 * `docs/20-manual-de-operacion.md` cierra declarando que **nada vigila el sitio
 * publicado**, que la comprobacion diaria de su seccion 2 es manual, y que
 * depende de que alguien se acuerde -que es lo que **I-10** dejo dicho que no
 * funciona-. Nombra a esta historia como lo que falta.
 *
 * Asi que esta pantalla es, exactamente, la seccion 2 de ese manual hecha una
 * pantalla. No inventa criterios nuevos: muestra los mismos campos con las mismas
 * lecturas. Si el manual cambia, esto cambia con el.
 *
 * LO QUE NO HACE, Y ESTA ESCRITO EN LA PROPIA PANTALLA
 *
 * No dice «todo bien». Por cada campo muestra **el valor y el esperado**, y deja
 * la conclusion a quien lee. Un panel que resume el estado en una luz verde es
 * una fuente que informa sobre si misma: es el patron de I-25, I-39 e I-41, los
 * tres que el manual de operacion junta en su tabla de triaje.
 *
 * Y declara lo que no vigila -CA-5-, en vez de dejar un recuadro vacio que se
 * lea como «no hay problemas».
 */
export default function PanelMonitoreo({ salud, alVerMapa }) {
  const [esperado, setEsperado] = useState(undefined)

  // El archivo lo genera `frontend/herramientas/generar_esperado.py` desde
  // `contratos/__init__.py`. Si no esta, no se supone que todo coincide: se dice
  // que no hay con que comparar. Ver `contrastarVersiones`.
  useEffect(() => {
    let vigente = true
    fetch(`${import.meta.env.BASE_URL}estado/esperado.json`)
      .then((respuesta) => (respuesta.ok ? respuesta.json() : null))
      .then((datos) => {
        if (vigente) setEsperado(datos)
      })
      .catch(() => {
        if (vigente) setEsperado(null)
      })
    return () => {
      vigente = false
    }
  }, [])

  const entorno = useMemo(
    () => describirEntorno(salud, typeof window === 'undefined' ? '' : window.location.hostname),
    [salud],
  )

  // La hora se toma una vez al montar y no con un temporizador. Un reloj que
  // corre haria que «hace 3 h» cambiara solo, y esta pantalla no se actualiza
  // sola: lo honesto es que la antiguedad sea la del momento en que se abrio.
  const campos = useMemo(() => leerCampos(salud, esperado ?? null, new Date()), [salud, esperado])

  if (!salud) {
    return (
      <section className="monitoreo" aria-label="Estado del sistema">
        <p className="monitoreo-vacio">
          Todavia no se pudo leer <code>/api/salud</code>. Sin esa respuesta esta pantalla no
          tiene que mostrar.
        </p>
      </section>
    )
  }

  return (
    <section className="monitoreo" aria-label="Estado del sistema">
      <div className="monitoreo-encabezado">
        <div>
          <h2 className="monitoreo-titulo">Estado del sistema</h2>
          <p className="monitoreo-subtitulo">
            Es la comprobacion diaria de <code>docs/20-manual-de-operacion.md</code>, seccion 2,
            hecha pantalla. Muestra el valor y el esperado; la conclusion la saca quien mira.
          </p>
        </div>
        <button type="button" className="boton-ir-a-hoy" onClick={alVerMapa}>
          Volver al mapa
        </button>
      </div>

      {/* CA-1 · el entorno se deriva de `origen` y del host, nunca de una constante */}
      {entorno && (
        <div className={`monitoreo-entorno monitoreo-entorno-${entorno.clave}`}>
          <span className="monitoreo-entorno-nombre">{entorno.nombre}</span>
          <span className="monitoreo-entorno-detalle">{entorno.detalle}</span>
        </div>
      )}

      {/* CA-2, CA-3 y CA-4 · los cinco campos con su lectura.

          La envoltura no es decorativa: a 390 px una tabla de cuatro columnas no
          cabe, y CA-7 exige que no haya desbordamiento horizontal **de la
          pagina**. Desplazarse dentro del propio contenedor si vale; arrastrar la
          pagina entera, no. */}
      <div className="monitoreo-tabla-envoltura">
      <table className="monitoreo-tabla">
        <caption className="monitoreo-caption">
          Los cinco campos de <code>Salud</code>. Desde I-41 los cinco se derivan de la
          implementacion que contesto: ninguno se escribe a mano.
        </caption>
        <thead>
          <tr>
            <th scope="col">Campo</th>
            <th scope="col">Valor</th>
            <th scope="col">Esperado</th>
            <th scope="col">Que significa</th>
          </tr>
        </thead>
        <tbody>
          {campos.map((campo) => (
            <tr key={campo.clave} className={campo.bien ? undefined : 'monitoreo-fila-atencion'}>
              <th scope="row">
                <code>{campo.etiqueta}</code>
              </th>
              <td>
                {/* D-07 · la ausencia se declara, no se rellena con un guion */}
                {campo.valor === null ? (
                  <span className="monitoreo-ausente">sin dato</span>
                ) : (
                  <code>{campo.valor}</code>
                )}
                {campo.antiguedad && !campo.antiguedad.anomala && (
                  <span className="monitoreo-antiguedad"> · {campo.antiguedad.texto}</span>
                )}
              </td>
              <td className="monitoreo-esperado">{campo.esperado}</td>
              <td>{campo.lectura}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>

      {esperado === null && (
        <p className="monitoreo-nota">
          No se encontro <code>estado/esperado.json</code>, asi que la version de contratos no se
          pudo contrastar contra el arbol construido. Se genera con{' '}
          <code>python frontend/herramientas/generar_esperado.py</code>.
        </p>
      )}

      {/* CA-5 · lo que esta pantalla NO vigila, dicho aca y no omitido */}
      <div className="monitoreo-huecos">
        <h3 className="monitoreo-huecos-titulo">Lo que esta pantalla no vigila</h3>
        <p className="monitoreo-huecos-intro">
          Se dice porque callarlo la convertiria en lo que este proyecto ya arreglo tres veces:
          un indicador que informa sobre si mismo en vez de sobre el sistema (I-25, I-39, I-41).
        </p>
        <dl className="monitoreo-huecos-lista">
          {LO_QUE_NO_SE_VIGILA.map((hueco) => (
            <div key={hueco.que}>
              <dt>{hueco.que}</dt>
              <dd>
                {hueco.porque} <em>{hueco.depende}</em>
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}
